"""AI 阅读引擎 —— DeepSeek API 流式调用"""

import os

import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from prompt import build_system_prompt, build_paste_prompt, build_mode_prompt

# 修复 Windows 中文环境下 ASCII 编码问题
os.environ["PYTHONUTF8"] = "1"

load_dotenv()


def _get_api_key() -> str | None:
    """优先从 Streamlit Secrets 取，兼容本地 .env"""
    try:
        return st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        return os.getenv("DEEPSEEK_API_KEY")


def _get_base_url() -> str:
    """优先从 Streamlit Secrets 取，兼容本地 .env"""
    try:
        return st.secrets.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    except Exception:
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


@st.cache_resource(show_spinner=False)
def _get_client() -> OpenAI:
    """获取 OpenAI 客户端（Streamlit 资源缓存，全局复用）"""
    return OpenAI(
        api_key=_get_api_key(),
        base_url=_get_base_url(),
    )


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
    mode_id: str = "default",
) -> str:
    """开始阅读一个章节，返回 AI 的首段回复。

    优先级：custom_prompt（用户自定义）> mode_id（预设模式）> 默认。
    """
    if custom_prompt.strip():
        # 使用自定义提示词，替换变量占位符
        system_prompt = custom_prompt.replace("{book_title}", book_title)\
            .replace("{author}", author)\
            .replace("{chapter_name}", chapter_name)\
            .replace("{chapter_text}", chapter_text)
    elif mode_id and mode_id != "default":
        # 使用预设阅读模式
        system_prompt = build_mode_prompt(
            book_title, author, chapter_name, chapter_text, mode_id,
        )
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
