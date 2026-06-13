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
from prompt import build_overview_prompt
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

load_dotenv()

SHELF_DIR = Path(__file__).parent / "shelf"
THEME_PATH = SHELF_DIR / "theme.json"

st.set_page_config(
    page_title="阅伴",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════════
# 设计系统 —— CSS（浅/深双主题，现代极简）
# ═══════════════════════════════════════════════════════════════
def get_css() -> str:
    return """
<style>
/* ── 字体 ── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700;800&family=Noto+Serif+SC:wght@500;700&display=swap');

/* ── 主题变量：浅色（默认）── */
:root {
    --bg: #FFFFFF;
    --bg-subtle: #FAFAFA;
    --card: #FFFFFF;
    --text: #111827;
    --text-secondary: #6B7280;
    --text-tertiary: #9CA3AF;
    --border: #ECECEC;
    --border-strong: #E5E5E5;
    --accent: #C8893E;
    --accent-soft: #FDF6EC;
    --green: #16A34A;
    --green-soft: #ECFDF5;
    --hover: #F7F7F7;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.03);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.06);
    --spine-1: #C8893E;
    --spine-2: #5B7553;
    --spine-3: #8B5A3C;
    --spine-4: #6B7B8C;
}

/* ── 主题变量：深色 ── */
:root[data-theme="dark"] {
    --bg: #0F0F10;
    --bg-subtle: #161618;
    --card: #1A1A1D;
    --text: #E8E8E8;
    --text-secondary: #A0A0A0;
    --text-tertiary: #6B6B6B;
    --border: #2A2A2D;
    --border-strong: #333337;
    --accent: #D4A056;
    --accent-soft: #2A2018;
    --green: #4ADE80;
    --green-soft: #16261C;
    --hover: #222225;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.4);
    --spine-1: #D4A056;
    --spine-2: #7A9270;
    --spine-3: #B07A52;
    --spine-4: #8B9BAC;
}

/* ── 全局 ── */
html, body, .stApp {
    font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    transition: background 0.25s ease, color 0.25s ease;
}
.main .block-container {
    padding: 1.5rem 2rem 4rem;
    max-width: 1200px;
}
#MainMenu, footer, .stDeployButton, header[data-testid="stHeader"] { display: none !important; }

h1, h2, h3, h4 {
    font-family: 'Noto Sans SC', sans-serif !important;
    letter-spacing: -0.01em;
    color: var(--text) !important;
}
h1 { font-size: 1.65rem !important; font-weight: 700 !important; }
h2 { font-size: 1.2rem !important; font-weight: 600 !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; }
p, span, div, li { color: var(--text); }

/* ── 隐藏 Streamlit 警告横幅的边框，让它更克制 ── */
.stAlert { border-radius: 10px !important; }

/* ── 顶部 Header ── */
.app-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.5rem 0 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
}
.app-header .brand {
    display: flex; align-items: center; gap: 0.7rem;
}
.app-header .logo {
    width: 36px; height: 36px;
    background: var(--text);
    color: var(--bg);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 1.1rem;
}
.app-header .brand-name {
    font-weight: 700; font-size: 1.15rem; color: var(--text);
}
.app-header .brand-sub {
    font-size: 0.78rem; color: var(--text-tertiary); margin-top: 1px;
}
.app-header .header-actions {
    display: flex; align-items: center; gap: 0.5rem;
}
.theme-btn {
    width: 36px; height: 36px; border-radius: 10px;
    background: var(--bg-subtle); border: 1px solid var(--border);
    cursor: pointer; font-size: 1.1rem; line-height: 1;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
}
.theme-btn:hover { background: var(--hover); transform: translateY(-1px); }

/* ── 统计条 ── */
.stats-bar {
    display: flex; gap: 0; margin-bottom: 1.5rem;
    background: var(--bg-subtle); border-radius: 12px; padding: 0.9rem 1.2rem;
}
.stat-item {
    flex: 1; text-align: center;
    border-right: 1px solid var(--border);
}
.stat-item:last-child { border-right: none; }
.stat-value {
    font-size: 1.4rem; font-weight: 700; color: var(--text);
    line-height: 1.1;
}
.stat-label {
    font-size: 0.72rem; color: var(--text-tertiary); margin-top: 4px;
    letter-spacing: 0.02em;
}

/* ── 书卡 ── */
.book-card {
    background: var(--card); border-radius: 14px; padding: 1.2rem 1.2rem 1rem 1.4rem;
    box-shadow: var(--shadow-sm); transition: all 0.2s;
    position: relative; overflow: hidden;
    display: flex; flex-direction: column; min-height: 180px;
    margin-bottom: 0.8rem;
}
.book-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.book-card .spine {
    position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
}
.book-card .book-title {
    font-weight: 600; font-size: 1rem; color: var(--text); line-height: 1.35;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden; flex-grow: 1;
}
.book-card .book-author {
    font-size: 0.8rem; color: var(--text-tertiary); margin: 0.3rem 0 0.8rem;
}
.book-card .progress-row {
    display: flex; align-items: center; gap: 0.5rem; margin-top: auto;
}
.book-card .progress-track {
    flex: 1; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden;
}
.book-card .progress-fill {
    height: 100%; border-radius: 2px; transition: width 0.5s; background: var(--accent);
}
.book-card .progress-pct {
    font-size: 0.75rem; font-weight: 600; color: var(--text-secondary);
    min-width: 32px; text-align: right;
}
.book-card .card-meta {
    display: flex; justify-content: space-between;
    font-size: 0.7rem; color: var(--text-tertiary); margin-top: 0.5rem;
}

/* ── 空状态 ── */
.empty-state {
    text-align: center; padding: 4rem 2rem;
}
.empty-state .empty-icon {
    font-size: 3rem; margin-bottom: 1rem; opacity: 0.6;
}
.empty-state h2 {
    font-size: 1.4rem !important; font-weight: 700; margin-bottom: 0.5rem;
}
.empty-state p {
    color: var(--text-tertiary); font-size: 0.95rem;
}

/* ── 章节统计胶囊 ── */
.chapter-stats {
    display: flex; gap: 0.5rem; flex-wrap: wrap;
    margin: 0.8rem 0;
}
.stat-pill {
    background: var(--bg-subtle); border-radius: 20px;
    padding: 0.3rem 0.8rem; font-size: 0.78rem;
    color: var(--text-secondary);
    display: inline-flex; align-items: center; gap: 0.3rem;
}
.stat-pill .pill-dot {
    width: 6px; height: 6px; border-radius: 50%;
}
.stat-pill.reading .pill-dot { background: var(--accent); }
.stat-pill.done .pill-dot { background: var(--green); }
.stat-pill.bookmark .pill-dot { background: #EAB308; }

/* ── 章节行 ── */
.chapter-row {
    background: var(--card); border-radius: 10px; padding: 0.8rem 1rem;
    margin-bottom: 0.4rem; transition: all 0.15s;
    display: flex; align-items: center; gap: 0.7rem;
}
.chapter-row:hover { background: var(--hover); }
.chapter-row.reading { background: var(--accent-soft); }
.chapter-row .ch-status-dot {
    width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
    border: 2px solid var(--border-strong);
}
.chapter-row.unread .ch-status-dot { background: transparent; }
.chapter-row.reading .ch-status-dot { background: var(--accent); border-color: var(--accent); }
.chapter-row.completed .ch-status-dot { background: var(--green); border-color: var(--green); }
.chapter-row .ch-info { flex: 1; min-width: 0; }
.chapter-row .ch-name {
    font-weight: 500; font-size: 0.92rem; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.chapter-row .ch-summary {
    font-size: 0.76rem; color: var(--text-tertiary); margin-top: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.chapter-row .ch-meta-right {
    display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;
}
.chapter-row .ch-note-tag {
    font-size: 0.68rem; color: var(--text-tertiary);
    background: var(--bg-subtle); padding: 0.15rem 0.5rem; border-radius: 4px;
}

/* ── 导读框 ── */
.overview-box {
    background: var(--bg-subtle); border-radius: 12px; padding: 1.2rem 1.4rem;
    margin: 1rem 0; line-height: 1.85; font-size: 0.93rem; color: var(--text-secondary);
    border-left: 3px solid var(--accent);
}

/* ── 周阅读图表 ── */
.weekly-chart {
    display: flex; align-items: flex-end; gap: 6px;
    height: 80px; padding: 0.5rem 0;
}
.weekly-bar-col {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.weekly-bar {
    width: 100%; max-width: 32px;
    background: var(--accent); border-radius: 4px 4px 0 0;
    min-height: 2px; transition: height 0.4s;
    opacity: 0.85;
}
.weekly-bar-col:hover .weekly-bar { opacity: 1; }
.weekly-bar-label {
    font-size: 0.65rem; color: var(--text-tertiary);
}

/* ── 按钮统一样式 ── */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'Noto Sans SC', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.87rem !important;
    transition: all 0.15s !important;
    border: 1px solid var(--border-strong) !important;
    background: var(--card) !important;
    color: var(--text) !important;
}
.stButton > button:hover {
    background: var(--hover) !important;
    border-color: var(--text-tertiary) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: var(--text) !important;
    color: var(--bg) !important;
    border-color: var(--text) !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--text-secondary) !important;
    border-color: var(--text-secondary) !important;
}

/* ── 下载按钮 ── */
.stDownloadButton > button {
    border-radius: 10px !important;
    font-family: 'Noto Sans SC', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

/* ── 聊天 ── */
.stChatMessage {
    border-radius: 14px !important;
    padding: 1rem 1.2rem !important;
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
}
.stChatMessage > div:first-child {
    background: var(--text) !important;
}
.stChatInput > div {
    border: 1px solid var(--border-strong) !important;
    border-radius: 12px !important;
    background: var(--card) !important;
}
.stChatInput > div:focus-within {
    border-color: var(--accent) !important;
}

/* ── 输入框 ── */
.stTextInput > div > input,
.stTextArea > div > textarea {
    background: var(--card) !important;
    color: var(--text) !important;
    border-color: var(--border-strong) !important;
    border-radius: 10px !important;
    font-family: 'Noto Sans SC', sans-serif !important;
}
.stTextInput > div > input:focus,
.stTextArea > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: none !important;
}

/* ── expander ── */
.streamlit-expanderHeader {
    background: var(--card) !important;
    font-size: 0.9rem !important;
}
details {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    background: var(--card) !important;
}

/* ── sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-subtle) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid var(--border-strong) !important;
}

/* ── 金句卡片 ── */
.quote-card {
    background: var(--card); border-radius: 10px; padding: 1rem 1.1rem;
    margin-bottom: 0.6rem; border-left: 3px solid var(--accent);
    position: relative;
}
.quote-card .quote-text {
    font-size: 0.92rem; line-height: 1.7; color: var(--text);
    font-family: 'Noto Serif SC', serif;
}
.quote-card .quote-meta {
    font-size: 0.72rem; color: var(--text-tertiary); margin-top: 0.5rem;
}

/* ── divider ── */
hr {
    border-color: var(--border) !important;
    margin: 1.5rem 0 !important;
}

/* ── 进度环数字（reading 页右上） ── */
.progress-display {
    text-align: right;
}
.progress-display .pct {
    font-size: 1.5rem; font-weight: 700; color: var(--text); line-height: 1;
}
.progress-display .label {
    font-size: 0.68rem; color: var(--text-tertiary); letter-spacing: 0.05em;
}

/* ── 底部工具栏 ── */
.toolbar {
    display: flex; gap: 0.5rem; padding: 0.8rem 0;
    background: var(--bg-subtle); border-radius: 12px; padding: 0.6rem;
    margin-top: 1rem;
}
.toolbar .tool-btn {
    flex: 1; padding: 0.5rem; text-align: center;
    background: var(--card); border-radius: 8px; font-size: 0.85rem;
    cursor: pointer; transition: all 0.15s;
}
.toolbar .tool-btn:hover { background: var(--hover); }
</style>
"""


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
# API key
# ═══════════════════════════════════════════════════════════════
if not os.getenv("DEEPSEEK_API_KEY"):
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
                            <div class="brand-sub">好书共读 · 逐章伴读</div>
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
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
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
            sort_by = st.selectbox(
                "排序",
                options=[("added", "最近添加"), ("progress", "按进度"), ("title", "按书名")],
                format_func=lambda x: x[1],
                index=["added", "progress", "title"].index(
                    st.session_state.get("sort_by_val", "added")
                ),
                key="sort_select",
            )
            st.session_state.sort_by_val = sort_by[0]
            st.session_state.sort_by = sort_by

        sort_key = st.session_state.get("sort_by_val", "added")
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
        st.markdown(f"""
        <div class="progress-display">
            <div class="pct">{pct}%</div>
            <div class="label">已读</div>
        </div>
        """, unsafe_allow_html=True)

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

    # 继续阅读
    last_ch = book.get("current_chapter", 0)
    if book.get("progress_pct", 0) > 0 and last_ch < len(chapters):
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

    # 导读
    with st.spinner(""):  # 占位，避免 spinner 闪烁
        pass
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
        summary = ch.get("summary", "") or ch["text"][:80].replace("\n", " ").strip()
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
        st.markdown(f"""
        <div class="progress-display">
            <div class="pct">{pct}%</div>
            <div class="label">全书进度</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    # AI 头像：首字母
    author = book.get("author", "")
    author_avatar = author[:1] if author else "📖"

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
