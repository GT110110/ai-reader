"""AI 阅读引擎 —— DeepSeek API 流式调用"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from prompt import build_system_prompt, build_paste_prompt

# 修复 Windows 中文环境下 ASCII 编码问题
os.environ["PYTHONUTF8"] = "1"

load_dotenv()

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    return _client


def stream_chat(
    messages: list,
    on_token=None,
    model: str = "deepseek-chat",
) -> str:
    """流式对话，每收到 token 回调 on_token(token_text)"""
    client = _get_client()

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.7,
        max_tokens=4096,
    )

    full_text = ""
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            token = chunk.choices[0].delta.content
            full_text += token
            if on_token:
                on_token(token)

    return full_text


def start_chapter(
    book_title: str,
    author: str,
    chapter_name: str,
    chapter_text: str,
    history: list = None,
    on_token=None,
    custom_prompt: str = "",
) -> str:
    """开始阅读一个章节，返回 AI 的首段回复"""
    if custom_prompt.strip():
        # 使用自定义提示词，替换变量占位符
        system_prompt = custom_prompt.replace("{book_title}", book_title)\
            .replace("{author}", author)\
            .replace("{chapter_name}", chapter_name)\
            .replace("{chapter_text}", chapter_text)
    else:
        system_prompt = build_system_prompt(
            book_title=book_title,
            author=author,
            chapter_name=chapter_name,
            chapter_text=chapter_text,
        )

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        messages = [messages[0]] + history

    # 首条用户消息触发开始
    messages.append({"role": "user", "content": "请开始讲解这一章。"})

    return stream_chat(messages, on_token=on_token)


def continue_chat(
    messages: list,
    on_token=None,
) -> str:
    """继续对话"""
    return stream_chat(messages, on_token=on_token)


def start_article(article_text: str, on_token=None) -> str:
    """开始阅读粘贴的文章"""
    system_prompt = build_paste_prompt(article_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请开始带我理解这篇文章。"},
    ]

    return stream_chat(messages, on_token=on_token)
