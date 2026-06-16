"""设计系统 CSS —— 浅/深双主题，现代极简"""


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

/* ── 按钮统一样式：全部白底深字，靠描边粗细区分层级 ── */
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
.stButton button,
.stDownloadButton button,
.stFormSubmitButton button {
    border-radius: 10px !important;
    font-family: 'Noto Sans SC', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.87rem !important;
    transition: all 0.15s !important;
    background: #FFFFFF !important;
    color: #111827 !important;
}
/* secondary：浅灰描边 */
[data-testid="stBaseButton-secondary"],
.stButton button,
.stDownloadButton button,
.stFormSubmitButton button {
    border: 1px solid #E5E5E5 !important;
}
[data-testid="stBaseButton-secondary"]:hover,
.stButton button:hover,
.stDownloadButton button:hover {
    background: #F7F7F7 !important;
    border-color: #9CA3AF !important;
    color: #111827 !important;
}
/* primary：深色描边（更醒目，但仍是白底） */
[data-testid="stBaseButton-primary"],
.stButton button[kind="primary"] {
    border: 1.5px solid #111827 !important;
    background: #FFFFFF !important;
    color: #111827 !important;
    font-weight: 600 !important;
}
[data-testid="stBaseButton-primary"]:hover,
.stButton button[kind="primary"]:hover {
    background: #F7F7F7 !important;
    border-color: #374151 !important;
    color: #111827 !important;
}
/* 深色主题：白底在深色背景上仍然成立 */
[data-theme="dark"] [data-testid="stBaseButton-secondary"],
[data-theme="dark"] [data-testid="stBaseButton-primary"],
[data-theme="dark"] .stButton button,
[data-theme="dark"] .stDownloadButton button {
    background: #FFFFFF !important;
    color: #111827 !important;
}
[data-theme="dark"] [data-testid="stBaseButton-secondary"],
[data-theme="dark"] .stButton button,
[data-theme="dark"] .stDownloadButton button {
    border: 1px solid #E5E5E5 !important;
}
[data-theme="dark"] [data-testid="stBaseButton-primary"],
[data-theme="dark"] .stButton button[kind="primary"] {
    border: 1.5px solid #111827 !important;
    font-weight: 600 !important;
}

/* ── 聊天 ── */
.stChatMessage {
    border-radius: 14px !important;
    padding: 1rem 1.2rem !important;
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
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

/* ── 环形进度图 ── */
.progress-ring {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.progress-ring svg {
    transform: rotate(-90deg);  /* 从顶部开始 */
}
.progress-ring .ring-bg {
    stroke: var(--border);
    fill: none;
}
.progress-ring .ring-fill {
    stroke: var(--accent);
    fill: none;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.6s ease;
}
.progress-ring .ring-text {
    position: absolute;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
}
.progress-ring .ring-label {
    position: absolute;
    bottom: -1.2rem;
    font-size: 0.68rem;
    color: var(--text-tertiary);
    letter-spacing: 0.05em;
    white-space: nowrap;
}
/* 书卡上的小进度环 */
.progress-ring.sm .ring-text { font-size: 0.8rem; }
/* 阅读页上的大进度环 */
.progress-ring.lg .ring-text { font-size: 1.1rem; }

/* ── 阅读统计页 ── */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.8rem;
    margin: 1rem 0;
}
.stat-card {
    background: var(--bg-subtle);
    border-radius: 12px;
    padding: 1.2rem 1rem;
    text-align: center;
}
.stat-card .sc-icon { font-size: 1.5rem; margin-bottom: 0.4rem; }
.stat-card .sc-value { font-size: 1.6rem; font-weight: 700; color: var(--text); line-height: 1.1; }
.stat-card .sc-label { font-size: 0.78rem; color: var(--text-tertiary); margin-top: 0.3rem; }

/* 周阅读时长条形图 */
.weekly-bars {
    display: flex; align-items: flex-end; gap: 8px;
    height: 120px; padding: 1rem 0 0.5rem;
}
.wb-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; height: 100%; justify-content: flex-end; }
.wb-bar {
    width: 100%; max-width: 40px;
    background: var(--accent); border-radius: 6px 6px 0 0;
    min-height: 3px; opacity: 0.85; transition: height 0.5s;
    position: relative;
}
.wb-col:hover .wb-bar { opacity: 1; }
.wb-bar-tip {
    position: absolute; top: -1.3rem; left: 50%; transform: translateX(-50%);
    font-size: 0.65rem; color: var(--text-secondary); white-space: nowrap;
    opacity: 0; transition: opacity 0.2s;
}
.wb-col:hover .wb-bar-tip { opacity: 1; }
.wb-label { font-size: 0.7rem; color: var(--text-tertiary); }

/* 各书进度行 */
.book-stat-row {
    display: flex; align-items: center; gap: 1rem;
    background: var(--card); border-radius: 12px; padding: 0.9rem 1.1rem;
    margin-bottom: 0.5rem;
}
.book-stat-row .bsr-info { flex: 1; min-width: 0; }
.book-stat-row .bsr-title { font-weight: 600; font-size: 0.95rem; color: var(--text); }
.book-stat-row .bsr-meta { font-size: 0.78rem; color: var(--text-tertiary); margin-top: 2px; }
.book-stat-row .bsr-track {
    flex: 0 0 120px; height: 6px; background: var(--border);
    border-radius: 3px; overflow: hidden;
}
.book-stat-row .bsr-fill { height: 100%; background: var(--accent); border-radius: 3px; }
.book-stat-row .bsr-pct { font-size: 0.85rem; font-weight: 600; color: var(--text); min-width: 38px; text-align: right; }
</style>
"""
