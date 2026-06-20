"""Sentence embedding using DashScope/OpenAI-compatible API."""

import os
from dotenv import load_dotenv
from openai import OpenAI


def get_embeddings(text: str, model: str | None = None) -> list:
    """Generate text embedding via DashScope/OpenAI-compatible API.

    Reads OPENAI_API_KEY and OPENAI_API_BASE from environment variables.
    """
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE")
    model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not detected. Please set it in .env or system environment.")

    client = OpenAI(api_key=api_key, base_url=base_url)

    completion = client.embeddings.create(
        model=model,
        input=text,
        encoding_format="float"
    ).model_dump()

    return completion["data"][0]["embedding"]
