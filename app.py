"""AI 书僮 —— 上传一本书，AI 扮演作者逐章带你阅读"""

import os, time, tempfile
import streamlit as st
from dotenv import load_dotenv
from shelf import (
    load_shelf, add_book, get_book, get_chapters,
    delete_book, save_progress, load_history,
    load_chapters_with_state, save_chapters, update_chapter_status,
    get_custom_prompt, save_custom_prompt,
)
from reader import start_chapter, continue_chat, start_article
from prompt import SYSTEM_PROMPT_TEMPLATE
from notes import save_note, load_note, append_to_note, export_book_notes
from reading_log import log_reading, get_reading_stats, get_book_stats

load_dotenv()

st.set_page_config(
    page_title="AI Book Reader", page_icon="📖",
    layout="wide", initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════
# CSS
# ═══════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {
        --bg: #F5F5F5; --card: #FFFFFF; --text: #1A1A1A;
        --text-secondary: #6B7280; --text-tertiary: #9CA3AF;
        --accent: #1A1A1A; --green: #10B981; --amber: #F59E0B;
        --red: #EF4444; --blue: #3B82F6; --border: #F0F0F0;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
        --shadow-md: 0 4px 16px rgba(0,0,0,0.06);
    }
    .stApp { background: var(--bg); font-family: 'Inter', sans-serif; }
    .main .block-container { padding: 2rem 2.5rem; max-width: 1280px; }
    #MainMenu, footer, .stDeployButton, header[data-testid="stHeader"] { display: none !important; }
    h1, h2, h3 { font-family: 'Inter', sans-serif !important; letter-spacing: -0.02em; }
    h1 { font-size: 1.75rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.25rem !important; font-weight: 600 !important; }

    /* ──Header── */
    .site-header { display:flex; align-items:center; justify-content:space-between; padding:0 0 1.5rem; }
    .brand { display:flex; align-items:center; gap:0.6rem; }
    .logo { width:36px;height:36px;background:var(--accent);border-radius:10px;
            display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700; }
    .brand .name { font-weight:700;font-size:1.15rem;color:var(--text); }
    .greeting { color:var(--text-secondary);font-size:0.93rem; }

    /* ──Stat cards── */
    .stat-card { background:var(--card);border-radius:14px;padding:1.2rem 1.4rem;box-shadow:var(--shadow-sm); }
    .stat-number { font-size:1.8rem;font-weight:700;color:var(--text);line-height:1.2; }
    .stat-label { font-size:0.78rem;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em;margin-top:0.15rem; }

    /* ──Bookshelf── */
    .book-card { background:var(--card);border-radius:14px;padding:1.3rem 1.2rem 1rem;
        box-shadow:var(--shadow-sm);transition:all 0.2s;position:relative;overflow:hidden;
        display:flex;flex-direction:column;min-height:210px; }
    .book-card:hover { box-shadow:var(--shadow-md);transform:translateY(-2px); }
    .book-card .cover-strip { position:absolute;top:0;left:0;right:0;height:4px; }
    .book-card .book-icon { font-size:1.6rem;margin:0.7rem 0 0.5rem; }
    .book-card .book-name { font-weight:600;font-size:0.95rem;color:var(--text);line-height:1.35;
        display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;flex-grow:1; }
    .book-card .book-author { font-size:0.78rem;color:var(--text-tertiary);margin:0.15rem 0 0.6rem; }
    .book-card .progress-row { display:flex;align-items:center;gap:0.5rem;margin-top:auto; }
    .book-card .progress-track { flex:1;height:4px;background:#F0F0F0;border-radius:2px;overflow:hidden; }
    .book-card .progress-fill { height:100%;border-radius:2px;transition:width 0.5s; }
    .book-card .progress-pct { font-size:0.75rem;font-weight:600;color:var(--text-secondary);min-width:32px;text-align:right; }
    .book-card .card-meta { display:flex;justify-content:space-between;font-size:0.72rem;color:var(--text-tertiary);margin-top:0.5rem; }

    /* ──TOC── */
    .toc-chapter { background:var(--card);border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.5rem;
        border-left:3px solid #E5E5E5;transition:all 0.15s;cursor:pointer; }
    .toc-chapter:hover { border-left-color:var(--accent);box-shadow:var(--shadow-sm); }
    .toc-chapter.active { border-left-color:var(--accent);background:#FAFAFA; }
    .toc-chapter.completed { border-left-color:var(--green); }
    .toc-chapter .toc-name { font-weight:600;font-size:0.92rem;color:var(--text); }
    .toc-chapter .toc-summary { font-size:0.8rem;color:var(--text-tertiary);margin-top:0.2rem; }
    .toc-chapter .toc-subs { font-size:0.75rem;color:var(--text-tertiary);margin-top:0.3rem;padding-left:1rem; }

    /* ──Notes panel── */
    .notes-panel { background:var(--card);border-radius:14px;padding:1rem;box-shadow:var(--shadow-sm); }
    .notes-panel h4 { font-size:0.9rem;font-weight:600;color:var(--text);margin-bottom:0.5rem; }

    /* ──Buttons── */
    .stButton > button { border-radius:10px!important;font-family:'Inter',sans-serif!important;
        font-weight:600!important;font-size:0.88rem!important;transition:all 0.15s!important;border:none!important; }
    .stButton > button[kind="primary"] { background:var(--accent)!important;color:#fff!important; }
    .stButton > button[kind="primary"]:hover { background:#333!important;transform:translateY(-1px); }
    .stButton > button[kind="secondary"] { background:var(--card)!important;color:var(--text)!important;border:1px solid #E5E5E5!important; }

    /* ──Chat── */
    .stChatMessage { border-radius:14px!important;padding:1rem 1.2rem!important; }
    .stChatInput > div { border:1px solid #E5E5E5!important;border-radius:12px!important;background:var(--card)!important; }

    /* ──Sidebar── */
    [data-testid="stSidebar"] { background:var(--card);border-right:1px solid var(--border); }

    /* ──Empty── */
    .empty-state { text-align:center;padding:5rem 2rem; }
    .empty-state .empty-icon { font-size:3.5rem;margin-bottom:1rem; }
    .empty-state p { color:var(--text-tertiary);font-size:0.95rem; }

    /* ──Export btn── */
    .stDownloadButton > button { border-radius:10px!important;font-family:'Inter',sans-serif!important;
        font-weight:600!important;font-size:0.85rem!important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════
# Session state
# ═══════════════════════════════════════
def init_session():
    for k, v in {
        "current_view": "shelf",
        "current_book_id": None,
        "messages": [],
        "chapters": [],
        "current_chapter": 0,
        "paste_messages": [],
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ═══════════════════════════════════════
# API key
# ═══════════════════════════════════════
if not os.getenv("DEEPSEEK_API_KEY"):
    with st.sidebar:
        st.warning("⚠️ API Key not set")
        key_in = st.text_input("DeepSeek API Key", type="password")
        if key_in:
            os.environ["DEEPSEEK_API_KEY"] = key_in
            st.rerun()

# ═══════════════════════════════════════
# Router helpers
# ═══════════════════════════════════════
def switch_to_toc(book_id):
    st.session_state.current_view = "toc"
    st.session_state.current_book_id = book_id
    st.session_state.chapters = load_chapters_with_state(book_id)
    st.rerun()

def switch_to_reading(book_id, chapter_idx):
    st.session_state.current_view = "reading"
    st.session_state.current_book_id = book_id
    st.session_state.chapters = load_chapters_with_state(book_id)
    st.session_state.current_chapter = chapter_idx
    st.session_state.messages = load_history(book_id, chapter_idx)
    update_chapter_status(book_id, chapter_idx, "reading")
    log_reading(book_id, chapter_idx, "start_chapter",
                detail=st.session_state.chapters[chapter_idx]["name"])
    st.rerun()

def switch_to_shelf():
    st.session_state.current_view = "shelf"
    st.session_state.current_book_id = None
    st.session_state.messages = []
    st.rerun()

# ═══════════════════════════════════════
# VIEW: Shelf
# ═══════════════════════════════════════
def render_shelf():
    st.markdown("""
    <div class="site-header">
        <div class="brand">
            <div class="logo">B</div>
            <span class="name">AI Book Reader</span>
        </div>
        <span class="greeting">你的私人AI书僮 · 好书一起读</span>
    </div>
    """, unsafe_allow_html=True)

    books = load_shelf()
    stats = get_reading_stats()

    if books:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(f"""<div class="stat-card">
            <div class="stat-number">{len(books)}</div>
            <div class="stat-label">Books</div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="stat-card" style="--num-color:var(--green)">
            <div class="stat-number" style="color:var(--green)">{stats['chapters_read']}</div>
            <div class="stat-label">Chapters Read</div>
        </div>""", unsafe_allow_html=True)
        c3.markdown(f"""<div class="stat-card" style="--num-color:var(--amber)">
            <div class="stat-number" style="color:var(--amber)">{stats['weekly_chapters']}</div>
            <div class="stat-label">This Week</div>
        </div>""", unsafe_allow_html=True)
        c4.markdown(f"""<div class="stat-card" style="--num-color:var(--blue)">
            <div class="stat-number" style="color:var(--blue)">{stats['notes_taken']}</div>
            <div class="stat-label">Notes</div>
        </div>""", unsafe_allow_html=True)
        c5.markdown(f"""<div class="stat-card">
            <div class="stat-number">{stats['total_sessions']}</div>
            <div class="stat-label">Sessions</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<h2 style='margin:1.8rem 0 1rem;'>Your Bookshelf</h2>" if books else "",
                unsafe_allow_html=True)

    if not books:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📖</div>
            <h2>Your bookshelf is empty</h2>
            <p>Upload your first book and let AI guide your reading</p>
        </div>
        """, unsafe_allow_html=True)

    # Upload
    with st.expander("+ Add a new book", expanded=not books):
        c_up, _ = st.columns([1, 1])
        with c_up:
            uploaded = st.file_uploader(
                "Upload PDF or TXT", type=["pdf", "txt"],
                label_visibility="collapsed", key="shelf_upload")
            custom_title = st.text_input(
                "Book title", placeholder="Leave blank to auto-detect",
                label_visibility="collapsed")
            if uploaded and st.button("Add to Bookshelf", type="primary", use_container_width=True):
                suffix = os.path.splitext(uploaded.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name
                try:
                    book = add_book(tmp_path, custom_title)
                    os.unlink(tmp_path)
                    # 首次加载章节状态
                    chs = load_chapters_with_state(book["id"])
                    save_chapters(book["id"], chs)
                    st.success(f"\"{book['title']}\" added!")
                    time.sleep(0.5)
                    switch_to_toc(book["id"])
                except Exception as e:
                    st.error(f"Failed: {e}")

    # Book grid
    if books:
        cols = st.columns(4)
        for i, book in enumerate(books):
            with cols[i % 4]:
                pct = book.get("progress_pct", 0)
                status_color = "var(--green)" if pct >= 100 else "var(--amber)" if pct > 0 else "#E5E5E5"
                icon = "✅" if pct >= 100 else "📖" if pct > 0 else "📕"
                last = book.get("last_read_at", "")
                last_str = f"Last: {last}" if last else ""

                st.markdown(f"""
                <div class="book-card">
                    <div class="cover-strip" style="background:{book['cover_color']};"></div>
                    <div class="book-icon">{icon}</div>
                    <div class="book-name">{book['title']}</div>
                    <div class="book-author">{book['author'] or 'Unknown author'}</div>
                    <div class="progress-row">
                        <div class="progress-track">
                            <div class="progress-fill" style="width:{pct}%;background:{status_color};"></div>
                        </div>
                        <span class="progress-pct">{pct}%</span>
                    </div>
                    <div class="card-meta">
                        <span>{book.get('chapter_count', 0)} ch</span>
                        <span>{last_str}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                b_col, d_col = st.columns([3, 1])
                with b_col:
                    if st.button(
                        "Continue" if pct > 0 else "Start Reading",
                        key=f"read_{book['id']}", use_container_width=True,
                        type="primary" if pct == 0 else "secondary",
                    ):
                        switch_to_toc(book["id"])
                with d_col:
                    if st.button("🗑", key=f"del_{book['id']}", help="Delete"):
                        delete_book(book["id"])
                        st.rerun()


# ═══════════════════════════════════════
# VIEW: Table of Contents
# ═══════════════════════════════════════
def render_toc():
    book_id = st.session_state.current_book_id
    if not book_id:
        switch_to_shelf(); return
    try:
        book = get_book(book_id)
    except ValueError:
        switch_to_shelf(); return

    chapters = st.session_state.chapters

    # ── Header ──
    c1, c2, c3 = st.columns([1, 6, 1])
    with c1:
        if st.button("← Bookshelf", key="toc_back", use_container_width=True):
            switch_to_shelf()
    with c2:
        st.markdown(f"""
        <div style="text-align:center;">
            <h1 style="margin:0;">{book['title']}</h1>
            <p style="color:var(--text-tertiary);margin:0.2rem 0 0;">
                {book['author'] or 'Unknown'} · {book.get('chapter_count', len(chapters))} chapters · {book['total_chars']:,} chars
            </p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        book_stats = get_book_stats(book_id)
        st.markdown(f"""
        <div style="text-align:right;padding-top:0.5rem;">
            <div style="font-weight:700;font-size:1.3rem;">{book.get('progress_pct', 0)}%</div>
            <div style="font-size:0.75rem;color:var(--text-tertiary);">READ</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Quick actions ──
    st.markdown(f"""
    <div style="display:flex;gap:1rem;margin:1rem 0;">
        <div class="stat-card" style="flex:1;text-align:center;">
            <div style="font-size:0.8rem;color:var(--text-tertiary);">SESSIONS</div>
            <div style="font-weight:700;">{book_stats['sessions']}</div>
        </div>
        <div class="stat-card" style="flex:1;text-align:center;">
            <div style="font-size:0.8rem;color:var(--text-tertiary);">NOTES</div>
            <div style="font-weight:700;">{book_stats['notes']}</div>
        </div>
        <div class="stat-card" style="flex:1;text-align:center;">
            <div style="font-size:0.8rem;color:var(--text-tertiary);">CHAPTERS VISITED</div>
            <div style="font-weight:700;">{book_stats['chapters_visited']}/{len(chapters)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Start from last position ──
    last_ch = book.get("current_chapter", 0)
    if book.get("progress_pct", 0) > 0 and last_ch < len(chapters):
        if st.button(f"📍 Continue from Chapter {last_ch + 1}: {chapters[last_ch]['name']}",
                     type="primary", use_container_width=True):
            switch_to_reading(book_id, last_ch)

    # ── Export all notes ──
    all_notes = notes_export_helper(book_id, book['title'])
    if all_notes:
        st.download_button(
            "📥 Export All Notes (Markdown)", all_notes,
            f"{book['title']}_notes.md", "text/markdown",
            use_container_width=True,
        )

    # ── 自定义提示词 ──
    with st.expander("⚙️ 自定义伴读风格（点击展开）", expanded=False):
        st.caption("修改 AI 的伴读风格，支持变量：{book_title} {author} {chapter_name} {chapter_text}")
        saved_prompt = get_custom_prompt(book_id)

        custom_prompt = st.text_area(
            "提示词（留空=使用默认风格）",
            value=saved_prompt,
            placeholder="自定义范例：\n你是一个毒舌书评人，用犀利幽默的语言逐章点评《{book_title}》，指出逻辑漏洞和精彩之处。也要给出建设性意见。",
            height=180,
            key=f"prompt_toc_{book_id}",
        )
        pc1, pc2, pc3 = st.columns([1, 1, 2])
        with pc1:
            if st.button("💾 保存", use_container_width=True, key=f"save_prompt_toc_{book_id}"):
                save_custom_prompt(book_id, custom_prompt)
                st.success("已保存！")
                time.sleep(0.5)
                st.rerun()
        with pc2:
            if st.button("🔄 默认", use_container_width=True, key=f"reset_prompt_toc_{book_id}"):
                save_custom_prompt(book_id, "")
                st.success("已恢复默认")
                time.sleep(0.5)
                st.rerun()

    # ── Chapter list ──
    st.markdown("<h3 style='margin-top:1.5rem;'>📑 Table of Contents</h3>", unsafe_allow_html=True)

    for i, ch in enumerate(chapters):
        status = ch.get("status", "unread")
        icon = "●" if status == "completed" else "◐" if status == "reading" else "○"
        border_class = "active" if status == "reading" else "completed" if status == "completed" else ""
        summary = ch.get("summary", ch["text"][:80].replace("\n", " ").strip())
        subs = ch.get("subsections", [])

        subs_html = ""
        if subs:
            subs_html = "<div class='toc-subs'>"
            for s in subs:
                subs_html += f"├ {s['name']}<br>"
            subs_html += "</div>"

        st.markdown(f"""
        <div class="toc-chapter {border_class}">
            <div class="toc-name">{icon} {ch['name']}</div>
            <div class="toc-summary">{summary[:80]}{'...' if len(summary) > 80 else ''}</div>
            {subs_html}
        </div>
        """, unsafe_allow_html=True)

        # Per-chapter actions
        ac1, ac2, ac3, ac4 = st.columns([2, 1, 1, 1])
        with ac1:
            if st.button(f"📖 Read this chapter", key=f"toc_read_{i}", use_container_width=True):
                switch_to_reading(book_id, i)
        with ac2:
            if status != "completed":
                if st.button("✓ Done", key=f"toc_done_{i}", help="Mark as completed"):
                    update_chapter_status(book_id, i, "completed")
                    st.session_state.chapters = load_chapters_with_state(book_id)
                    log_reading(book_id, i, "end_chapter", detail=ch["name"])
                    st.rerun()
        with ac3:
            note = load_note(book_id, i)
            if note.strip():
                with st.expander(f"📝 Note ({len(note)} chars)"):
                    st.text(note[:500])
        with ac4:
            if st.button("📥 Export", key=f"toc_export_{i}"):
                single_note = load_note(book_id, i)
                md = f"# {ch['name']}\n\n{single_note}" if single_note else f"# {ch['name']}\n\n(No notes)"
                st.download_button(
                    f"Download {ch['name'][:15]}.md", md,
                    f"{ch['name'][:20]}.md", "text/markdown",
                    key=f"dl_{i}",
                )

    # ── New: paste text entry ──
    st.divider()
    if st.button("📋 Paste Text Mode", use_container_width=True):
        st.session_state.current_view = "paste"
        st.rerun()


def notes_export_helper(book_id, book_title):
    """判断是否有笔记可导出"""
    from notes import get_all_notes
    n = get_all_notes(book_id)
    if not n:
        return ""
    chs = st.session_state.chapters
    return export_book_notes(book_id, book_title, chs)


# ═══════════════════════════════════════
# VIEW: Reading (with notes panel)
# ═══════════════════════════════════════
def render_reading():
    book_id = st.session_state.current_book_id
    if not book_id:
        switch_to_shelf(); return
    try:
        book = get_book(book_id)
    except ValueError:
        switch_to_shelf(); return

    chapters = st.session_state.chapters
    if not chapters:
        st.warning("No chapters"); return

    current = st.session_state.current_chapter
    chapter = chapters[current]

    # ── Layout: main + notes panel ──
    main_col, notes_col = st.columns([3, 1])

    with main_col:
        # Header bar
        h1, h2, h3 = st.columns([1, 5, 1])
        with h1:
            if st.button("← TOC", key="read_back", use_container_width=True):
                update_chapter_status(book_id, current, "completed")
                log_reading(book_id, current, "end_chapter", detail=chapter["name"])
                st.session_state.current_view = "toc"
                st.rerun()
        with h2:
            st.markdown(f"""
            <div style="text-align:center;">
                <div style="font-weight:700;font-size:1.1rem;">{book['title']}</div>
                <div style="font-size:0.8rem;color:var(--text-tertiary);">
                    {chapter['name']} · Chapter {current + 1}/{len(chapters)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with h3:
            pct = int((current + 1) / len(chapters) * 100)
            st.markdown(f"""
            <div style="text-align:right;">
                <div style="font-weight:700;font-size:1.2rem;">{pct}%</div>
                <div style="font-size:0.7rem;color:var(--text-tertiary);">PROGRESS</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Messages ──
        messages = st.session_state.messages
        for msg in messages:
            role = msg["role"]
            avatar = "🧑" if role == "user" else "📖"
            with st.chat_message(role, avatar=avatar):
                st.write(msg["content"])

        # ── Start button ──
        if not messages:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                if st.button(f"Start Reading", type="primary", use_container_width=True):
                    with st.chat_message("assistant", avatar="📖"):
                        ph = st.empty(); streamed = ""
                        def on_tok(t):
                            nonlocal streamed; streamed += t
                            ph.markdown(streamed + "▌")
                        try:
                            result = start_chapter(book["title"], book["author"],
                                                   chapter["name"], chapter["text"], on_token=on_tok,
                                                   custom_prompt=get_custom_prompt(book_id))
                            ph.markdown(result)
                            st.session_state.messages.append({"role": "assistant", "content": result})
                            save_progress(book_id, current, st.session_state.messages)
                            log_reading(book_id, current, "start_chapter", detail=chapter["name"])
                            st.rerun()
                        except Exception as e:
                            ph.error(f"AI error: {e}")

        # ── Chat input ──
        if messages:
            user_input = st.chat_input("Reply to the author...")
            if user_input:
                # 先追加用户消息
                st.session_state.messages.append({"role": "user", "content": user_input})
                save_progress(book_id, current, st.session_state.messages)
                # 流式生成 AI 回复
                with st.chat_message("assistant", avatar="📖"):
                    ph = st.empty(); streamed = ""
                    def on_tok(t):
                        nonlocal streamed; streamed += t; ph.markdown(streamed + "▌")
                    try:
                        api_msgs = [{"role": m["role"], "content": m["content"]}
                                    for m in st.session_state.messages]
                        result = continue_chat(api_msgs, on_token=on_tok)
                        ph.markdown(result)
                        st.session_state.messages.append({"role": "assistant", "content": result})
                        save_progress(book_id, current, st.session_state.messages)
                        st.rerun()
                    except Exception as e:
                        ph.error(f"AI error: {e}")

            # ── Chapter nav ──
            st.divider()
            cn1, _, cn2 = st.columns([1, 1, 1])
            with cn1:
                if current > 0 and st.button("← Previous", use_container_width=True):
                    update_chapter_status(book_id, current, "completed")
                    log_reading(book_id, current, "end_chapter", detail=chapter["name"])
                    st.session_state.current_chapter = current - 1
                    st.session_state.messages = []
                    save_progress(book_id, current - 1, [])
                    st.rerun()
            with cn2:
                if current < len(chapters) - 1 and st.button("Next →", use_container_width=True):
                    update_chapter_status(book_id, current, "completed")
                    log_reading(book_id, current, "end_chapter", detail=chapter["name"])
                    st.session_state.current_chapter = current + 1
                    st.session_state.messages = []
                    save_progress(book_id, current + 1, [])
                    st.rerun()

    # ── Notes panel (right column) ──
    with notes_col:
        st.markdown('<div class="notes-panel"><h4>📝 本章笔记</h4>', unsafe_allow_html=True)

        # Load existing note
        existing_note = load_note(book_id, current)
        new_note = st.text_area(
            "笔记内容",
            value=existing_note,
            height=300,
            placeholder="在这里记下你的想法...\n\nAI 的知识清单会自动追加到这里。",
            label_visibility="collapsed",
            key=f"note_{book_id}_{current}",
        )

        # Auto-save on change (via button for reliability)
        note_col1, note_col2 = st.columns(2)
        with note_col1:
            if st.button("💾 Save", use_container_width=True, key=f"save_note_{current}"):
                save_note(book_id, current, new_note)
                log_reading(book_id, current, "take_note")
                st.success("Saved!")
                time.sleep(0.5)
                st.rerun()
        with note_col2:
            if existing_note.strip():
                # Export single chapter note
                md = f"# {chapter['name']}\n\n{existing_note}"
                st.download_button(
                    "📥 Export", md,
                    f"{chapter['name'][:20]}.md", "text/markdown",
                    key=f"export_note_{current}",
                    use_container_width=True,
                )

        # ── 自定义提示词 ──
        with st.expander("⚙️ 自定义伴读风格"):
            default_prompt = """你是一位教学者。现在你要扮演一本书的作者，用第一人称"我"来教读者这本书的内容。
## 你的身份
你是《{book_title}》的作者{author}。
## 教学规则
1. 第一人称 + 按章节顺序 + 案例丰富 + 小块输出（3-5段）
2. 讲解 → 提问确认 → 等待回应 → 继续/深入
3. 禁止大段输出、跳跃讲解、未确认就继续
## 结束后
输出本章知识清单：方法论、概念、案例、金句
然后问读者想深入了解哪个知识点。"""

            saved_prompt = get_custom_prompt(book_id)
            prompt_display = saved_prompt if saved_prompt else default_prompt

            custom_prompt = st.text_area(
                "提示词（可用变量：{book_title} {author} {chapter_name} {chapter_text}）",
                value=prompt_display,
                height=250,
                key=f"prompt_{book_id}",
            )

            pc1, pc2 = st.columns(2)
            with pc1:
                if st.button("💾 保存提示词", use_container_width=True, key=f"save_prompt_{book_id}"):
                    save_custom_prompt(book_id, custom_prompt)
                    st.success("提示词已保存！")
                    time.sleep(0.5)
                    st.rerun()
            with pc2:
                if st.button("🔄 恢复默认", use_container_width=True, key=f"reset_prompt_{book_id}"):
                    save_custom_prompt(book_id, "")
                    st.success("已恢复默认提示词")
                    time.sleep(0.5)
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# VIEW: Paste
# ═══════════════════════════════════════
def render_paste():
    st.markdown("""
    <div class="site-header">
        <div class="brand">
            <div class="logo">T</div>
            <span class="name">Paste & Read</span>
        </div>
        <span class="greeting">Video transcripts, blog posts — AI reads with you</span>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        if st.button("← Back to Bookshelf", use_container_width=True):
            st.session_state.current_view = "shelf"
            st.session_state.paste_messages = []
            st.rerun()

    if not st.session_state.paste_messages:
        article = st.text_area(
            "Paste your text below", height=220,
            placeholder="Paste video transcripts, blog posts, or any text here...",
            label_visibility="collapsed")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if article.strip() and st.button("Start AI Reading", type="primary", use_container_width=True):
                with st.chat_message("assistant", avatar="📖"):
                    ph = st.empty(); streamed = ""
                    def on_tok(t):
                        nonlocal streamed; streamed += t; ph.markdown(streamed + "▌")
                    try:
                        result = start_article(article, on_token=on_tok)
                        ph.markdown(result)
                        st.session_state.paste_messages = [{"role": "assistant", "content": result}]
                    except Exception as e:
                        ph.error(f"AI error: {e}")
                st.rerun()

    for msg in st.session_state.paste_messages:
        role = "user" if msg["role"] == "user" else "assistant"
        avatar = "🧑" if msg["role"] == "user" else "📖"
        with st.chat_message(role, avatar=avatar):
            st.write(msg["content"])

    if st.session_state.paste_messages:
        user_input = st.chat_input("Reply...")
        if user_input:
            st.session_state.paste_messages.append({"role": "user", "content": user_input})
            with st.chat_message("assistant", avatar="📖"):
                ph = st.empty(); streamed = ""
                def on_tok(t):
                    nonlocal streamed; streamed += t; ph.markdown(streamed + "▌")
                try:
                    result = continue_chat(st.session_state.paste_messages, on_token=on_tok)
                    ph.markdown(result)
                    st.session_state.paste_messages.append({"role": "assistant", "content": result})
                except Exception as e:
                    ph.error(f"AI error: {e}")


# ═══════════════════════════════════════
# Router
# ═══════════════════════════════════════
view = st.session_state.current_view
if view == "shelf":
    render_shelf()
elif view == "toc":
    render_toc()
elif view == "reading":
    render_reading()
elif view == "paste":
    render_paste()
