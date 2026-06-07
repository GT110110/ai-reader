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

    # 常见模式: 《书名》 / 书名 by 作者 / Title by Author
    title_match = re.search(r"[《「](.+?)[》」]", head)
    if title_match:
        title = title_match.group(1)

    author_match = re.search(r"(?:作者|著者)[：:]\s*(.+?)(?:\n|$)", head)
    if not author_match:
        author_match = re.search(r"(?:by|By)\s+(.+?)(?:\n|$)", head)
    if author_match:
        author = author_match.group(1).strip()

    return title, author


def _split_chapters(text: str) -> list[dict]:
    """按章节拆分，支持多级标题"""
    # 匹配: 第X章 / 第X节 / Chapter X / CHAPTER X / 一级、二级标题
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


def _smart_split(text: str) -> list[dict]:
    """智能分段：无明确章节时按内容长度分段"""
    # 按双换行分段
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    if not paragraphs:
        return [{
            "name": "全文",
            "text": text,
            "summary": text[:200].replace("\n", " ").strip() + ("..." if len(text) > 200 else ""),
            "level": 1,
            "subsections": [],
            "status": "unread",
            "bookmarked": False,
        }]
    
    # 每5000字符作为一个章节
    chapters = []
    current_chunk = ""
    chunk_idx = 1
    
    for para in paragraphs:
        if len(current_chunk) + len(para) > 5000 and current_chunk:
            summary = current_chunk[:200].replace("\n", " ").strip() + "..."
            chapters.append({
                "name": f"第{chunk_idx}部分",
                "text": current_chunk,
                "summary": summary,
                "level": 1,
                "subsections": [],
                "status": "unread",
                "bookmarked": False,
            })
            current_chunk = para
            chunk_idx += 1
        else:
            current_chunk += "\n\n" + para
    
    # 添加最后一段
    if current_chunk:
        summary = current_chunk[:200].replace("\n", " ").strip()
        if len(current_chunk) > 200:
            summary += "..."
        chapters.append({
            "name": f"第{chunk_idx}部分",
            "text": current_chunk,
            "summary": summary,
            "level": 1,
            "subsections": [],
            "status": "unread",
            "bookmarked": False,
        })
    
    return chapters


def extract_article_text(raw_text: str) -> str:
    """清理粘贴的文本"""
    # 去除多余空行
    text = re.sub(r"\n{4,}", "\n\n\n", raw_text)
    return text.strip()
