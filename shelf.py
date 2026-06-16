"""书架管理：CRUD、索引持久化、阅读进度"""

import os
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from book_parser import parse_file

SHELF_DIR = Path(__file__).parent / "shelf"
INDEX_PATH = SHELF_DIR / "index.json"

# 封面颜色池 —— 暖色系
COVER_COLORS = [
    "#e8c3a0", "#d4a574", "#c4956a", "#b8956c", "#a6845c",
    "#d4b896", "#c9a882", "#e0c9a8", "#c49a7c", "#d1b18e",
    "#e2d0b8", "#c5a68c", "#b89070", "#dbc4a4", "#ceb494",
    "#bfa07e", "#dac5a8", "#c8b090", "#e5c9aa", "#c09770",
]


def _ensure_shelf():
    """确保书架目录和索引文件存在"""
    os.makedirs(SHELF_DIR, exist_ok=True)
    if not INDEX_PATH.exists():
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def _load_index() -> list:
    """加载书架索引"""
    _ensure_shelf()
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_index(books: list):
    """保存书架索引"""
    os.makedirs(SHELF_DIR, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)


@st.cache_data(ttl=2, show_spinner=False)
def load_shelf() -> list:
    """获取书架所有书（按添加时间倒序）"""
    books = _load_index()
    if not isinstance(books, list):
        books = []
    books.sort(key=lambda b: b.get("added_at", ""), reverse=True)
    return books


def add_book(file_path: str, custom_title: str = "") -> dict:
    """
    添加一本书到书架
    1. 解析文件
    2. 复制到 shelf/
    3. 保存索引
    返回书的元信息
    """
    parsed = parse_file(file_path)

    book_id = str(uuid.uuid4())[:8]
    detected = parsed["title"]
    # 如果检测到的标题是临时文件名，不用
    if detected.startswith("tmp") and len(detected) < 20:
        detected = ""
    title = custom_title or detected or os.path.splitext(os.path.basename(file_path))[0]
    author = parsed["author"]
    ext = os.path.splitext(file_path)[1]

    # 创建书的专属目录
    book_dir = SHELF_DIR / book_id
    os.makedirs(book_dir, exist_ok=True)

    # 复制原文件
    dst_file = book_dir / f"original{ext}"
    shutil.copy2(file_path, dst_file)

    # 保存全文
    full_text_path = book_dir / "full_text.txt"
    with open(full_text_path, "w", encoding="utf-8") as f:
        f.write(parsed["full_text"])

    # 保存初始对话历史
    history_path = book_dir / "history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump([], f)

    # 自动搜索作者照片
    author_photo = ""
    if author:
        author_photo = _search_author_photo(author, title)

    # 构建书籍元信息
    chapter_count = len(parsed["chapters"])
    color_idx = sum(ord(c) for c in book_id) % len(COVER_COLORS)

    book_info = {
        "id": book_id,
        "title": title,
        "author": author,
        "file_type": ext.lstrip("."),
        "chapter_count": chapter_count,
        "total_chars": len(parsed["full_text"]),
        "current_chapter": 0,
        "progress_pct": 0,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_read_at": "",
        "cover_color": COVER_COLORS[color_idx],
        "author_photo": author_photo,
    }

    # 更新索引
    books = _load_index()
    books.append(book_info)
    _save_index(books)

    return book_info


def get_book(book_id: str) -> dict:
    """获取单本书的元信息 + 章节内容"""
    books = _load_index()
    for b in books:
        if b["id"] == book_id:
            return b
    raise ValueError(f"找不到书籍: {book_id}")


def get_chapters(book_id: str) -> list[dict]:
    """获取书的章节列表（从 full_text.txt 解析）"""
    book_dir = SHELF_DIR / book_id
    text_path = book_dir / "full_text.txt"

    if not text_path.exists():
        return []

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    from book_parser import _split_chapters
    return _split_chapters(text)


def delete_book(book_id: str):
    """从书架删除一本书"""
    books = _load_index()
    books = [b for b in books if b["id"] != book_id]
    _save_index(books)

    # 删除文件
    book_dir = SHELF_DIR / book_id
    if book_dir.exists():
        shutil.rmtree(book_dir)


def save_progress(book_id: str, chapter_idx: int, messages: list):
    """保存阅读进度 + 对话历史（按章节）

    进度按"已完成章节"计算，不是当前章节序号，避免一打开第1章就显示 1%+。
    """
    books = _load_index()
    for b in books:
        if b["id"] == book_id:
            b["current_chapter"] = chapter_idx
            # 进度 = 已完成章节数 / 总章节数
            chapters = load_chapters_with_state(book_id)
            done = sum(1 for c in chapters if c.get("status") == "completed")
            total = max(len(chapters), 1)
            b["progress_pct"] = int(done / total * 100)
            b["last_read_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break
    _save_index(books)

    # 按章节保存对话历史
    history_path = SHELF_DIR / book_id / f"history_{chapter_idx}.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def recompute_progress(book_id: str):
    """重新计算某本书的进度（按已完成章节）。状态变更后调用。"""
    books = _load_index()
    chapters = load_chapters_with_state(book_id)
    done = sum(1 for c in chapters if c.get("status") == "completed")
    total = max(len(chapters), 1)
    pct = int(done / total * 100)
    for b in books:
        if b["id"] == book_id:
            b["progress_pct"] = pct
            break
    _save_index(books)
    return pct


def update_chapter_status(book_id: str, chapter_idx: int, status: str):
    """更新章节状态：unread, reading, completed

    状态变更后自动重算书籍进度。
    """
    chapters_path = SHELF_DIR / book_id / "chapters.json"

    # 加载章节数据
    if not chapters_path.exists():
        chapters = get_chapters(book_id)
    else:
        with open(chapters_path, "r", encoding="utf-8") as f:
            chapters = json.load(f)

    # 更新状态
    if 0 <= chapter_idx < len(chapters):
        chapters[chapter_idx]["status"] = status

    # 保存
    with open(chapters_path, "w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

    # 重算书籍进度
    recompute_progress(book_id)


def toggle_bookmark(book_id: str, chapter_idx: int) -> bool:
    """切换章节书签状态，返回切换后的状态（True=已加书签）"""
    chapters_path = SHELF_DIR / book_id / "chapters.json"

    # 加载章节数据
    if not chapters_path.exists():
        chapters = get_chapters(book_id)
    else:
        with open(chapters_path, "r", encoding="utf-8") as f:
            chapters = json.load(f)

    new_state = False
    if 0 <= chapter_idx < len(chapters):
        new_state = not chapters[chapter_idx].get("bookmarked", False)
        chapters[chapter_idx]["bookmarked"] = new_state

    # 保存
    with open(chapters_path, "w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

    return new_state


def save_chapters(book_id: str, chapters: list):
    """保存章节数据（包括状态、书签等）"""
    chapters_path = SHELF_DIR / book_id / "chapters.json"
    with open(chapters_path, "w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)


def load_chapters_with_state(book_id: str) -> list:
    """加载章节数据（包含状态和书签）"""
    chapters_path = SHELF_DIR / book_id / "chapters.json"
    
    if chapters_path.exists():
        with open(chapters_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # 首次加载，从文本解析
        chapters = get_chapters(book_id)
        save_chapters(book_id, chapters)
        return chapters


def load_history(book_id: str, chapter_idx: int = 0) -> list:
    """加载某章节的对话历史"""
    history_path = SHELF_DIR / book_id / f"history_{chapter_idx}.json"
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_custom_prompt(book_id: str) -> str:
    """获取某本书的自定义提示词，没有则返回空"""
    path = SHELF_DIR / book_id / "custom_prompt.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def save_custom_prompt(book_id: str, prompt: str):
    """保存自定义提示词"""
    path = SHELF_DIR / book_id / "custom_prompt.txt"
    path.write_text(prompt, encoding="utf-8")


def update_book_meta(book_id: str, key: str, value):
    """更新书籍元信息中的某个字段"""
    books = _load_index()
    for b in books:
        if b["id"] == book_id:
            b[key] = value
            break
    _save_index(books)


def _search_author_photo(author: str, book_title: str) -> str:
    """作者头像 —— 返回空字符串，由前端用首字母圆头像渲染

    （旧版生成 SVG data-URI 在 Streamlit chat_message 里渲染不稳定，已弃用。
    保留函数签名是为了向后兼容旧书架数据。）
    """
    return ""


@st.cache_data(ttl=3, show_spinner=False)
def get_bookshelf_stats() -> dict:
    """书架统计（含每本书的章节完成数）"""
    books = _load_index()
    total_chars = sum(b.get("total_chars", 0) for b in books)
    reading = sum(1 for b in books if 0 < b.get("progress_pct", 0) < 100)
    completed = sum(1 for b in books if b.get("progress_pct", 0) >= 100)
    return {
        "total_books": len(books),
        "total_chars": total_chars,
        "reading": reading,
        "completed": completed,
    }


@st.cache_data(ttl=2, show_spinner=False)
def get_book_chapter_stats(book_id: str) -> dict:
    """某本书的章节状态统计：完成数 / 在读数 / 书签数"""
    chapters = load_chapters_with_state(book_id)
    total = len(chapters)
    done = sum(1 for c in chapters if c.get("status") == "completed")
    reading = sum(1 for c in chapters if c.get("status") == "reading")
    bookmarked = sum(1 for c in chapters if c.get("bookmarked"))
    return {
        "total": total,
        "completed": done,
        "reading": reading,
        "unread": total - done - reading,
        "bookmarked": bookmarked,
    }


def get_author_initial(author: str) -> str:
    """取作者姓名首字，用于生成头像"""
    if not author:
        return "书"
    return author[0]


def get_author_avatar_color(author: str) -> str:
    """根据作者名生成稳定的深色背景色（用于首字头像）"""
    import hashlib
    if not author:
        author = "book"
    hue = int(hashlib.md5(author.encode()).hexdigest()[:2], 16) % 360
    # 用 HSL 生成较深的色（亮度 35%），白字可见
    return f"hsl({hue}, 45%, 38%)"
