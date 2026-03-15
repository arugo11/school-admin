from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


def _pick_category(title: str) -> str:
    rules = [
        ("式・因数分解", ["多項式", "展開", "乗法公式", "因数分解", "式の計算"]),
        ("平方根", ["平方根", "根号", "有理化"]),
        ("方程式", ["方程式", "解の公式"]),
        ("二次関数", ["関数", "放物線", "変域", "変化の割合"]),
        ("相似・比", ["相似", "線分の比", "面積比", "体積比", "中点連結", "チェバ", "メネラウス"]),
        ("円と図形", ["円", "円周角"]),
        ("三平方", ["三平方"]),
        ("図形総合", ["平面図形", "空間図形", "球"]),
        ("確率・データ", ["確率", "標本調査", "データ"]),
        ("整数・規則性", ["整数", "規則性", "数の性質"]),
    ]
    for category, keywords in rules:
        if any(keyword in title for keyword in keywords):
            return category
    return "総合"


def _pick_difficulty(title: str) -> str:
    if any(marker in title for marker in ["難関", "応用", "入試実戦", "記述対策", "ランクアップ"]):
        return "advanced"
    if any(marker in title for marker in ["章末精選", "利用", "まとめ", "対策テスト"]):
        return "standard"
    return "basic"


def _normalize_topic(raw: str) -> str | None:
    line = raw.strip().strip("`")
    if not line or line.startswith("リンク"):
        return None
    line = re.sub(r"^[\d０-９]+(?:[・\-][\d０-９]+)*\s*", "", line)
    line = re.sub(r"^第\d+章\s*", "", line)
    line = line.strip(" \t　")
    if not line:
        return None
    if line in {"章末精選問題", "章末応用問題", "重要ポイント", "1・2年の復習"}:
        return line
    return line


@lru_cache(maxsize=1)
def load_demo_homework_groups() -> list[dict]:
    text_path = settings.repo_root / "docs" / "text_sample.txt"
    if not text_path.exists():
        return []

    lines = text_path.read_text(encoding="utf-8").splitlines()
    textbook_index = -1
    current_textbook = ""
    groups: list[dict] = []

    for line in lines:
        heading = re.match(r"^#\s+(.+)$", line.strip())
        if heading:
            title = heading.group(1).strip()
            if title and title != "メインテキスト":
                textbook_index += 1
                current_textbook = f"教材{chr(ord('A') + textbook_index)}"
            elif title == "メインテキスト":
                textbook_index += 1
                current_textbook = f"教材{chr(ord('A') + textbook_index)}"
            continue

        if not current_textbook:
            continue

        topic = _normalize_topic(line)
        if topic is None:
            continue

        category = _pick_category(topic)
        difficulty = _pick_difficulty(topic)
        group_id = f"G-{len(groups) + 1:03d}"
        groups.append(
            {
                "group_id": group_id,
                "textbook_name": current_textbook,
                "unit_name": category,
                "topic_name": topic,
                "difficulty": difficulty,
                "estimated_minutes": 12 if difficulty == "advanced" else 8 if difficulty == "standard" else 6,
                "tags": [category, topic],
            }
        )

    # 同一教材・同一トピック重複を削る
    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        key = (group["textbook_name"], group["topic_name"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(group)
    return deduped
