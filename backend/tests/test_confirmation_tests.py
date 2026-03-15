from __future__ import annotations

from app.schemas import NormalizedOcrDocument, OcrConfidenceSummary, OcrItem
from app.services.confirmation_tests import (
    DatasetSource,
    apply_problem_regrade,
    build_manifest,
    build_problem_feedback,
    build_selection_record,
    sanitize_test_id,
    select_balanced_problems,
    summarize_confirmation_test_performance,
)


def sample_rows() -> list[dict]:
    return [
        {"problem": f"Problem {index}", "solution": f"Solution {index}", "answer": str(index), "subject": subject, "level": level, "unique_id": f"uid-{index:02d}"}
        for index, (subject, level) in enumerate([
            ("Algebra", 1),
            ("Geometry", 2),
            ("Prealgebra", 1),
            ("Algebra", 2),
            ("Geometry", 1),
            ("Precalculus", 2),
            ("Algebra", 3),
            ("Prealgebra", 2),
        ], start=1)
    ]


def test_selection_is_deterministic_for_same_seed() -> None:
    rows = sample_rows()
    first = select_balanced_problems(rows, count=5, seed=11)
    second = select_balanced_problems(rows, count=5, seed=11)
    assert [item["unique_id"] for item in first] == [item["unique_id"] for item in second]


def test_manifest_problem_count_matches_selection() -> None:
    source = DatasetSource('demo-dataset', 'Japanese', 'test')
    selected = select_balanced_problems(sample_rows(), count=4, seed=5)
    manifest = build_manifest('ct-demo', 5, '2026-03-15T00:00:00+09:00', 1, 3, 20, 3, source, selected)
    selection = build_selection_record(manifest, filters={"count": 4})
    assert manifest.problem_count == 4
    assert len(selection.selected_problems) == 4
    assert selection.selected_problems[0].catalog_problem_no.startswith('CT-DEMO-Q')


def test_performance_summary_uses_manifest_answers(tmp_path, monkeypatch) -> None:
    source = DatasetSource('demo-dataset', 'Japanese', 'test')
    selected = select_balanced_problems(sample_rows(), count=3, seed=7)
    manifest = build_manifest('ct-perf', 7, '2026-03-15T00:00:00+09:00', 1, 3, 15, 3, source, selected)
    out = tmp_path / 'test'
    out.mkdir()
    (out / 'manifest.json').write_text(manifest.model_dump_json(indent=2), encoding='utf-8')

    from app.services import confirmation_tests as module
    monkeypatch.setattr(module, 'TESTS_ROOT', tmp_path)

    normalized = NormalizedOcrDocument(
        student_id='s-03',
        source_image_id='img-1',
        source_image_paths=[],
        page_type='worksheet',
        ocr_confidence_summary=OcrConfidenceSummary(low_confidence_count=0, notes=[]),
        items=[
            OcrItem(problem_no='Q1', recognized_answer=manifest.problems[0].answer, final_answer=manifest.problems[0].answer, raw_text='Q1'),
            OcrItem(problem_no='Q2', recognized_answer='wrong', final_answer='wrong', raw_text='Q2'),
            OcrItem(problem_no='Q3', recognized_answer=manifest.problems[2].answer, final_answer=manifest.problems[2].answer, raw_text='Q3'),
        ],
        test_id='ct-perf',
        source_alias='math-500-jp',
    )
    summary = summarize_confirmation_test_performance(normalized)
    assert summary is not None
    assert summary.correct_count == 2
    assert summary.incorrect_count == 1


def test_problem_feedback_marks_ambiguous_as_uncertain(tmp_path, monkeypatch) -> None:
    source = DatasetSource('demo-dataset', 'Japanese', 'test')
    selected = select_balanced_problems(sample_rows(), count=2, seed=7)
    manifest = build_manifest('ct-feedback', 7, '2026-03-15T00:00:00+09:00', 1, 3, 15, 3, source, selected)
    out = tmp_path / 'test'
    out.mkdir()
    (out / 'manifest.json').write_text(manifest.model_dump_json(indent=2), encoding='utf-8')

    from app.services import confirmation_tests as module
    monkeypatch.setattr(module, 'TESTS_ROOT', tmp_path)

    normalized = NormalizedOcrDocument(
        student_id='s-03',
        source_image_id='img-1',
        source_image_paths=[],
        page_type='worksheet',
        ocr_confidence_summary=OcrConfidenceSummary(low_confidence_count=1, notes=[]),
        items=[
            OcrItem(problem_no='Q1', recognized_answer='unknown', work_text='2x+1=5', final_answer=None, raw_text='Q1 ?', uncertainty=['ambiguous-character', 'final-answer-missing']),
            OcrItem(problem_no='Q2', recognized_answer='wrong', final_answer='wrong', raw_text='Q2 wrong'),
        ],
        test_id='ct-feedback',
        source_alias='math-500-jp',
    )
    feedback = build_problem_feedback(normalized)
    assert feedback[0].grading_status == 'uncertain'
    assert feedback[0].needs_review is True
    assert feedback[0].work_text == '2x+1=5'
    assert feedback[1].grading_status == 'incorrect'


def test_problem_feedback_marks_exact_match_correct_despite_benign_ocr_fallback(tmp_path, monkeypatch) -> None:
    source = DatasetSource('demo-dataset', 'Japanese', 'test')
    selected = select_balanced_problems(sample_rows(), count=1, seed=3)
    manifest = build_manifest('ct-benign', 3, '2026-03-15T00:00:00+09:00', 1, 3, 15, 3, source, selected)
    out = tmp_path / 'test'
    out.mkdir()
    (out / 'manifest.json').write_text(manifest.model_dump_json(indent=2), encoding='utf-8')

    from app.services import confirmation_tests as module
    monkeypatch.setattr(module, 'TESTS_ROOT', tmp_path)

    answer = manifest.problems[0].answer
    normalized = NormalizedOcrDocument(
        student_id='s-03',
        source_image_id='img-1',
        source_image_paths=[],
        page_type='worksheet',
        ocr_confidence_summary=OcrConfidenceSummary(low_confidence_count=1, notes=[]),
        items=[OcrItem(problem_no='Q1', recognized_answer=answer, final_answer=answer, raw_text='Q1', uncertainty=['low-confidence', 'aoai-bulk-fallback: HTTPStatusError'])],
        test_id='ct-benign',
        source_alias='qa-verify-10k-jp',
    )
    feedback = build_problem_feedback(normalized)
    assert feedback[0].grading_status == 'correct'
    assert feedback[0].needs_review is False


def test_problem_regrade_can_promote_to_correct_from_note(tmp_path, monkeypatch) -> None:
    source = DatasetSource('demo-dataset', 'Japanese', 'test')
    selected = select_balanced_problems(sample_rows(), count=1, seed=7)
    manifest = build_manifest('ct-regrade', 7, '2026-03-15T00:00:00+09:00', 1, 3, 15, 3, source, selected)
    out = tmp_path / 'test'
    out.mkdir()
    (out / 'manifest.json').write_text(manifest.model_dump_json(indent=2), encoding='utf-8')

    from app.services import confirmation_tests as module
    monkeypatch.setattr(module, 'TESTS_ROOT', tmp_path)

    normalized = NormalizedOcrDocument(
        student_id='s-03',
        source_image_id='img-1',
        source_image_paths=[],
        page_type='worksheet',
        ocr_confidence_summary=OcrConfidenceSummary(low_confidence_count=0, notes=[]),
        items=[OcrItem(problem_no='Q1', recognized_answer='wrong', final_answer='wrong', raw_text='Q1 wrong')],
        test_id='ct-regrade',
        source_alias='math-500-jp',
    )
    current = build_problem_feedback(normalized)
    updated, target = apply_problem_regrade(normalized, current, 'Q1', f'本当は {manifest.problems[0].answer} です')
    assert updated[0].grading_status == 'correct'
    assert target.regrade_requested is True
    assert target.regrade_note is not None
