"""阅读记录 —— 追踪阅读行为，生成统计"""

import json
from datetime import datetime, timedelta
from pathlib import Path

SHELF_DIR = Path(__file__).parent / "shelf"


def log_reading(book_id: str, chapter_idx: int, action: str, detail: str = ""):
    """记录阅读行为：start_chapter, end_chapter, take_note"""
    log_path = SHELF_DIR / book_id / "reading_log.json"

    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
    else:
        log = []

    log.append({
        "book_id": book_id,
        "chapter_idx": chapter_idx,
        "action": action,
        "detail": detail,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": datetime.now().isoformat(),
    })

    # 只保留最近 500 条
    if len(log) > 500:
        log = log[-500:]

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def get_reading_log(book_id: str) -> list:
    """获取某本书的阅读日志"""
    log_path = SHELF_DIR / book_id / "reading_log.json"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_reading_stats() -> dict:
    """全局阅读统计"""
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    total_sessions = 0
    chapters_read = 0
    notes_taken = 0
    weekly_chapters = 0

    for book_dir in SHELF_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        log_path = book_dir / "reading_log.json"
        if not log_path.exists():
            continue

        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)

        for entry in log:
            t = datetime.fromisoformat(entry["timestamp"])
            action = entry.get("action", "")

            if action == "start_chapter":
                total_sessions += 1
                if t > week_ago:
                    weekly_chapters += 1
            elif action == "end_chapter":
                chapters_read += 1
            elif action == "take_note":
                notes_taken += 1

    return {
        "total_sessions": total_sessions,
        "chapters_read": chapters_read,
        "notes_taken": notes_taken,
        "weekly_chapters": weekly_chapters,
    }


def get_book_stats(book_id: str) -> dict:
    """某本书的阅读统计"""
    log = get_reading_log(book_id)
    chapters_touched = set()
    actions_count = {"start_chapter": 0, "end_chapter": 0, "take_note": 0}

    for entry in log:
        action = entry.get("action", "")
        if action in actions_count:
            actions_count[action] += 1
        if "chapter_idx" in entry:
            chapters_touched.add(entry["chapter_idx"])

    # 距离第一次阅读的天数
    first_read = log[0]["time"] if log else ""
    last_read = log[-1]["time"] if log else ""

    return {
        "total_actions": len(log),
        "sessions": actions_count["start_chapter"],
        "notes": actions_count["take_note"],
        "chapters_visited": len(chapters_touched),
        "first_read": first_read,
        "last_read": last_read,
    }
