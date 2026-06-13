"""PDF/TXT 解析 + 章节检测"""

import os
import re
import fitz  # PyMuPDF


def parse_file(file_path: str) -> dict:
    """
    解析文件，返回:
    {
        "title": "检测到的书名",
        "author": "检测到的作者",
        "full_text": "完整纯文本",
        "chapters": [{"name": "第1章 xxx", "text": "..."}, ...]
    }
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        full_text = _extract_pdf_text(file_path)
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            full_text = f.read()
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    # 尝试从文件名提取标题
    basename = os.path.splitext(os.path.basename(file_path))[0]
    title, author = _guess_metadata(full_text, basename)

    chapters = _split_chapters(full_text)

    return {
        "title": title,
        "author": author,
        "full_text": full_text,
        "chapters": chapters,
    }


def _extract_pdf_text(file_path: str) -> str:
    """从 PDF 提取纯文本"""
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages)


def _guess_metadata(text: str, basename: str) -> tuple[str, str]:
    """从文本头部或文件名猜测书名和作者"""
    head = text[:2000]

    title = basename
    author = ""

    # 常见模式: 《书名》
    title_match = re.search(r"[《「](.+?)[》」]", head)
    if title_match:
        title = title_match.group(1)

    # 作者检测：多种中文模式
    author_patterns = [
        r"(?:作者|著者|原著|编者)[：:]\s*(.+?)(?:\n|$)",  # 作者：xxx
        r"(.+?)\s*(?:著|编著|主编|编)\s*\n",               # xxx 著
        r"\[([^\]]+)\s*(?:著|编著)\]",                     # [xxx 著]
        r"(?:by|By)\s+(.+?)(?:\n|$)",                      # by xxx
        r"^(.{2,4})\s+(?:著|编著)",                         # 开头的作者名
    ]
    for pattern in author_patterns:
        author_match = re.search(pattern, head, re.MULTILINE)
        if author_match:
            candidate = author_match.group(1).strip()
            # 过滤太长的或明显不是人名的
            if 2 <= len(candidate) <= 6 and not re.search(r'[，。！？\d]', candidate):
                author = candidate
                break

    # 从文件名尝试提取
    if not author:
        author = _extract_author_from_filename(basename)

    # 还是没找到，用 AI 提取
    if not author:
        author = _ai_extract_author(head[:3000])

    return title, author


def _ai_extract_author(text: str) -> str:
    """用 AI 从文本中提取作者名"""
    try:
        import os
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": f"从下面文本中提取作者姓名。只输出姓名，不要任何其他文字。如果找不到，输出'无'。\n\n{text[:2000]}"}],
            temperature=0, max_tokens=20,
        )
        result = resp.choices[0].message.content.strip()
        return "" if result == "无" else result
    except Exception:
        return ""


def _extract_author_from_filename(filename: str) -> str:
    """从文件名提取作者，如 '王阳明-传习录' → 王阳明"""
    # 中文字符+常见分隔符
    m = re.match(r"^([一-鿿]{2,4})[\s\-_【\[（(]", filename)
    if m:
        return m.group(1)
    # 最后一个中文词
    parts = re.split(r"[\s\-_【\[（(）)\]】]", filename)
    for p in parts:
        if re.match(r"^[一-鿿]{2,4}$", p):
            return p
    return ""


def _parse_from_toc(text: str) -> list[str]:
    """从书本自带的目录中提取章节名列表"""
    # 找"目录"标记（前5000字内）
    head = text[:5000]
    toc_match = re.search(r"目\s*录\s*\n+", head)
    if not toc_match:
        return []

    toc_start = toc_match.end()
    toc_text = head[toc_start:]

    # 收集目录中的章节名（每行一个，直到遇到空行或正文内容）
    chapter_names = []
    content_start_keywords = ["前言", "序", "第一章", "第1章"]

    for line in toc_text.split("\n"):
        line = line.strip()
        if not line:
            # 空行可能是目录的结束
            if chapter_names:
                break
            continue

        # 跳过明显不是章节名的行（太长的句子、标点密集等）
        if len(line) > 50:
            continue
        if re.search(r"[，。！？；：、""''.]", line):
            continue

        # 干净的行 → 可能是章节名
        chapter_names.append(line)

    # 去重保持顺序，过滤无意义的目录项
    skip_words = {"目录", "目  录", "目 录", "目录 ", "Contents", "CONTENTS",
                  "前言", "序言", "征引与参考书目", "参考文献", "附录", "后记"}
    seen = set()
    unique = []
    for n in chapter_names:
        n = n.strip()
        # 跳过无意义的短名
        if n in skip_words:
            continue
        if len(n) <= 1:  # 单字如"二""又"
            continue
        if re.match(r"^[一二三四五六七八九十]+$", n):  # 纯数字如"二"
            continue
        if n not in seen:
            seen.add(n)
            unique.append(n)

    return unique


def _find_toc_end(text: str) -> int:
    """找到目录区域的结束位置（实际正文开始的地方）"""
    # 找"目录"标记
    m = re.search(r"目\s*录\s*\n+", text[:5000])
    if not m:
        return 0
    toc_start = m.start()

    # 目录通常结束于第一个"前言"、"序"或正文段落（超过200字的连续文本）
    after_toc = text[m.end():m.end() + 5000]

    # 策略：找到第一个在目录中列出但实际作为正文标题出现的位置
    # 目录后的第一个实质性标题通常是"前言"或"序"
    for keyword in ["前言", "序", "第一章", "第1章"]:
        idx = after_toc.find(f"\n{keyword}\n")
        if idx == -1:
            idx = after_toc.find(f"\n{keyword}")
        if idx > 0:
            return m.end() + idx

    # 回退：找目录后第一个大段落（超过300字）
    paras = after_toc.split("\n\n")
    pos = m.end()
    for p in paras:
        p = p.strip()
        if len(p) > 300:
            return pos
        pos += len(p) + 2

    return m.end()


def _build_chapters(text: str, chapter_names: list[str]) -> list[dict]:
    """根据章节名列表拆分文本 —— 跳过目录区，在正文中定位"""
    # 找到目录结束位置，只在正文中搜索章节位置
    content_start = _find_toc_end(text)
    body_text = text[content_start:]

    positions = []  # [(name, absolute_pos, end_pos), ...]
    for name in chapter_names:
        escaped = re.escape(name)
        # 在正文中找独占一行的章节名
        m = re.search(rf"(?:^|\n)\s*{escaped}\s*(?:\n|$)", body_text, re.MULTILINE)
        if m:
            abs_pos = content_start + m.start()
            abs_end = content_start + m.end()
            positions.append((name, abs_pos, abs_end))

    if len(positions) < 2:
        return None

    # 按位置排序
    positions.sort(key=lambda x: x[1])

    # 每个章节的内容：从本章标题后到下一章标题前
    chapters = []
    for i, (name, start, end) in enumerate(positions):
        next_start = positions[i + 1][1] if i + 1 < len(positions) else len(text)
        content = text[end:next_start].strip()
        summary = content[:120].replace("\n", " ").strip() if content else ""

        chapters.append({
            "name": name,
            "text": content,
            "summary": summary,
            "level": 1,
            "subsections": [],
            "status": "unread",
            "bookmarked": False,
        })

    return chapters


def _split_chapters(text: str) -> list[dict]:
    """按章节拆分，支持 TOC 目录 和 第X章 两种格式"""

    # ── 优先：检测书本自带的目录（适用于古典/中文书籍）──
    toc_chapters = _parse_from_toc(text)
    if toc_chapters and len(toc_chapters) >= 3:
        result = _build_chapters(text, toc_chapters)
        if result:
            return result

    # ── 回退：第X章 / Chapter X ──
    primary_pattern = re.compile(
        r"(?:^|\n)\s*"
        r"((?:第[零一二三四五六七八九十百千\d]+[章部篇]|"
        r"Chapter\s+\d+|CHAPTER\s+\d+)\s*.*?)(?:\n|$)",
        re.MULTILINE,
    )
    
    secondary_pattern = re.compile(
        r"(?:^|\n)\s*"
        r"((?:第[零一二三四五六七八九十百千\d]+节|"
        r"\d+\.\d+\s+.*?|"
        r"Section\s+\d+|SECTION\s+\d+)\s*.*?)(?:\n|$)",
        re.MULTILINE,
    )

    # 首先尝试匹配一级标题
    primary_matches = list(primary_pattern.finditer(text))
    
    if not primary_matches:
        # 无章节标记，尝试按段落智能分段
        return _smart_split(text)

    chapters = []
    for i, match in enumerate(primary_matches):
        name = match.group(1).strip()
        start = match.end()
        end = primary_matches[i + 1].start() if i + 1 < len(primary_matches) else len(text)
        content = text[start:end].strip()
        
        # 提取内容摘要（前200字符）
        summary = content[:200].replace("\n", " ").strip()
        if len(content) > 200:
            summary += "..."
        
        # 检测该章节下的二级标题
        section_matches = list(secondary_pattern.finditer(content))
        subsections = []
        if section_matches:
            for j, sec_match in enumerate(section_matches):
                sec_name = sec_match.group(1).strip()
                sec_start = sec_match.end()
                sec_end = section_matches[j + 1].start() if j + 1 < len(section_matches) else len(content)
                subsections.append({
                    "name": sec_name,
                    "text": content[sec_start:sec_end].strip()
                })
        
        chapters.append({
            "name": name,
            "text": content,
            "summary": summary,
            "level": 1,
            "subsections": subsections,
            "status": "unread",  # 状态：unread, reading, completed
            "bookmarked": False,
        })

    # 如果有前言（第一章之前的文字），加入
    if primary_matches and primary_matches[0].start() > 0:
        preamble = text[: primary_matches[0].start()].strip()
        if preamble and len(preamble) > 200:
            summary = preamble[:200].replace("\n", " ").strip() + "..."
            chapters.insert(0, {
                "name": "前言/绪论",
                "text": preamble,
                "summary": summary,
                "level": 1,
                "subsections": [],
                "status": "unread",
                "bookmarked": False,
            })

    return chapters


def _smart_split(text: str, chunk_size: int = 5000, max_chapters: int = 25) -> list[dict]:
    """智能分段：按段落切分，大块合并，超过上限则自动调大块大小"""
    # 先按双换行分，分不出来按单换行
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    total = len(text)

    # 自动调整块大小，确保不超过 max_chapters
    if total / chunk_size > max_chapters:
        chunk_size = total // max_chapters + 1

    chapters = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current.strip():
            ch_text = current.strip()
            chapters.append(_make_chapter(ch_text))
            current = para
        else:
            current += "\n\n" + para

    if current.strip():
        chapters.append(_make_chapter(current.strip()))

    # 如果还是太多，合并相邻章
    while len(chapters) > max_chapters:
        merged = []
        for i in range(0, len(chapters), 2):
            if i + 1 < len(chapters):
                merged.append(_make_chapter(
                    chapters[i]["text"] + "\n\n" + chapters[i + 1]["text"]
                ))
            else:
                merged.append(chapters[i])
        chapters = merged

    # 如果章节名是英文，用 AI 翻译成中文
    if chapters and not _has_chinese("".join(ch["name"] for ch in chapters[:3])):
        try:
            names = [ch["name"] for ch in chapters]
            cn_names = translate_names(names)
            for ch, cn in zip(chapters, cn_names):
                ch["name"] = cn
        except Exception:
            pass

    return chapters


def _make_chapter(text: str) -> dict:
    """从文本块创建章节，章节名简短可读"""
    lines = text.split("\n")
    raw = lines[0].strip() if lines else ""

    # 截到合适长度
    for sep in [". ", "! ", "? ", "。", "！", "？"]:
        idx = raw.find(sep)
        if 8 <= idx <= 30:
            raw = raw[:idx + 1]
            break
    if len(raw) > 25:
        raw = raw[:25] + "..."

    summary = text[:120].replace("\n", " ").strip()

    return {
        "name": raw,
        "text": text,
        "summary": summary,
        "level": 1,
        "subsections": [],
        "status": "unread",
        "bookmarked": False,
    }


def _has_chinese(s: str) -> bool:
    """判断字符串是否包含中文"""
    return bool(re.search(r'[一-鿿]', s))


def translate_names(names: list[str]) -> list[str]:
    """批量翻译章节名为中文"""
    import os
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    joined = "\n".join(f"{i}: {n}" for i, n in enumerate(names))
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": f"把下面这些英文章节名翻译成简洁中文（每行一个，不超过20字，保留编号）：\n{joined}"}],
            temperature=0.3, max_tokens=500,
        )
        result = []
        for line in resp.choices[0].message.content.strip().split("\n"):
            if ":" in line:
                result.append(line.split(":", 1)[1].strip())
            else:
                result.append(line.strip())
        # 补齐缺失的
        while len(result) < len(names):
            result.append(names[len(result)][:20])
        return result[:len(names)]
    except Exception:
        return [n[:20] for n in names]


def extract_article_text(raw_text: str) -> str:
    """清理粘贴的文本"""
    # 去除多余空行
    text = re.sub(r"\n{4,}", "\n\n\n", raw_text)
    return text.strip()
