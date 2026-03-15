from __future__ import annotations

from pathlib import Path

from app.services.confirmation_box_ocr import _cleanup_math_ocr_text, detect_question_regions
from app.services.llm_sheet_ocr import _open_image, _regions_from_visible_questions


def _line(text: str, left: float, top: float, right: float, bottom: float) -> dict:
    return {
        "text": text,
        "boundingBox": [left, top, right, top, right, bottom, left, bottom],
    }


def test_detect_question_regions_uses_help_lines_when_label_is_missing() -> None:
    image_path = Path("data/generated/tests/exhibit-main/sample-correct.png")
    raw_ocr = {
        "analyzeResult": {
            "readResults": [{
                "lines": [
                    _line("Q1", 10, 299, 40, 319),
                    _line("CT-EXHIBIT-MAIN-Q01 / 比例反比例", 10, 393, 320, 408),
                    _line("Q2", 10, 506, 40, 523),
                    _line("CT-EXHIBIT-MAIN-Q02 / 二次関数", 10, 600, 320, 614),
                    _line("Q3", 10, 715, 40, 730),
                    _line("CT-EXHIBIT-MAIN-Q03 / 三角関数", 10, 806, 320, 820),
                    _line("Q4", 10, 919, 40, 935),
                    _line("CT-EXHIBIT-MAIN-Q04 / 数列", 10, 1013, 320, 1026),
                    _line("05", 10, 1125, 40, 1139),
                    _line("CT-EXHIBIT-MAIN-Q05 / 数と式", 10, 1220, 320, 1233),
                    _line("Q6", 10, 1333, 40, 1347),
                    _line("CT-EXHIBIT-MAIN-Q06 / 積分", 10, 1426, 320, 1438),
                ]
            }]
        }
    }

    regions = detect_question_regions(image_path, raw_ocr)

    assert [region.problem_no for region in regions] == ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
    assert regions[4].row_box[1] < regions[4].row_box[3]


def test_cleanup_math_ocr_text_normalizes_common_formula_artifacts() -> None:
    assert _cleanup_math_ocr_text("Ifrac{Isqrt{2}} {2}") == "\\frac{\\sqrt{2}}{2}"


def test_llm_box_region_detection_finds_top_half_final_boxes() -> None:
    image_path = Path("data/test/confirmation_test-3.jpg")
    regions = _regions_from_visible_questions(_open_image(image_path), ["Q1", "Q2", "Q3", "Q4"])
    assert [region.problem_no for region in regions] == ["Q1", "Q2", "Q3", "Q4"]
    assert all(region.final_box[0] > 1500 for region in regions)
    assert all(region.work_box[2] < region.final_box[0] for region in regions)


def test_llm_box_region_detection_finds_lower_half_final_boxes() -> None:
    image_path = Path("data/test/confirmation_test-4.jpg")
    regions = _regions_from_visible_questions(_open_image(image_path), ["Q5", "Q6"])
    assert [region.problem_no for region in regions] == ["Q5", "Q6"]
    assert all(region.final_box[0] > 1500 for region in regions)
    assert all(region.row_box[0] < region.work_box[0] < region.work_box[2] < region.final_box[0] for region in regions)
