from __future__ import annotations

import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datasets import load_dataset
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.schemas import (
    ConfirmationPerformanceItem,
    ConfirmationPerformanceSummary,
    ConfirmationProblem,
    ConfirmationSelectionRecord,
    ConfirmationTestLayout,
    ConfirmationTestManifest,
    NormalizedOcrDocument,
    ProblemFeedback,
)

GENERATOR_VERSION = "confirmation-test-v2"
SOURCE_ALIAS = "qa-verify-10k-jp"
DEFAULT_DATASET_NAME = "team-victory/qa_verify_10k_test"
DEFAULT_DATASET_CONFIG = None
DEFAULT_DATASET_SPLIT = "train"
FALLBACK_DATASET_NAME = "appier-ai-research/Multilingual-MATH-500"
FALLBACK_DATASET_CONFIG = "Japanese"
FALLBACK_DATASET_SPLIT = "test"
TESTS_ROOT = settings.data_dir / "generated" / "tests"
TEMPLATES_ROOT = settings.repo_root / "scripts" / "templates"
KATEX_ROOT = settings.repo_root / "node_modules" / "katex" / "dist"
PLAYWRIGHT_RENDERER = settings.repo_root / "scripts" / "render_html_to_pdf.mjs"
SUBJECT_TO_UNIT = {
    "Prealgebra": "整数・四則計算",
    "Algebra": "一次方程式",
    "Intermediate Algebra": "式の変形",
    "Geometry": "図形",
    "Counting & Probability": "確率・場合の数",
    "Precalculus": "関数・座標",
    "Number Theory": "整数の性質",
}
TAG_HINTS = {
    "一次方程式": ["equation", "sign"],
    "式の変形": ["distribution", "sign"],
    "関数・座標": ["function"],
    "整数・四則計算": ["review"],
}


@dataclass(frozen=True)
class DatasetSource:
    name: str
    config: str | None
    split: str
    alias: str = SOURCE_ALIAS


PRIMARY_SOURCE = DatasetSource(DEFAULT_DATASET_NAME, DEFAULT_DATASET_CONFIG, DEFAULT_DATASET_SPLIT)
FALLBACK_SOURCE = DatasetSource(FALLBACK_DATASET_NAME, FALLBACK_DATASET_CONFIG, FALLBACK_DATASET_SPLIT)


def sanitize_test_id(test_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]+", "-", test_id).strip("-").lower()


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_math500_dataset(source: DatasetSource) -> tuple[list[dict[str, Any]], DatasetSource]:
    try:
        dataset = load_dataset(source.name, source.config, split=source.split, local_files_only=True)
    except Exception:
        dataset = load_dataset(source.name, source.config, split=source.split)
    return list(dataset), source


def load_with_fallback(dataset_name: str, dataset_config: str | None, split: str) -> tuple[list[dict[str, Any]], DatasetSource]:
    requested = DatasetSource(dataset_name, dataset_config, split)
    try:
        return load_math500_dataset(requested)
    except Exception:
        if requested == PRIMARY_SOURCE:
            return load_math500_dataset(FALLBACK_SOURCE)
        raise


def normalize_problem_row(row: dict[str, Any]) -> dict[str, Any]:
    unique_id = row.get("unique_id") or row.get("id") or f"row-{abs(hash(row.get('problem', ''))) % 10_000_000}"
    subject = str(row.get("unit") or row.get("subject") or row.get("category") or "General").strip() or "General"
    solution = str(row.get("generated_solution") or row.get("solution") or "").strip()
    answer = str(row.get("expected_answer") or row.get("answer") or "").strip()
    return {
        "problem": str(row.get("problem", "")).strip(),
        "solution": solution,
        "answer": answer,
        "subject": subject,
        "level": int(row.get("level", row.get("difficulty", 3))),
        "unique_id": str(unique_id),
    }


def filter_problem_rows(
    rows: list[dict[str, Any]],
    difficulty_min: int,
    difficulty_max: int,
    subject_include: list[str] | None = None,
    subject_exclude: list[str] | None = None,
) -> list[dict[str, Any]]:
    include = {item.lower() for item in (subject_include or [])}
    exclude = {item.lower() for item in (subject_exclude or [])}
    filtered: list[dict[str, Any]] = []
    for raw in rows:
        row = normalize_problem_row(raw)
        if not row["problem"] or not row["answer"]:
            continue
        if not difficulty_min <= row["level"] <= difficulty_max:
            continue
        subject = row["subject"].lower()
        if include and subject not in include:
            continue
        if exclude and subject in exclude:
            continue
        filtered.append(row)
    return sorted(filtered, key=lambda item: item["unique_id"])


def select_balanced_problems(rows: list[dict[str, Any]], count: int, seed: int) -> list[dict[str, Any]]:
    if len(rows) < count:
        raise ValueError(f"Not enough problems after filtering: requested={count}, available={len(rows)}")
    rng = random.Random(seed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["subject"]].append(row)
    for subject_rows in grouped.values():
        subject_rows.sort(key=lambda item: (item["level"], len(item["problem"]), item["unique_id"]))
        if subject_rows:
            rotation = rng.randrange(len(subject_rows))
            subject_rows[:] = subject_rows[rotation:] + subject_rows[:rotation]
    subjects = sorted(grouped)
    rng.shuffle(subjects)

    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    subject_index = 0
    while len(selected) < count:
        progressed = False
        for offset in range(len(subjects)):
            subject = subjects[(subject_index + offset) % len(subjects)]
            subject_rows = grouped[subject]
            while subject_rows and subject_rows[0]["unique_id"] in seen_ids:
                subject_rows.pop(0)
            if not subject_rows:
                continue
            item = subject_rows.pop(0)
            if item["unique_id"] in seen_ids:
                continue
            selected.append(item)
            seen_ids.add(item["unique_id"])
            subject_index = (subject_index + offset + 1) % len(subjects)
            progressed = True
            if len(selected) >= count:
                break
        if not progressed:
            break
    if len(selected) < count:
        remaining = [row for row in rows if row["unique_id"] not in seen_ids]
        selected.extend(remaining[: count - len(selected)])
    return selected[:count]


def estimated_minutes_for(level: int, problem_text: str) -> int:
    base = {1: 2, 2: 3, 3: 4, 4: 6, 5: 8}.get(level, 5)
    if len(problem_text) > 140:
        base += 1
    if len(problem_text) > 240:
        base += 1
    return base


def problem_to_manifest_entry(
    row: dict[str, Any],
    display_no: int,
    test_id: str,
    source: DatasetSource,
) -> ConfirmationProblem:
    catalog_problem_no = f"{sanitize_test_id(test_id).upper()}-Q{display_no:02d}"
    return ConfirmationProblem(
        display_no=display_no,
        problem_id=row["unique_id"],
        catalog_problem_no=catalog_problem_no,
        subject=row["subject"],
        level=row["level"],
        problem=row["problem"],
        answer=row["answer"],
        solution=row.get("solution", ""),
        estimated_minutes=estimated_minutes_for(row["level"], row["problem"]),
        source_dataset=source.name,
        source_config=source.config,
        source_split=source.split,
        source_unique_id=row["unique_id"],
        answer_zone_type="final_answer",
        work_area_label="計算過程",
        final_area_label="最終解答",
        metadata={"unit_name": SUBJECT_TO_UNIT.get(row["subject"], row["subject"]), "tag_hints": TAG_HINTS.get(SUBJECT_TO_UNIT.get(row["subject"], ""), [])},
    )


def estimate_question_pages(problems: list[ConfirmationProblem], max_pages: int) -> int:
    units = sum(max(1.0, len(problem.problem) / 180.0 + problem.level * 0.15) for problem in problems)
    pages = max(1, math.ceil(units / 4.2))
    return min(max_pages, pages)


def build_manifest(
    test_id: str,
    seed: int,
    generated_at: str,
    difficulty_min: int,
    difficulty_max: int,
    target_minutes: int,
    max_pages: int,
    source: DatasetSource,
    rows: list[dict[str, Any]],
) -> ConfirmationTestManifest:
    problems = [problem_to_manifest_entry(row, index + 1, test_id, source) for index, row in enumerate(rows)]
    return ConfirmationTestManifest(
        test_id=test_id,
        source_alias=source.alias,
        source_dataset=source.name,
        source_config=source.config,
        source_split=source.split,
        generated_at=generated_at,
        generator_version=GENERATOR_VERSION,
        seed=seed,
        problem_count=len(problems),
        difficulty_min=difficulty_min,
        difficulty_max=difficulty_max,
        layout=ConfirmationTestLayout(
            estimated_question_pages=estimate_question_pages(problems, max_pages=max_pages),
            max_pages=max_pages,
        ),
        target_minutes=target_minutes,
        problems=problems,
    )


def build_selection_record(manifest: ConfirmationTestManifest, filters: dict[str, Any]) -> ConfirmationSelectionRecord:
    return ConfirmationSelectionRecord(
        test_id=manifest.test_id,
        source_alias=manifest.source_alias,
        source_dataset=manifest.source_dataset,
        source_config=manifest.source_config,
        source_split=manifest.source_split,
        seed=manifest.seed,
        filters=filters,
        selected_problems=manifest.problems,
    )


def katex_asset_paths() -> dict[str, str]:
    return {
        "katex_css": (KATEX_ROOT / "katex.min.css").as_uri(),
        "katex_js": (KATEX_ROOT / "katex.min.js").as_uri(),
        "katex_autorender_js": (KATEX_ROOT / "contrib" / "auto-render.min.js").as_uri(),
    }


def render_html(template_name: str, context: dict[str, Any], output_path: Path) -> None:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATES_ROOT),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template(template_name)
    output_path.write_text(template.render(**context), encoding="utf-8")


def write_manifest_bundle(output_dir: Path, manifest: ConfirmationTestManifest, selection: ConfirmationSelectionRecord) -> None:
    (output_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "selected_problems.json").write_text(selection.model_dump_json(indent=2), encoding="utf-8")


def render_answer_key_markdown(output_dir: Path, manifest: ConfirmationTestManifest) -> Path:
    lines = [
        f"# Answer Key - {manifest.test_id}",
        "",
        f"- Source: {manifest.source_dataset} / {manifest.source_config or 'default'} / {manifest.source_split}",
        f"- Seed: {manifest.seed}",
        "",
        "| No | catalog_problem_no | subject | level | answer | source_unique_id |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for problem in manifest.problems:
        answer = problem.answer.replace("\n", " ")
        lines.append(
            f"| {problem.display_no} | {problem.catalog_problem_no} | {problem.subject} | {problem.level} | {answer} | {problem.source_unique_id} |"
        )
    target = output_dir / "answer_key.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def load_manifest_from_dir(directory: Path) -> ConfirmationTestManifest:
    return ConfirmationTestManifest.model_validate_json((directory / "manifest.json").read_text(encoding="utf-8"))


def load_manifest_by_test_id(test_id: str) -> ConfirmationTestManifest | None:
    if not TESTS_ROOT.exists():
        return None
    for manifest_path in TESTS_ROOT.glob("*/manifest.json"):
        manifest = ConfirmationTestManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if manifest.test_id == test_id:
            return manifest
    return None


def summarize_confirmation_test_performance(normalized_ocr: NormalizedOcrDocument) -> ConfirmationPerformanceSummary | None:
    if not normalized_ocr.test_id:
        return None
    manifest = load_manifest_by_test_id(normalized_ocr.test_id)
    if manifest is None:
        return None
    item_map = {item.problem_no: item for item in normalized_ocr.items}
    performance_items: list[ConfirmationPerformanceItem] = []
    missed_subjects: list[str] = []
    missed_catalog_problem_nos: list[str] = []
    for problem in manifest.problems:
        problem_no = f"Q{problem.display_no}"
        recognized = item_map.get(problem_no)
        recognized_answer = recognized.recognized_answer if recognized else "unknown"
        expected = normalize_answer_text(problem.answer)
        actual = normalize_answer_text(recognized_answer)
        is_correct = actual == expected and actual != "unknown"
        performance_items.append(
            ConfirmationPerformanceItem(
                problem_no=problem_no,
                catalog_problem_no=problem.catalog_problem_no,
                expected_answer=problem.answer,
                recognized_answer=recognized_answer,
                subject=problem.subject,
                level=problem.level,
                is_correct=is_correct,
            )
        )
        if not is_correct:
            missed_subjects.append(problem.metadata.get("unit_name", problem.subject))
            missed_catalog_problem_nos.append(problem.catalog_problem_no)
    correct_count = sum(1 for item in performance_items if item.is_correct)
    return ConfirmationPerformanceSummary(
        test_id=manifest.test_id,
        source_alias=manifest.source_alias,
        matched_count=sum(1 for item in performance_items if item.recognized_answer != "unknown"),
        correct_count=correct_count,
        incorrect_count=len(performance_items) - correct_count,
        missed_subjects=list(dict.fromkeys(missed_subjects)),
        missed_catalog_problem_nos=missed_catalog_problem_nos,
        items=performance_items,
    )


def normalize_answer_text(answer: str) -> str:
    simplified = answer.strip().lower()
    simplified = simplified.replace(" ", "")
    simplified = simplified.replace("\\left", "").replace("\\right", "")
    simplified = simplified.replace("（", "(").replace("）", ")")
    simplified = simplified.replace("−", "-").replace("–", "-")
    return simplified or "unknown"


def manifest_context_for_analysis(normalized_ocr: NormalizedOcrDocument) -> dict[str, Any] | None:
    summary = summarize_confirmation_test_performance(normalized_ocr)
    if summary is None:
        return None
    return summary.model_dump()


def _grading_basis(recognized_answer: str, work_text: str | None, final_answer: str | None) -> str:
    if final_answer and final_answer.strip():
        return f"最終解答欄を優先して {final_answer} を採用しました。"
    if work_text and work_text.strip():
        return f"最終解答欄が弱いため、計算過程欄の {work_text} を参考表示に残しました。"
    if recognized_answer != "unknown":
        return f"OCR では {recognized_answer} を抽出しましたが、欄の判別は要確認です。"
    return "最終解答欄も計算過程欄も十分に読み取れませんでした。"


def _comment_for_feedback(
    status: str,
    problem: ConfirmationProblem,
    recognized_answer: str,
    work_text: str | None,
    final_answer: str | None,
) -> str:
    if status == "correct":
        return f"最終解答欄の {recognized_answer} が模範解答 {problem.answer} と一致したため、正解として扱いました。"
    if status == "incorrect":
        work_note = f" 計算過程欄には {work_text} が見えています。" if work_text else ""
        return f"最終解答欄は {recognized_answer} と読み取り、模範解答 {problem.answer} と一致しませんでした。{work_note}".strip()
    if recognized_answer == "unknown":
        if work_text:
            return f"計算過程欄には {work_text} が見えますが、最終解答欄が弱いため、模範解答 {problem.answer} との照合は要確認にしました。"
        return f"最終解答欄が十分に読み取れなかったため、模範解答 {problem.answer} と照合しても断定を避けました。"
    if final_answer and work_text and normalize_answer_text(final_answer) != normalize_answer_text(work_text):
        return f"最終解答欄 {final_answer} と計算過程欄 {work_text} の内容が揃わないため、模範解答 {problem.answer} との照合結果は要確認です。"
    return f"OCR または表記ゆれの影響があるため、模範解答 {problem.answer} との照合結果は要確認にしています。"


def build_problem_feedback(
    normalized_ocr: NormalizedOcrDocument,
    previous_feedback: list[ProblemFeedback] | None = None,
) -> list[ProblemFeedback]:
    if not normalized_ocr.test_id:
        return []
    manifest = load_manifest_by_test_id(normalized_ocr.test_id)
    if manifest is None:
        return []
    item_map = {item.problem_no: item for item in normalized_ocr.items}
    previous_map = {item.problem_no: item for item in (previous_feedback or [])}
    feedback_items: list[ProblemFeedback] = []
    for problem in manifest.problems:
        problem_no = f"Q{problem.display_no}"
        recognized = item_map.get(problem_no)
        recognized_answer = recognized.recognized_answer if recognized else "unknown"
        work_text = recognized.work_text if recognized else None
        final_answer = recognized.final_answer if recognized else None
        expected = normalize_answer_text(problem.answer)
        actual = normalize_answer_text(recognized_answer)
        uncertainty = recognized.uncertainty if recognized else ["answer-missing"]
        benign_uncertainty = all(
            note == "low-confidence" or str(note).startswith("aoai-bulk-fallback:")
            for note in uncertainty
        )
        if actual == "unknown":
            status = "uncertain"
            needs_review = True
        elif actual == expected and benign_uncertainty:
            status = "correct"
            needs_review = False
        elif uncertainty:
            status = "uncertain"
            needs_review = True
        elif actual == expected:
            status = "correct"
            needs_review = False
        else:
            status = "incorrect"
            needs_review = False
        previous = previous_map.get(problem_no)
        feedback_items.append(
            ProblemFeedback(
                problem_no=problem_no,
                catalog_problem_no=problem.catalog_problem_no,
                expected_answer=problem.answer,
                recognized_answer=recognized_answer,
                work_text=work_text,
                final_answer=final_answer,
                source_image_path=recognized.source_image_path if recognized else (
                    normalized_ocr.source_image_paths[0] if normalized_ocr.source_image_paths else None
                ),
                work_image_path=recognized.work_image_path if recognized else None,
                final_image_path=recognized.final_image_path if recognized else None,
                grading_basis=_grading_basis(recognized_answer, work_text, final_answer),
                grading_status=status,
                comment=_comment_for_feedback(status, problem, recognized_answer, work_text, final_answer),
                needs_review=needs_review,
                regrade_available=True,
                regrade_requested=previous.regrade_requested if previous else False,
                regrade_note=previous.regrade_note if previous else None,
                regrade_outcome=previous.regrade_outcome if previous else None,
            )
        )
    return feedback_items


def _note_mentions_ocr_issue(student_note: str) -> bool:
    lowered = student_note.lower()
    hints = ("ocr", "読み取り", "誤認識", "符号", "マイナス", "分数", "小数点", "見切れ", "薄い")
    return any(hint in lowered for hint in hints)


def apply_problem_regrade(
    normalized_ocr: NormalizedOcrDocument,
    current_feedback: list[ProblemFeedback],
    problem_no: str,
    student_note: str,
) -> tuple[list[ProblemFeedback], ProblemFeedback]:
    manifest = load_manifest_by_test_id(normalized_ocr.test_id or "")
    if manifest is None:
        raise ValueError("Problem regrade is available only for confirmation tests")
    feedback_items = build_problem_feedback(normalized_ocr, previous_feedback=current_feedback)
    target_problem = next((problem for problem in manifest.problems if f"Q{problem.display_no}" == problem_no), None)
    if target_problem is None:
        raise KeyError(problem_no)
    expected = normalize_answer_text(target_problem.answer)
    note_normalized = normalize_answer_text(student_note)
    updated_items: list[ProblemFeedback] = []
    updated_feedback: ProblemFeedback | None = None
    for item in feedback_items:
        if item.problem_no != problem_no:
            updated_items.append(item)
            continue
        next_item = item.model_copy(deep=True)
        next_item.regrade_requested = True
        next_item.regrade_note = student_note.strip()
        if expected != "unknown" and expected in note_normalized:
            next_item.grading_status = "correct"
            next_item.needs_review = False
            next_item.regrade_outcome = "訂正依頼に模範解答と一致する内容が含まれていたため、再評価で正解候補として扱いました。"
            next_item.comment = f"生徒の訂正依頼を反映し、模範解答 {target_problem.answer} と一致する説明が確認できたため正解候補へ更新しました。"
            next_item.grading_basis = "生徒の訂正依頼を追加根拠として採用しました。"
        elif _note_mentions_ocr_issue(student_note):
            next_item.grading_status = "uncertain"
            next_item.needs_review = True
            next_item.regrade_outcome = "OCR や表記の取り違えの可能性があるため、再評価では要確認に変更しました。"
            next_item.comment = f"訂正依頼で OCR の取り違え可能性が示されたため、模範解答 {target_problem.answer} との照合は要確認として残しました。"
            next_item.grading_basis = "生徒の訂正依頼により OCR 読み取りの不確実性を優先しました。"
        else:
            next_item.regrade_outcome = "訂正依頼を反映して再確認しましたが、現在の情報だけでは判定を変更しませんでした。"
            next_item.comment = f"訂正依頼を受けて再確認しましたが、模範解答 {target_problem.answer} と一致する追加根拠はまだ不足しています。"
            next_item.grading_basis = "OCR と訂正依頼を見比べましたが、判定変更に十分な根拠は増えませんでした。"
        updated_feedback = next_item
        updated_items.append(next_item)
    if updated_feedback is None:
        raise KeyError(problem_no)
    return updated_items, updated_feedback
