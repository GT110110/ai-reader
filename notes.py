"""笔记管理 —— 阅读时随手记录，自动关联章节"""

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
    """保存/覆盖某章的笔记"""
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
    """读取某章的笔记"""
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
        notes.append({
            "chapter_idx": idx,
            "content": content,
            "length": len(content),
            "preview": content[:100],
        })
    return notes


def append_to_note(book_id: str, chapter_idx: int, text: str):
    """追加内容到某章笔记（不覆盖）"""
    existing = load_note(book_id, chapter_idx)
    new_text = existing + "\n\n" + text if existing else text
    save_note(book_id, chapter_idx, new_text)


def export_book_notes(book_id: str, book_title: str, chapters: list) -> str:
    """导出全书笔记为 Markdown 文本"""
    lines = [f"# 📝 {book_title} — 阅读笔记", "", f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    all_notes = get_all_notes(book_id)
    note_map = {n["chapter_idx"]: n["content"] for n in all_notes}

    for i, ch in enumerate(chapters):
        name = ch.get("name", f"第{i+1}章")
        status = ch.get("status", "unread")
        status_icon = "●" if status == "completed" else "◐" if status == "reading" else "○"
        lines.append(f"## {status_icon} {name}")
        if i in note_map:
            lines.append("")
            lines.append(note_map[i])
        else:
            lines.append("")
            lines.append("（暂无笔记）")
        lines.append("")

    return "\n".join(lines)
