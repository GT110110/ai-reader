"""笔记管理 —— 阅读时随手记录，自动关联章节

支持：
- 章节笔记（Markdown 原文存储）
- 金句收藏（quotes.json，按书聚合）
- 全书导出（Markdown，带目录/状态/金句区）
"""

import os
import json
from datetime import datetime
from pathlib import Path

SHELF_DIR = Path(__file__).parent / "shelf"


def get_notes_dir(book_id: str) -> Path:
    """获取某本书的笔记目录"""
    d = SHELF_DIR / book_id / "notes"
    os.makedirs(d, exist_ok=True)
    return d


def save_note(book_id: str, chapter_idx: int, text: str) -> dict:
    """保存/覆盖某章的笔记（Markdown 原文）"""
    path = get_notes_dir(book_id) / f"chapter_{chapter_idx}.md"
    note = {
        "chapter_idx": chapter_idx,
        "content": text,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    # 同时存一份 JSON 元信息
    meta_path = get_notes_dir(book_id) / f"chapter_{chapter_idx}.meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(note, f, ensure_ascii=False, indent=2)
    return note


def load_note(book_id: str, chapter_idx: int) -> str:
    """读取某章的笔记（Markdown 原文）"""
    path = get_notes_dir(book_id) / f"chapter_{chapter_idx}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_all_notes(book_id: str) -> list[dict]:
    """获取某本书所有笔记的摘要列表"""
    notes_dir = get_notes_dir(book_id)
    notes = []
    for f in sorted(notes_dir.glob("chapter_*.md")):
        idx = int(f.stem.split("_")[1])
        content = f.read_text(encoding="utf-8").strip()
        notes.append(
            {
                "chapter_idx": idx,
                "content": content,
                "length": len(content),
                "preview": content[:100],
            }
        )
    return notes


def append_to_note(book_id: str, chapter_idx: int, text: str):
    """追加内容到某章笔记（不覆盖）"""
    existing = load_note(book_id, chapter_idx)
    new_text = existing + "\n\n" + text if existing else text
    save_note(book_id, chapter_idx, new_text)


# ═══════════════════════════════════════════
# 金句收藏
# ═══════════════════════════════════════════


def _quotes_path(book_id: str) -> Path:
    return SHELF_DIR / book_id / "quotes.json"


def save_quote(book_id: str, chapter_idx: int, quote: str, source: str = "ai") -> bool:
    """收藏一条金句。

    quote: 金句正文
    source: "ai" 或 "user"（用户手动摘录）
    返回 True 表示新增成功，False 表示已存在（去重）
    """
    path = _quotes_path(book_id)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            quotes = json.load(f)
    else:
        quotes = []

    # 去重：相同文字 + 相同章节视为重复
    quote_clean = quote.strip()
    for q in quotes:
        if q.get("quote", "").strip() == quote_clean and q.get("chapter_idx") == chapter_idx:
            return False

    quotes.append(
        {
            "chapter_idx": chapter_idx,
            "quote": quote_clean,
            "source": source,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)
    return True


def get_quotes(book_id: str) -> list[dict]:
    """获取某本书的全部金句"""
    path = _quotes_path(book_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def delete_quote(book_id: str, index: int) -> bool:
    """按索引删除一条金句"""
    path = _quotes_path(book_id)
    if not path.exists():
        return False
    with open(path, "r", encoding="utf-8") as f:
        quotes = json.load(f)
    if 0 <= index < len(quotes):
        quotes.pop(index)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(quotes, f, ensure_ascii=False, indent=2)
        return True
    return False


# ═══════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════


def export_book_notes(book_id: str, book_title: str, chapters: list) -> str:
    """导出全书笔记为 Markdown（带目录/状态/金句区）"""
    lines = [
        f"# 《{book_title}》阅读笔记",
        "",
        f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 📑 目录",
        "",
    ]

    all_notes = get_all_notes(book_id)
    note_map = {n["chapter_idx"]: n["content"] for n in all_notes}

    for i, ch in enumerate(chapters):
        name = ch.get("name", f"第{i+1}章")
        status = ch.get("status", "unread")
        status_icon = "✅" if status == "completed" else "📖" if status == "reading" else "○"
        bookmark = " ⭐" if ch.get("bookmarked") else ""
        has_note = "📝" if i in note_map and note_map[i].strip() else ""
        lines.append(f"{status_icon} {i+1}. {name}{bookmark} {has_note}")

    lines += ["", "---", "", "## 📝 章节笔记", ""]

    for i, ch in enumerate(chapters):
        name = ch.get("name", f"第{i+1}章")
        lines.append(f"### {i+1}. {name}")
        if i in note_map and note_map[i].strip():
            lines.append("")
            lines.append(note_map[i])
        else:
            lines.append("")
            lines.append("*（暂无笔记）*")
        lines.append("")

    # 金句区
    quotes = get_quotes(book_id)
    if quotes:
        lines += ["---", "", "## 💎 金句收藏", ""]
        for q in quotes:
            ch_name = (
                chapters[q["chapter_idx"]].get("name", f"第{q['chapter_idx']+1}章")
                if 0 <= q["chapter_idx"] < len(chapters)
                else ""
            )
            lines.append(f"> {q['quote']}")
            lines.append(f">")
            lines.append(f"> —— 《{book_title}》{ch_name}")
            lines.append("")

    return "\n".join(lines)
