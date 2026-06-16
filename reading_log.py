"""阅读记录 —— 追踪阅读行为、统计阅读时长

时长计算逻辑：
- 进入章节时记一条 start_chapter（带 timestamp）
- 离开/切换章节时记一条 end_chapter，并写入 duration_sec（秒）
- 多次进出同一章节会累加，所以 get_reading_duration 会按章节聚合
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

SHELF_DIR = Path(__file__).parent / "shelf"


def log_reading(
    book_id: str,
    chapter_idx: int,
    action: str,
    detail: str = "",
    duration_sec: float = 0,
):
    """记录阅读行为。

    action: start_chapter / end_chapter / take_note / mark_bookmark
    duration_sec: 仅 end_chapter 使用，本次停留秒数
    """
    log_path = SHELF_DIR / book_id / "reading_log.json"

    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
    else:
        log = []

    now = datetime.now()
    log.append(
        {
            "book_id": book_id,
            "chapter_idx": chapter_idx,
            "action": action,
            "detail": detail,
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": now.isoformat(),
            "duration_sec": round(duration_sec, 1) if duration_sec else 0,
        }
    )

    # 只保留最近 1000 条
    if len(log) > 1000:
        log = log[-1000:]

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def get_reading_log(book_id: str) -> list:
    """获取某本书的阅读日志"""
    log_path = SHELF_DIR / book_id / "reading_log.json"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _fmt_duration(seconds: float) -> str:
    """把秒数格式化成 '5h23m' / '12m' / '45s' 这种紧凑形式"""
    if not seconds or seconds < 1:
        return "0m"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h{m:02d}m"
    if m > 0:
        return f"{m}m"
    return f"{s}s"


@st.cache_data(ttl=3, show_spinner=False)
def get_reading_duration(book_id: str) -> dict:
    """某本书的阅读时长统计

    返回:
      {
        "total_sec": 累计秒数,
        "total_fmt": "5h23m",
        "by_chapter": {chapter_idx: 秒数, ...},
        "first_read": "2026-06-08 04:02:45",
        "last_read": "2026-06-08 04:10:00",
      }
    """
    log = get_reading_log(book_id)
    total_sec = 0.0
    by_chapter = {}
    first_read = ""
    last_read = ""

    for entry in log:
        action = entry.get("action", "")
        ts = entry.get("time", "")
        if ts:
            if not first_read:
                first_read = ts
            last_read = ts

        if action == "end_chapter" and entry.get("duration_sec"):
            dur = float(entry["duration_sec"])
            total_sec += dur
            ch = entry.get("chapter_idx", 0)
            by_chapter[ch] = by_chapter.get(ch, 0) + dur
        elif action == "start_chapter" and entry.get("duration_sec"):
            # 兼容：如果 start 已带 duration（旧版写入），也算上
            dur = float(entry["duration_sec"])
            total_sec += dur

    return {
        "total_sec": total_sec,
        "total_fmt": _fmt_duration(total_sec),
        "by_chapter": by_chapter,
        "first_read": first_read,
        "last_read": last_read,
    }


@st.cache_data(ttl=5, show_spinner=False)
def get_total_duration() -> dict:
    """全站阅读时长统计"""
    total_sec = 0.0
    weekly_sec = 0.0
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    if not SHELF_DIR.exists():
        return {"total_sec": 0, "total_fmt": "0m", "weekly_sec": 0, "weekly_fmt": "0m"}

    for book_dir in SHELF_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        log_path = book_dir / "reading_log.json"
        if not log_path.exists():
            continue
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            continue

        for entry in log:
            if entry.get("action") == "end_chapter" and entry.get("duration_sec"):
                dur = float(entry["duration_sec"])
                total_sec += dur
                try:
                    t = datetime.fromisoformat(entry["timestamp"])
                    if t > week_ago:
                        weekly_sec += dur
                except Exception:
                    pass

    return {
        "total_sec": total_sec,
        "total_fmt": _fmt_duration(total_sec),
        "weekly_sec": weekly_sec,
        "weekly_fmt": _fmt_duration(weekly_sec),
    }


@st.cache_data(ttl=3, show_spinner=False)
def get_reading_stats() -> dict:
    """全局阅读统计（动作计数 + 时长 + 本周章节）"""
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    total_sessions = 0
    chapters_read = 0
    notes_taken = 0
    weekly_chapters = 0
    total_sec = 0.0
    weekly_sec = 0.0

    if not SHELF_DIR.exists():
        return _empty_stats()

    for book_dir in SHELF_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        log_path = book_dir / "reading_log.json"
        if not log_path.exists():
            continue
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            continue

        for entry in log:
            action = entry.get("action", "")
            try:
                t = datetime.fromisoformat(entry.get("timestamp", ""))
            except Exception:
                t = now

            if action == "start_chapter":
                total_sessions += 1
                if t > week_ago:
                    weekly_chapters += 1
            elif action == "end_chapter":
                chapters_read += 1
                dur = float(entry.get("duration_sec", 0) or 0)
                total_sec += dur
                if t > week_ago:
                    weekly_sec += dur
            elif action == "take_note":
                notes_taken += 1

    return {
        "total_sessions": total_sessions,
        "chapters_read": chapters_read,
        "notes_taken": notes_taken,
        "weekly_chapters": weekly_chapters,
        "weekly_chapters_in_progress": 0,  # 保留向后兼容
        "total_sec": total_sec,
        "total_fmt": _fmt_duration(total_sec),
        "weekly_sec": weekly_sec,
        "weekly_fmt": _fmt_duration(weekly_sec),
    }


def _empty_stats() -> dict:
    return {
        "total_sessions": 0,
        "chapters_read": 0,
        "notes_taken": 0,
        "weekly_chapters": 0,
        "weekly_chapters_in_progress": 0,
        "total_sec": 0,
        "total_fmt": "0m",
        "weekly_sec": 0,
        "weekly_fmt": "0m",
    }


def get_book_stats(book_id: str) -> dict:
    """某本书的阅读统计"""
    log = get_reading_log(book_id)
    chapters_touched = set()
    actions_count = {"start_chapter": 0, "end_chapter": 0, "take_note": 0}
    total_sec = 0.0

    for entry in log:
        action = entry.get("action", "")
        if action in actions_count:
            actions_count[action] += 1
        if action == "end_chapter" and entry.get("duration_sec"):
            total_sec += float(entry["duration_sec"])
        if "chapter_idx" in entry:
            chapters_touched.add(entry["chapter_idx"])

    first_read = log[0]["time"] if log else ""
    last_read = log[-1]["time"] if log else ""

    return {
        "total_actions": len(log),
        "sessions": actions_count["start_chapter"],
        "notes": actions_count["take_note"],
        "chapters_visited": len(chapters_touched),
        "first_read": first_read,
        "last_read": last_read,
        "total_sec": total_sec,
        "total_fmt": _fmt_duration(total_sec),
    }


@st.cache_data(ttl=5, show_spinner=False)
def get_weekly_chart_data(book_id: str = None) -> list:
    """最近 7 天每天的阅读时长（秒），用于条形图

    返回: [{"date": "06-08", "weekday": "周一", "sec": 1234}, ...]
    """
    today = datetime.now().date()
    days = []
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        days.append(
            {
                "date": d.strftime("%m-%d"),
                "weekday": weekday_names[d.weekday()],
                "sec": 0,
                "_iso": d.isoformat(),
            }
        )

    # 收集日志
    if book_id:
        logs = [(book_id, get_reading_log(book_id))]
    else:
        logs = []
        if SHELF_DIR.exists():
            for book_dir in SHELF_DIR.iterdir():
                if not book_dir.is_dir():
                    continue
                lp = book_dir / "reading_log.json"
                if lp.exists():
                    try:
                        with open(lp, "r", encoding="utf-8") as f:
                            logs.append((book_dir.name, json.load(f)))
                    except Exception:
                        pass

    day_map = {d["_iso"]: d for d in days}
    for _, log in logs:
        for entry in log:
            if entry.get("action") != "end_chapter":
                continue
            dur = float(entry.get("duration_sec", 0) or 0)
            if not dur:
                continue
            try:
                d = datetime.fromisoformat(entry["timestamp"]).date().isoformat()
            except Exception:
                continue
            if d in day_map:
                day_map[d]["sec"] += dur

    # 去掉内部字段
    return [{k: v for k, v in d.items() if k != "_iso"} for d in days]
