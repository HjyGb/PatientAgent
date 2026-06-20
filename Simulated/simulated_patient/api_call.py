"""Unified LLM and embedding API client.

All model names are read from environment variables with sensible defaults,
so you never need to edit source code to switch models.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from utils import ensure_parent


# ====== Configuration via environment variables ======
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL")  # e.g. https://ark.cn-beijing.volces.com/api/v3

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY env var not found. Please set it before running.")

client_kwargs = {"api_key": OPENAI_API_KEY}
if BASE_URL:
    client_kwargs["base_url"] = BASE_URL

client = OpenAI(**client_kwargs)

# Model names — override via env vars if needed
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_LITE_MODEL = os.getenv("LLM_LITE_MODEL", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")


# ====== Token counter ======
def token_counter(usage: dict) -> None:
    """Accumulate token usage into log files."""
    file_path_overall = Path("make_task/token_count/token_overall.txt")
    file_path_stream = Path("make_task/token_count/token_stream.txt")

    ensure_parent(file_path_overall)
    ensure_parent(file_path_stream)

    token_str_stream = file_path_stream.read_text(encoding="utf-8") if file_path_stream.exists() else ""
    token_str_overall = file_path_overall.read_text(encoding="utf-8") if file_path_overall.exists() else ""

    # Filter to only numeric values (skip None and nested dicts like *_token_details)
    numeric_usage = {k: v for k, v in usage.items() if isinstance(v, (int, float))}

    with file_path_stream.open("w", encoding="utf-8") as tok:
        for key, value in numeric_usage.items():
            token_str_stream += f"{key}: **{value}**\n"
        tok.write(token_str_stream)

    if not token_str_overall.strip():
        with file_path_overall.open("w", encoding="utf-8") as tok:
            tok.write(token_str_stream)
    else:
        numbers = [int(num) for num in re.findall(r"\d+", token_str_overall)]
        token_str_new = ""
        with file_path_overall.open("w", encoding="utf-8") as tok:
            for i, (key, value) in enumerate(numeric_usage.items()):
                token_str_new += f"{key}: **{value + numbers[i]}**\n"
            tok.write(token_str_new)


# ====== LLM API ======
def llm_api(messages, model: str | None = None, temperature: float = 0.2) -> str:
    """Call the chat completion API and return the response text."""
    model = model or LLM_MODEL
    response = client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=temperature,
        top_p=1.0,
        n=1,
        stream=False,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        logit_bias={},
    ).model_dump()
    response_text = response["choices"][0]["message"]["content"]
    token_counter(response["usage"])
    return response_text


def llm_api_lite(messages, model: str | None = None, temperature: float = 0.2) -> str:
    """Call the lite (cheaper/faster) chat completion API."""
    model = model or LLM_LITE_MODEL
    response = client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=temperature,
        top_p=1.0,
        n=1,
        stream=False,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        logit_bias={},
    ).model_dump()
    response_text = response["choices"][0]["message"]["content"]
    token_counter(response["usage"])
    return response_text


# ====== Embedding API ======
def get_text_embedding(text: str, model: str | None = None) -> list:
    """Get text embedding vector."""
    model = model or EMBEDDING_MODEL
    text = text or "None"
    return client.embeddings.create(
        input=text,
        model=model,
    ).model_dump()["data"][0]["embedding"]


def get_code_embedding(code: str, model: str | None = None) -> list:
    """Get code embedding vector (uses the same embedding model by default)."""
    model = model or EMBEDDING_MODEL
    code = code or "#"
    return client.embeddings.create(
        input=code,
        model=model,
    ).model_dump()["data"][0]["embedding"]
