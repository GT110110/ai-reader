"""阅伴 —— 上传一本书，AI 扮演作者逐章带你阅读

v3.0 现代极简重构：
- 设计系统：浅/深双主题，CSS 变量驱动，思源黑体
- 修复缺失功能：目录搜索 / 书签筛选 / 章节统计 / 长目录折叠
- 进度计算：按已完成章节，不再"一打开就 1%"
- 阅读体验：全宽阅读区 + 抽屉式笔记 + 金句收藏
- 阅读时长：自动统计，书架/目录展示
"""

import os
import time
import tempfile
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from shelf import (
    load_shelf,
    add_book,
    get_book,
    delete_book,
    save_progress,
    load_history,
    load_chapters_with_state,
    save_chapters,
    update_chapter_status,
    toggle_bookmark,
    get_custom_prompt,
    save_custom_prompt,
    update_book_meta,
    recompute_progress,
    get_bookshelf_stats,
    get_book_chapter_stats,
)
from reader import start_chapter, continue_chat, start_article
from prompt import build_overview_prompt, READING_MODES
from notes import (
    save_note,
    load_note,
    export_book_notes,
    get_all_notes,
    save_quote,
    get_quotes,
    delete_quote,
)
from reading_log import (
    log_reading,
    get_reading_stats,
    get_reading_duration,
    get_total_duration,
    get_weekly_chart_data,
)
from styles import get_css

load_dotenv()

SHELF_DIR = Path(__file__).parent / "shelf"
THEME_PATH = SHELF_DIR / "theme.json"

st.set_page_config(
    page_title="阅伴",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# CSS 从 styles.py 导入（见文件顶部 import）
# ═══════════════════════════════════════════════════════════════
# 主题管理
# ═══════════════════════════════════════════════════════════════
def load_theme() -> str:
    """从本地文件加载主题偏好，默认 light"""
    try:
        if THEME_PATH.exists():
            data = json.loads(THEME_PATH.read_text(encoding="utf-8"))
            return data.get("theme", "light")
    except Exception:
        pass
    return "light"


def save_theme(theme: str):
    """持久化主题"""
    try:
        SHELF_DIR.mkdir(exist_ok=True)
        THEME_PATH.write_text(
            json.dumps({"theme": theme}), encoding="utf-8"
        )
    except Exception:
        pass


def apply_theme():
    """注入主题到 html 根元素"""
    theme = st.session_state.get("theme", "light")
    st.markdown(
        f"""
        <script>
            document.documentElement.setAttribute('data-theme', '{theme}');
            try {{ localStorage.setItem('ai-reader-theme', '{theme}'); }} catch(e) {{}}
        </script>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
# Session state
# ═══════════════════════════════════════════════════════════════
def init_session():
    defaults = {
        "current_view": "shelf",
        "current_book_id": None,
        "messages": [],
        "chapters": [],
        "current_chapter": 0,
        "paste_messages": [],
        "toc_search": "",
        "toc_bookmark_only": False,
        "show_notes_drawer": False,
        "show_quotes_view": False,
        "chapter_enter_time": None,  # 进入章节的时间戳，用于算时长
        "sort_by": "added",  # shelf 排序：added / progress / title
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if "theme" not in st.session_state:
        st.session_state["theme"] = load_theme()


init_session()
st.markdown(get_css(), unsafe_allow_html=True)
apply_theme()


# ═══════════════════════════════════════════════════════════════
# 头像取值（防御性：永远返回 Streamlit 能渲染的合法头像）
# ═══════════════════════════════════════════════════════════════
# 关键：Streamlit 的 chat_message(avatar=...) 只接受三种值：
#   1. 单个 emoji（如 "📖"）
#   2. 已注册的 icon 名（如 ":material/person:"）
#   3. 图片（PIL Image / BytesIO / URL / 本地路径）
# 中文字符（"王"）和字母（"A"）都不是 emoji，会被当 URL 加载 → 报错！
# 所以我们用 PIL 动态生成首字头像 PNG，永远安全。
_AVATAR_CACHE = {}  # 缓存生成的头像，避免重复渲染


def _safe_avatar(author: str | None):
    """生成作者头像。

    返回 PIL Image（首字+背景色），永远可被 Streamlit 渲染。
    作者名空时返回 📖 emoji。
    """
    import re
    # 取作者名首个"正经字符"
    if not author:
        return "📖"
    m = re.search(r"\w", author)
    if not m:
        return "📖"
    char = m.group()

    # 缓存命中
    if char in _AVATAR_CACHE:
        return _AVATAR_CACHE[char]

    try:
        from PIL import Image, ImageDraw, ImageFont
        import hashlib

        # 用字符生成稳定的背景色（深色，白字可见）
        hue = int(hashlib.md5(char.encode()).hexdigest()[:2], 16)
        bg = _hsl_to_rgb(hue % 360, 0.45, 0.38)

        size = 128
        img = Image.new("RGB", (size, size), tuple(bg))
        draw = ImageDraw.Draw(img)

        # 找一个能渲染中文的字体
        font = _find_cjk_font(size)
        if font:
            # 测量并居中
            try:
                bbox = draw.textbbox((0, 0), char, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (size - w) / 2 - bbox[0]
                y = (size - h) / 2 - bbox[1]
            except Exception:
                x, y = size / 2 - 30, size / 2 - 50
            draw.text((x, y), char, fill="white", font=font)
        else:
            # 无中文字体，画 emoji 兜底
            return "📖"

        _AVATAR_CACHE[char] = img
        return img
    except Exception:
        return "📖"


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple:
    """HSL 转 RGB（h: 0-360, s/l: 0-1）"""
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def _find_cjk_font(size: int):
    """找一个能渲染中文的系统字体"""
    from PIL import ImageFont
    import os
    # 常见中文字体路径（Linux/macOS/Windows）
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=72)
            except Exception:
                continue
    return None


# ═══════════════════════════════════════════════════════════════
# API key（优先 Streamlit Secrets，兼容本地 .env）
# ═══════════════════════════════════════════════════════════════
def _get_api_key() -> str | None:
    try:
        return st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        return os.getenv("DEEPSEEK_API_KEY")

if not _get_api_key():
    with st.sidebar:
        st.warning("⚠️ 未配置 API Key")
        key_in = st.text_input("DeepSeek API Key", type="password")
        if key_in:
            os.environ["DEEPSEEK_API_KEY"] = key_in
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# 公共组件
# ═══════════════════════════════════════════════════════════════
def render_app_header(show_back: bool = False, back_label: str = "返回"):
    """统一的顶部 Header"""
    left = st.container()
    with left:
        cols = st.columns([1, 6, 1]) if not show_back else st.columns([1, 5, 1])
        with cols[0]:
            if show_back:
                if st.button("← " + back_label, key=f"back_{st.session_state.current_view}",
                             use_container_width=True):
                    return True  # 触发返回
        with cols[1]:
            st.markdown(
                f"""
                <div class="app-header" style="border:none;margin:0;padding:0.3rem 0;">
                    <div class="brand">
                        <div class="logo">阅</div>
                        <div>
                            <div class="brand-name">阅伴</div>
                            <div class="brand-sub">AI 陪你读懂每一本好书</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cols[2]:
            theme = st.session_state.get("theme", "light")
            icon = "🌙" if theme == "light" else "☀️"
            if st.button(icon, key="theme_toggle", use_container_width=True,
                         help="切换主题"):
                new_theme = "dark" if theme == "light" else "light"
                st.session_state["theme"] = new_theme
                save_theme(new_theme)
                st.rerun()
    return False


def render_stats_bar(items: list):
    """通用统计条 items: [(value, label), ...]"""
    cells = "".join(
        f'<div class="stat-item"><div class="stat-value">{v}</div>'
        f'<div class="stat-label">{l}</div></div>'
        for v, l in items
    )
    st.markdown(f'<div class="stats-bar">{cells}</div>', unsafe_allow_html=True)


def progress_ring_svg(pct: int, size: str = "sm", label: str = "") -> str:
    """生成环形进度 SVG HTML。

    pct: 0-100
    size: "sm"（书卡，48px）或 "lg"（阅读页，72px）
    label: 环下方的小标签
    """
    import math
    if size == "lg":
        dim, stroke = 72, 6
    else:
        dim, stroke = 48, 4
    radius = (dim - stroke) / 2 - 1
    circumference = 2 * math.pi * radius
    # pct 映射到 dashoffset
    offset = circumference * (1 - max(0, min(100, pct)) / 100)
    text_size = dim * 0.28
    label_html = f'<span class="ring-label">{label}</span>' if label else ''
    return f"""
    <div class="progress-ring {size}" style="width:{dim}px;height:{dim}px;">
        <svg width="{dim}" height="{dim}">
            <circle class="ring-bg" cx="{dim/2}" cy="{dim/2}" r="{radius}" stroke-width="{stroke}"/>
            <circle class="ring-fill" cx="{dim/2}" cy="{dim/2}" r="{radius}" stroke-width="{stroke}"
                stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}"/>
        </svg>
        <span class="ring-text" style="font-size:{text_size}px;">{pct}%</span>
        {label_html}
    </div>
    """


def get_overview(book_id: str, book_title: str, chapters: list) -> str:
    """获取或生成书籍导读（持久化）"""
    overview_path = SHELF_DIR / book_id / "overview.txt"
    if overview_path.exists():
        return overview_path.read_text(encoding="utf-8")

    # 生成
    try:
        sample = "\n\n".join(
            f"《{ch['name']}》: {ch['text'][:500]}" for ch in chapters[:10]
        )
        from reader import _get_client
        client = _get_client()
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": build_overview_prompt(book_title, sample[:5000])}],
            temperature=0.5,
            max_tokens=600,
        )
        overview = resp.choices[0].message.content
        overview_path.parent.mkdir(exist_ok=True, parents=True)
        overview_path.write_text(overview, encoding="utf-8")
        return overview
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# 路由
# ═══════════════════════════════════════════════════════════════
def end_current_chapter_session(book_id: str, chapter_idx: int, chapter_name: str):
    """离开当前章节时，结算阅读时长并记日志"""
    enter_time = st.session_state.get("chapter_enter_time")
    duration = 0
    if enter_time:
        duration = (datetime.now() - enter_time).total_seconds()
        st.session_state["chapter_enter_time"] = None
    log_reading(book_id, chapter_idx, "end_chapter",
                detail=chapter_name, duration_sec=duration)


def switch_to_toc(book_id: str):
    # 如果正在阅读某章，先结算时长
    if st.session_state.current_view == "reading" and st.session_state.current_book_id:
        end_current_chapter_session(
            st.session_state.current_book_id,
            st.session_state.current_chapter,
            st.session_state.chapters[st.session_state.current_chapter]["name"]
            if st.session_state.chapters else "",
        )
    st.session_state.current_view = "toc"
    st.session_state.current_book_id = book_id
    st.session_state.chapters = load_chapters_with_state(book_id)
    st.session_state.show_quotes_view = False
    st.rerun()


def switch_to_reading(book_id: str, chapter_idx: int):
    # 结算上一个章节（如果有）
    if (st.session_state.current_view == "reading"
            and st.session_state.chapter_enter_time
            and st.session_state.current_book_id == book_id
            and st.session_state.current_chapter != chapter_idx):
        old_idx = st.session_state.current_chapter
        if st.session_state.chapters and old_idx < len(st.session_state.chapters):
            end_current_chapter_session(book_id, old_idx, st.session_state.chapters[old_idx]["name"])
        else:
            st.session_state.chapter_enter_time = None

    st.session_state.current_view = "reading"
    st.session_state.current_book_id = book_id
    st.session_state.chapters = load_chapters_with_state(book_id)
    st.session_state.current_chapter = chapter_idx
    st.session_state.messages = load_history(book_id, chapter_idx)
    st.session_state.chapter_enter_time = datetime.now()
    st.session_state.show_notes_drawer = False
    update_chapter_status(book_id, chapter_idx, "reading")
    log_reading(book_id, chapter_idx, "start_chapter",
                detail=st.session_state.chapters[chapter_idx]["name"])
    st.rerun()


def switch_to_shelf():
    if st.session_state.current_view == "reading":
        end_current_chapter_session(
            st.session_state.current_book_id,
            st.session_state.current_chapter,
            st.session_state.chapters[st.session_state.current_chapter]["name"]
            if st.session_state.chapters else "",
        )
    st.session_state.current_view = "shelf"
    st.session_state.current_book_id = None
    st.session_state.messages = []
    st.session_state.show_quotes_view = False
    st.rerun()


# ═══════════════════════════════════════════════════════════════
# VIEW: 书架
# ═══════════════════════════════════════════════════════════════
def render_shelf():
    if render_app_header():
        pass

    books = load_shelf()
    stats = get_reading_stats()
    bs_stats = get_bookshelf_stats()
    dur = get_total_duration()

    # 统计条
    if books:
        render_stats_bar([
            (len(books), "书架"),
            (bs_stats["reading"], "在读"),
            (bs_stats["completed"], "已完成"),
            (stats["weekly_chapters"], "本周章节"),
            (dur["total_fmt"], "累计时长"),
        ])

    # 统计页入口（统计条右侧）
    stat_btn_col, _ = st.columns([1, 5])
    with stat_btn_col:
        if st.button("📊 阅读统计", key="goto_stats", use_container_width=True):
            st.session_state.current_view = "stats"
            st.rerun()

    # 空状态
    if not books:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📚</div>
            <h2>书架空空如也</h2>
            <p>上传一本书，让 AI 扮演作者逐章带你阅读</p>
        </div>
        """, unsafe_allow_html=True)

    # 上传区
    with st.expander("＋ 添加新书", expanded=not books):
        c_up, c_title, _ = st.columns([2, 2, 1])
        with c_up:
            uploaded = st.file_uploader(
                "上传 PDF 或 TXT",
                type=["pdf", "txt"],
                label_visibility="collapsed",
                key="shelf_upload",
            )
        with c_title:
            custom_title = st.text_input(
                "书名（留空自动识别）",
                placeholder="留空自动识别",
                label_visibility="collapsed",
            )
        if uploaded and st.button("添加到书架", type="primary", use_container_width=True):
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            try:
                fallback = custom_title or os.path.splitext(uploaded.name)[0]
                with st.spinner("正在解析书籍..."):
                    book = add_book(tmp_path, fallback)
                os.unlink(tmp_path)
                chs = load_chapters_with_state(book["id"])
                save_chapters(book["id"], chs)
                st.success(f"已添加《{book['title']}》")
                time.sleep(0.6)
                switch_to_toc(book["id"])
            except Exception as e:
                st.error(f"添加失败：{e}")

    # 排序
    if books:
        s_col, _ = st.columns([1, 4])
        with s_col:
            sort_options = ["最近添加", "按进度", "按书名"]
            current = st.session_state.get("sort_by", "added")
            default_idx = {"added": 0, "progress": 1, "title": 2}.get(current, 0)
            sort_label = st.selectbox(
                "排序",
                options=sort_options,
                index=default_idx,
                key="sort_select",
            )
            # 把显示标签映射回内部 key
            label_to_key = {"最近添加": "added", "按进度": "progress", "按书名": "title"}
            st.session_state.sort_by = label_to_key[sort_label]

        sort_key = st.session_state.sort_by
        if sort_key == "progress":
            books.sort(key=lambda b: b.get("progress_pct", 0), reverse=True)
        elif sort_key == "title":
            books.sort(key=lambda b: b.get("title", ""))
        # added 已经是默认倒序

        # 书卡网格
        spine_colors = ["var(--spine-1)", "var(--spine-2)", "var(--spine-3)", "var(--spine-4)"]
        cols = st.columns(3)
        for i, book in enumerate(books):
            with cols[i % 3]:
                pct = book.get("progress_pct", 0)
                last = book.get("last_read_at", "")
                last_str = f"上次：{last[5:]}" if last else "未开始"
                ch_count = book.get("chapter_count", 0)
                spine = spine_colors[i % len(spine_colors)]
                icon = "✅" if pct >= 100 else "📖" if pct > 0 else "📕"

                st.markdown(f"""
                <div class="book-card">
                    <div class="spine" style="background:{spine};"></div>
                    <div class="book-title">{icon} {book['title']}</div>
                    <div class="book-author">{book['author'] or '未知作者'}</div>
                    <div class="progress-row">
                        <div class="progress-track">
                            <div class="progress-fill" style="width:{pct}%;"></div>
                        </div>
                        <span class="progress-pct">{pct}%</span>
                    </div>
                    <div class="card-meta">
                        <span>{ch_count} 章</span>
                        <span>{last_str}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                bc, dc = st.columns([4, 1])
                with bc:
                    if st.button(
                        "继续阅读" if pct > 0 else "开始阅读",
                        key=f"read_{book['id']}",
                        use_container_width=True,
                        type="primary" if pct == 0 else "secondary",
                    ):
                        switch_to_toc(book["id"])
                with dc:
                    if st.button("🗑", key=f"del_{book['id']}", help="删除"):
                        delete_book(book["id"])
                        st.rerun()


# ═══════════════════════════════════════════════════════════════
# VIEW: 目录
# ═══════════════════════════════════════════════════════════════
def render_toc():
    book_id = st.session_state.current_book_id
    if not book_id:
        switch_to_shelf()
        return
    try:
        book = get_book(book_id)
    except ValueError:
        switch_to_shelf()
        return

    # 金句本视图
    if st.session_state.get("show_quotes_view"):
        render_quotes_view(book)
        return

    chapters = st.session_state.chapters

    # Header
    if render_app_header(show_back=True, back_label="书架"):
        switch_to_shelf()
        return

    # 书名信息条
    c1, c2 = st.columns([6, 1])
    with c1:
        st.markdown(f"""
        <div style="margin-bottom:0.5rem;">
            <h1 style="margin:0 0 0.3rem;">《{book['title']}》</h1>
            <div style="color:var(--text-tertiary);font-size:0.85rem;">
                {book['author'] or '未知作者'} · {book.get('chapter_count', len(chapters))} 章 · {book['total_chars']:,} 字
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        pct = book.get("progress_pct", 0)
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;padding-top:0.3rem;">'
            f'{progress_ring_svg(pct, size="lg", label="已读")}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 章节状态统计胶囊
    cs = get_book_chapter_stats(book_id)
    st.markdown(f"""
    <div class="chapter-stats">
        <span class="stat-pill reading"><span class="pill-dot"></span>在读 {cs['reading']}</span>
        <span class="stat-pill done"><span class="pill-dot"></span>已完成 {cs['completed']}</span>
        <span class="stat-pill"><span class="pill-dot" style="background:var(--border-strong);"></span>未读 {cs['unread']}</span>
        <span class="stat-pill bookmark"><span class="pill-dot"></span>书签 {cs['bookmarked']}</span>
    </div>
    """, unsafe_allow_html=True)

    # 继续阅读（基于上次阅读位置，而非进度百分比，避免进度=0时不显示）
    last_ch = book.get("current_chapter", 0)
    has_history = bool(book.get("last_read_at")) or book.get("progress_pct", 0) > 0
    if has_history and last_ch < len(chapters):
        if st.button(
            f"📍 从第 {last_ch + 1} 章继续：{chapters[last_ch]['name']}",
            type="primary",
            use_container_width=True,
        ):
            switch_to_reading(book_id, last_ch)

    # 工具栏：搜索 + 书签筛选 + 金句本入口
    tool_cols = st.columns([3, 1, 1])
    with tool_cols[0]:
        search = st.text_input(
            "🔍 搜索章节",
            value=st.session_state.toc_search,
            placeholder="输入章节名关键词...",
            label_visibility="collapsed",
            key="toc_search_input",
        )
        st.session_state.toc_search = search
    with tool_cols[1]:
        bookmark_only = st.checkbox(
            "⭐ 仅看书签",
            value=st.session_state.toc_bookmark_only,
        )
        st.session_state.toc_bookmark_only = bookmark_only
    with tool_cols[2]:
        quotes = get_quotes(book_id)
        if st.button(f"💎 金句本 ({len(quotes)})", use_container_width=True):
            st.session_state.show_quotes_view = True
            st.rerun()

    # 导读（首次访问时自动生成并缓存）
    overview_path = SHELF_DIR / book_id / "overview.txt"
    if overview_path.exists():
        overview = get_overview(book_id, book['title'], chapters)
    else:
        with st.spinner("✍️ AI 正在撰写本书导读..."):
            overview = get_overview(book_id, book['title'], chapters)
    if overview:
        st.markdown(
            f'<div class="overview-box">{overview.replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )
        oc1, _ = st.columns([1, 4])
        with oc1:
            if st.button("🔄 重新生成导读", key=f"regen_overview_{book_id}"):
                p = SHELF_DIR / book_id / "overview.txt"
                if p.exists():
                    p.unlink()
                st.rerun()

    # 导出 & 设置
    with st.expander("⚙️ 设置 · 导出"):
        # 导出全书笔记
        all_notes = get_all_notes(book_id)
        if all_notes or quotes:
            md = export_book_notes(book_id, book['title'], chapters)
            st.download_button(
                "📥 导出全书笔记（Markdown）",
                md,
                f"{book['title']}_笔记.md",
                "text/markdown",
                use_container_width=True,
            )

        st.divider()

        # 作者头像首字（提示用）
        st.caption("**作者名**：用于 AI 对话头像")
        author_input = st.text_input(
            "作者名",
            value=book.get("author", ""),
            key=f"author_{book_id}",
        )
        if st.button("💾 保存作者名", key=f"save_author_{book_id}"):
            update_book_meta(book_id, "author", author_input)
            st.success("已保存")
            time.sleep(0.5)
            st.rerun()

        st.divider()

        # 阅读模式（预设风格，普通用户免写 prompt）
        st.caption("**阅读模式**：选择 AI 的讲解风格")
        current_mode = book.get("reading_mode", "default")
        mode_names = [m["name"] for m in READING_MODES]
        mode_ids = [m["id"] for m in READING_MODES]
        try:
            default_idx = mode_ids.index(current_mode)
        except ValueError:
            default_idx = 0
        selected = st.selectbox(
            "模式",
            options=mode_names,
            index=default_idx,
            format_func=lambda x: x,
            key=f"mode_select_{book_id}",
        )
        selected_id = mode_ids[mode_names.index(selected)]
        # 显示模式描述
        selected_mode = next(m for m in READING_MODES if m["id"] == selected_id)
        st.caption(f"_{selected_mode['desc']}_")
        if selected_id != current_mode:
            if st.button("💾 应用此模式", key=f"save_mode_{book_id}", type="primary",
                         use_container_width=True):
                update_book_meta(book_id, "reading_mode", selected_id)
                st.success("已应用")
                time.sleep(0.5)
                st.rerun()

        st.divider()

        # 自定义提示词
        st.caption("**伴读风格**（留空使用默认）· 变量：`{book_title}` `{author}` `{chapter_name}` `{chapter_text}`")
        saved_prompt = get_custom_prompt(book_id)
        custom_prompt = st.text_area(
            "提示词",
            value=saved_prompt,
            placeholder="例：你是一个毒舌书评人，用犀利幽默的语言逐章点评《{book_title}》。",
            height=120,
            key=f"prompt_toc_{book_id}",
        )
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("💾 保存提示词", use_container_width=True, key=f"save_prompt_toc_{book_id}"):
                save_custom_prompt(book_id, custom_prompt)
                st.success("已保存")
                time.sleep(0.5)
                st.rerun()
        with pc2:
            if st.button("🔄 恢复默认", use_container_width=True, key=f"reset_prompt_toc_{book_id}"):
                save_custom_prompt(book_id, "")
                st.success("已恢复默认")
                time.sleep(0.5)
                st.rerun()

    # ── 章节列表（带搜索、书签筛选、长目录分组）──
    st.markdown("<h3 style='margin-top:1.5rem;'>📑 目录</h3>", unsafe_allow_html=True)

    # 过滤
    filtered = []
    for i, ch in enumerate(chapters):
        name = ch.get("name", "")
        if st.session_state.toc_search and st.session_state.toc_search.lower() not in name.lower():
            continue
        if st.session_state.toc_bookmark_only and not ch.get("bookmarked"):
            continue
        filtered.append((i, ch))

    if not filtered:
        st.info("没有匹配的章节")
    else:
        _render_chapter_list(book_id, filtered, chapters)

    # 粘贴模式入口
    st.divider()
    if st.button("📋 切换到粘贴文本模式", use_container_width=True):
        st.session_state.current_view = "paste"
        st.rerun()


def _smart_group_chapters(filtered: list, group_size: int = 10) -> list:
    """智能分组章节。

    策略：
    1. 先尝试按"第X部/卷/篇"语义分组
    2. 但要校验：组数必须明显少于章节数（≤ 1/3）才算有效语义分组，
       否则像"第1部分 第2部分..."这种每章都命中的会被当成普通章节
    3. 校验失败回退到固定每 N 章一组

    filtered 形如 [(chapter_idx, chapter_dict), ...]
    返回: [(group_name, [(chapter_idx, chapter_dict), ...]), ...]
    """
    import re

    n_total = len(filtered)

    # ── 语义分组尝试 ──
    group_pattern = re.compile(r"第[零一二三四五六七八九十百千\d]+[部卷篇]")
    semantic_groups = []
    current_group = None
    current_items = []

    for i, ch in filtered:
        name = ch.get("name", "")
        m = group_pattern.match(name)
        # 只有当组名变化时才开新组（避免"第1部分 第2部分"每章一组）
        if m and m.group() != current_group:
            if current_items:
                semantic_groups.append((current_group, current_items))
            current_group = m.group()
            current_items = [(i, ch)]
        else:
            current_items.append((i, ch))

    if current_items:
        semantic_groups.append((current_group, current_items))

    # ── 校验语义分组是否有效 ──
    # 有效条件：至少 2 组，且组数 ≤ 章节数的 1/3（说明分组确实合并了章节）
    if (len(semantic_groups) >= 2
            and len(semantic_groups) <= max(2, n_total / 3)
            and any(len(items) >= 2 for _, items in semantic_groups)):
        result = []
        for gname, items in semantic_groups:
            if gname is None:
                gname = "开头"
            result.append((gname, items))
        return result

    # ── 回退：固定每 N 章一组，组名用章节序号范围 ──
    groups = []
    for start in range(0, n_total, group_size):
        chunk = filtered[start:start + group_size]
        first_no = chunk[0][0] + 1  # chapter_idx 是 0-based，显示用 1-based
        last_no = chunk[-1][0] + 1
        if first_no == last_no:
            name = f"第 {first_no} 章"
        else:
            name = f"第 {first_no}–{last_no} 章"
        groups.append((name, chunk))
    return groups


def _render_chapter_list(book_id: str, filtered: list, all_chapters: list):
    """渲染章节列表，长目录自动分组折叠"""
    # 笔记索引
    note_indices = {n["chapter_idx"] for n in get_all_notes(book_id)}

    # 是否需要分组：章节 >= 15 且未搜索时分组
    need_group = (
        len(filtered) >= 15
        and not st.session_state.toc_search
        and not st.session_state.toc_bookmark_only
    )

    if not need_group:
        _render_chapter_rows(book_id, filtered, note_indices)
        return

    # 分组策略：先试语义分组（第X部/卷/篇），失败则固定每 10 章一组
    groups = _smart_group_chapters(filtered, group_size=10)

    # 渲染分组（默认展开第一个未完成的组，其余折叠）
    first_unfolded = False
    for gname, items in groups:
        done_in_group = sum(1 for _, ch in items if ch.get("status") == "completed")
        total_in_group = len(items)
        all_done = done_in_group == total_in_group

        # 默认展开策略：第一个未全部完成的组展开
        default_open = not all_done and not first_unfolded
        if default_open:
            first_unfolded = True

        with st.expander(f"{gname} · {done_in_group}/{total_in_group} 已完成", expanded=default_open):
            _render_chapter_rows(book_id, items, note_indices)


def _render_chapter_rows(book_id: str, items: list, note_indices: set):
    """渲染单组章节行"""
    for i, ch in items:
        status = ch.get("status", "unread")
        status_class = status if status in ("reading", "completed") else "unread"
        name = ch.get("name", f"第{i+1}章")
        summary = ch.get("summary", "") or ch.get("text", "")[:80].replace("\n", " ").strip()
        bookmarked = ch.get("bookmarked", False)

        note_tag = '📝' if i in note_indices else ''
        bookmark_icon = '⭐' if bookmarked else '☆'

        st.markdown(f"""
        <div class="chapter-row {status_class}">
            <div class="ch-status-dot"></div>
            <div class="ch-info">
                <div class="ch-name">{name}</div>
                <div class="ch-summary">{summary[:70]}{'...' if len(summary) > 70 else ''}</div>
            </div>
            <div class="ch-meta-right">
                <span class="ch-note-tag">{note_tag}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        rc1, rc2, rc3 = st.columns([4, 1, 1])
        with rc1:
            if st.button("📖 阅读", key=f"toc_read_{i}", use_container_width=True):
                switch_to_reading(book_id, i)
        with rc2:
            if st.button(bookmark_icon, key=f"toc_bm_{i}", help="书签"):
                toggle_bookmark(book_id, i)
                st.session_state.chapters = load_chapters_with_state(book_id)
                st.rerun()
        with rc3:
            if status != "completed":
                if st.button("✓", key=f"toc_done_{i}", help="标记完成"):
                    update_chapter_status(book_id, i, "completed")
                    st.session_state.chapters = load_chapters_with_state(book_id)
                    log_reading(book_id, i, "end_chapter", detail=name)
                    st.rerun()
            else:
                if st.button("↺", key=f"toc_undo_{i}", help="取消完成"):
                    update_chapter_status(book_id, i, "reading")
                    st.session_state.chapters = load_chapters_with_state(book_id)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
# VIEW: 金句本
# ═══════════════════════════════════════════════════════════════
def render_quotes_view(book: dict):
    if render_app_header(show_back=True, back_label="目录"):
        st.session_state.show_quotes_view = False
        st.rerun()
        return

    book_id = book["id"]
    quotes = get_quotes(book_id)
    chapters = st.session_state.chapters

    st.markdown(f"""
    <h1>💎 《{book['title']}》金句本</h1>
    <p style="color:var(--text-tertiary);">共收藏 {len(quotes)} 条</p>
    """, unsafe_allow_html=True)

    if not quotes:
        st.info("还没有收藏金句。在阅读时点击 AI 回复下方的「📌 收藏此段」即可。")
        return

    for idx, q in enumerate(quotes):
        ch_name = (
            chapters[q["chapter_idx"]].get("name", f"第{q['chapter_idx']+1}章")
            if 0 <= q["chapter_idx"] < len(chapters)
            else ""
        )
        st.markdown(f"""
        <div class="quote-card">
            <div class="quote-text">「{q['quote']}」</div>
            <div class="quote-meta">—— {ch_name} · {q.get('saved_at', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        dc1, _ = st.columns([1, 4])
        with dc1:
            if st.button("🗑 删除", key=f"del_quote_{idx}"):
                delete_quote(book_id, idx)
                st.rerun()

    st.divider()
    if st.button("📥 导出全部金句", use_container_width=True):
        md = export_book_notes(book_id, book['title'], chapters)
        st.download_button(
            "下载 Markdown",
            md,
            f"{book['title']}_金句.md",
            "text/markdown",
        )


# ═══════════════════════════════════════════════════════════════
# VIEW: 阅读
# ═══════════════════════════════════════════════════════════════
def render_reading():
    book_id = st.session_state.current_book_id
    if not book_id:
        switch_to_shelf()
        return
    try:
        book = get_book(book_id)
    except ValueError:
        switch_to_shelf()
        return

    chapters = st.session_state.chapters
    if not chapters:
        st.warning("没有章节")
        return

    current = st.session_state.current_chapter
    if current >= len(chapters):
        current = 0
        st.session_state.current_chapter = 0
    chapter = chapters[current]

    # Header
    h1, h2, h3 = st.columns([1, 5, 1])
    with h1:
        if st.button("← 目录", key="read_back", use_container_width=True):
            # 返回目录时标记完成 + 结算时长
            update_chapter_status(book_id, current, "completed")
            end_current_chapter_session(book_id, current, chapter["name"])
            st.session_state.current_view = "toc"
            st.rerun()
    with h2:
        pct = book.get("progress_pct", 0)
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="font-weight:600;font-size:1rem;">{book['title']}</div>
            <div style="font-size:0.8rem;color:var(--text-tertiary);">
                {chapter['name']} · 第 {current + 1}/{len(chapters)} 章
            </div>
        </div>
        """, unsafe_allow_html=True)
    with h3:
        pct = book.get("progress_pct", 0)
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;">'
            f'{progress_ring_svg(pct, size="lg", label="全书进度")}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    # AI 头像：作者名首字（防御性，避免空字符串报错）
    author_avatar = _safe_avatar(book.get("author", ""))

    # 渲染历史消息
    messages = st.session_state.messages
    for msg_idx, msg in enumerate(messages):
        role = msg["role"]
        if role == "user" and msg["content"] == "请继续讲解":
            continue
        avatar = "👤" if role == "user" else author_avatar
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])
            # AI 回复下方加"收藏此段"按钮
            if role == "assistant" and msg["content"].strip():
                qcols, _ = st.columns([1, 4])
                with qcols:
                    if st.button("📌 收藏", key=f"quote_{msg_idx}", help="收藏此段到金句本"):
                        content = msg["content"]
                        # 截取前 200 字作为金句
                        quote_text = content[:200].strip()
                        if len(content) > 200:
                            quote_text += "..."
                        ok = save_quote(book_id, current, quote_text, source="ai")
                        if ok:
                            st.success("已收藏")
                        else:
                            st.info("已经收藏过啦")
                        time.sleep(0.8)
                        st.rerun()

    # 开始按钮
    if not messages:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("▶ 开始讲解本章", type="primary", use_container_width=True):
                with st.chat_message("assistant", avatar=author_avatar):
                    ph = st.empty()
                    streamed = ""

                    def on_tok(t):
                        nonlocal streamed
                        streamed += t
                        ph.markdown(streamed + "▌")

                    try:
                        result = start_chapter(
                            book["title"],
                            book["author"],
                            chapter["name"],
                            chapter["text"],
                            on_token=on_tok,
                            custom_prompt=get_custom_prompt(book_id),
                            mode_id=book.get("reading_mode", "default"),
                        )
                        ph.markdown(result)
                        st.session_state.messages.append({"role": "assistant", "content": result})
                        save_progress(book_id, current, st.session_state.messages)
                        st.rerun()
                    except Exception as e:
                        ph.error(f"AI 出错了：{e}")

    # 输入区
    if messages:
        user_input = st.chat_input("输入你的回复，或点下方按钮继续...")
        cc1, cc2, cc3, cc4 = st.columns([1, 1, 1, 1])

        continue_clicked = False
        with cc1:
            if st.button("▶ 继续", use_container_width=True, key="continue_btn"):
                continue_clicked = True
        with cc2:
            if st.button("📝 笔记", use_container_width=True, key="note_btn"):
                st.session_state.show_notes_drawer = not st.session_state.get("show_notes_drawer", False)
                st.rerun()
        with cc3:
            bookmarked = chapter.get("bookmarked", False)
            if st.button("⭐ 书签" if not bookmarked else "★ 已书签",
                         use_container_width=True, key="bm_btn"):
                toggle_bookmark(book_id, current)
                st.session_state.chapters = load_chapters_with_state(book_id)
                st.rerun()
        with cc4:
            if chapter.get("status") != "completed":
                if st.button("✓ 完成本章", use_container_width=True, key="done_btn"):
                    update_chapter_status(book_id, current, "completed")
                    st.session_state.chapters = load_chapters_with_state(book_id)
                    st.success("已标记完成 🎉")
                    time.sleep(0.6)
                    st.rerun()

        # 处理输入
        msg = None
        if user_input:
            msg = user_input
        elif continue_clicked:
            msg = "请继续讲解"

        if msg:
            st.session_state.messages.append({"role": "user", "content": msg})
            save_progress(book_id, current, st.session_state.messages)
            with st.chat_message("assistant", avatar=author_avatar):
                ph = st.empty()
                streamed = ""

                def on_tok2(t):
                    nonlocal streamed
                    streamed += t
                    ph.markdown(streamed + "▌")

                try:
                    api_msgs = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ]
                    result = continue_chat(api_msgs, on_token=on_tok2)
                    ph.markdown(result)
                    st.session_state.messages.append({"role": "assistant", "content": result})
                    save_progress(book_id, current, st.session_state.messages)
                    st.rerun()
                except Exception as e:
                    ph.error(f"AI 出错了：{e}")

        # 章节导航
        st.divider()
        nav1, nav2 = st.columns(2)
        with nav1:
            if current > 0 and st.button("← 上一章", use_container_width=True):
                update_chapter_status(book_id, current, "completed")
                end_current_chapter_session(book_id, current, chapter["name"])
                switch_to_reading(book_id, current - 1)
        with nav2:
            if current < len(chapters) - 1 and st.button("下一章 →", use_container_width=True):
                update_chapter_status(book_id, current, "completed")
                end_current_chapter_session(book_id, current, chapter["name"])
                switch_to_reading(book_id, current + 1)

    # ── 笔记抽屉 ──
    if st.session_state.get("show_notes_drawer"):
        st.divider()
        render_notes_drawer(book_id, current, chapter)


def render_notes_drawer(book_id: str, chapter_idx: int, chapter: dict):
    """底部笔记抽屉"""
    st.markdown("### 📝 本章笔记")

    existing = load_note(book_id, chapter_idx)

    edit_col, preview_col = st.columns([1, 1])
    with edit_col:
        st.caption("**编辑（支持 Markdown）**")
        new_note = st.text_area(
            "笔记内容",
            value=existing,
            height=280,
            placeholder="在这里记下你的想法...\n\n支持 **Markdown** 格式。",
            label_visibility="collapsed",
            key=f"note_edit_{book_id}_{chapter_idx}",
        )
    with preview_col:
        st.caption("**预览**")
        if new_note.strip():
            st.markdown(new_note)
        else:
            st.caption("（还没有内容）")

    nc1, nc2, nc3 = st.columns([1, 1, 2])
    with nc1:
        if st.button("💾 保存", use_container_width=True, key="save_note_btn"):
            save_note(book_id, chapter_idx, new_note)
            log_reading(book_id, chapter_idx, "take_note")
            st.success("已保存")
            time.sleep(0.5)
            st.rerun()
    with nc2:
        if existing.strip():
            md = f"# {chapter['name']}\n\n{existing}"
            st.download_button(
                "📥 导出本章",
                md,
                f"{chapter['name'][:20]}.md",
                "text/markdown",
                key="export_note_btn",
                use_container_width=True,
            )
    with nc3:
        if st.button("✕ 关闭笔记", use_container_width=True, key="close_note_btn"):
            st.session_state.show_notes_drawer = False
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# VIEW: 粘贴文本
# ═══════════════════════════════════════════════════════════════
def render_paste():
    if render_app_header(show_back=True, back_label="书架"):
        st.session_state.current_view = "shelf"
        st.session_state.paste_messages = []
        st.rerun()
        return

    st.markdown("""
    <h1>📋 粘贴文本阅读</h1>
    <p style="color:var(--text-tertiary);margin-top:-0.5rem;">视频转录稿、博客文章、长文 —— AI 带你读懂</p>
    """, unsafe_allow_html=True)

    if not st.session_state.paste_messages:
        article = st.text_area(
            "粘贴你的文本",
            height=200,
            placeholder="把视频转录稿、博客文章、或任何文本粘贴到这里...",
            label_visibility="collapsed",
        )
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if article.strip() and st.button("▶ 开始 AI 阅读", type="primary", use_container_width=True):
                with st.chat_message("assistant", avatar="📖"):
                    ph = st.empty()
                    streamed = ""

                    def on_tok(t):
                        nonlocal streamed
                        streamed += t
                        ph.markdown(streamed + "▌")

                    try:
                        result = start_article(article, on_token=on_tok)
                        ph.markdown(result)
                        st.session_state.paste_messages = [
                            {"role": "assistant", "content": result}
                        ]
                        st.rerun()
                    except Exception as e:
                        ph.error(f"AI 出错了：{e}")

    for msg in st.session_state.paste_messages:
        if msg["role"] == "user" and msg["content"] == "请继续讲解":
            continue
        role = msg["role"]
        avatar = "👤" if role == "user" else "📖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    if st.session_state.paste_messages:
        user_input = st.chat_input("回复...")
        if user_input:
            st.session_state.paste_messages.append({"role": "user", "content": user_input})
            with st.chat_message("assistant", avatar="📖"):
                ph = st.empty()
                streamed = ""

                def on_tok(t):
                    nonlocal streamed
                    streamed += t
                    ph.markdown(streamed + "▌")

                try:
                    result = continue_chat(st.session_state.paste_messages, on_token=on_tok)
                    ph.markdown(result)
                    st.session_state.paste_messages.append(
                        {"role": "assistant", "content": result}
                    )
                except Exception as e:
                    ph.error(f"AI 出错了：{e}")


# ═══════════════════════════════════════════════════════════════
# VIEW: 阅读统计
# ═══════════════════════════════════════════════════════════════
def render_stats():
    """阅读统计页：总览卡片 + 周时长图 + 各书进度"""
    if render_app_header(show_back=True, back_label="书架"):
        switch_to_shelf()
        return

    st.markdown("""
    <h1>📊 阅读统计</h1>
    <p style="color:var(--text-tertiary);margin-top:-0.5rem;">你的阅读足迹一目了然</p>
    """, unsafe_allow_html=True)

    # ── 总览卡片 ──
    stats = get_reading_stats()
    dur = get_total_duration()
    bs = get_bookshelf_stats()
    total_notes = sum(len(get_all_notes(b["id"])) for b in load_shelf())
    total_quotes = sum(len(get_quotes(b["id"])) for b in load_shelf())

    cards = "".join(f"""
    <div class="stat-card">
        <div class="sc-icon">{icon}</div>
        <div class="sc-value">{value}</div>
        <div class="sc-label">{label}</div>
    </div>
    """ for icon, value, label in [
        ("📚", bs["total_books"], "书架"),
        ("📖", stats["chapters_read"], "已读章节"),
        ("⏱️", dur["total_fmt"], "累计时长"),
        ("📝", total_notes, "笔记"),
        ("💎", total_quotes, "金句"),
        ("📅", stats["weekly_chapters"], "本周章节"),
    ])
    st.markdown(f'<div class="stats-grid">{cards}</div>', unsafe_allow_html=True)

    st.divider()

    # ── 本周阅读时长条形图 ──
    st.markdown("##### 📅 本周阅读时长")
    weekly = get_weekly_chart_data()
    max_sec = max((d["sec"] for d in weekly), default=1) or 1

    def _fmt_m(sec):
        m = int(sec / 60)
        if m >= 60:
            return f"{m//60}h{m%60}m"
        return f"{m}m" if m > 0 else "—"

    bars = ""
    for d in weekly:
        h_pct = (d["sec"] / max_sec * 100) if max_sec > 0 else 0
        bars += f"""
        <div class="wb-col">
            <div class="wb-bar" style="height:{max(h_pct, 2)}%;">
                <span class="wb-bar-tip">{_fmt_m(d['sec'])}</span>
            </div>
            <span class="wb-label">{d['weekday']}</span>
        </div>
        """
    st.markdown(f'<div class="weekly-bars">{bars}</div>', unsafe_allow_html=True)

    st.divider()

    # ── 各书进度 ──
    st.markdown("##### 📚 书籍进度")
    books = load_shelf()
    if not books:
        st.info("书架还空着，添加一本书开始阅读吧。")
        return

    for b in books:
        pct = b.get("progress_pct", 0)
        ch_count = b.get("chapter_count", 0)
        cs = get_book_chapter_stats(b["id"])
        b_dur = get_reading_duration(b["id"])
        last = b.get("last_read_at", "")
        last_str = f"上次：{last[5:]}" if last else "未开始"

        st.markdown(f"""
        <div class="book-stat-row">
            <div class="bsr-info">
                <div class="bsr-title">{b['title']}</div>
                <div class="bsr-meta">{ch_count} 章 · 完成 {cs['completed']}/{cs['total']} · 时长 {b_dur['total_fmt']} · {last_str}</div>
            </div>
            <div class="bsr-track"><div class="bsr-fill" style="width:{pct}%;"></div></div>
            <span class="bsr-pct">{pct}%</span>
        </div>
        """, unsafe_allow_html=True)

        # 点击进入
        sc1, _ = st.columns([1, 5])
        with sc1:
            if st.button("打开", key=f"stat_open_{b['id']}", use_container_width=True):
                switch_to_toc(b["id"])


# ═══════════════════════════════════════════════════════════════
# 路由分发
# ═══════════════════════════════════════════════════════════════
view = st.session_state.current_view
if view == "shelf":
    render_shelf()
elif view == "toc":
    render_toc()
elif view == "reading":
    render_reading()
elif view == "paste":
    render_paste()
elif view == "stats":
    render_stats()
