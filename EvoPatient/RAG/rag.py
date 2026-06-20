"""RAG function using LangChain for patient information retrieval."""

import os
import hashlib
from dotenv import load_dotenv

from RAG.helper_functions import (
    RecursiveCharacterTextSplitter,
    BailianEmbeddings,
    FAISS,
    retrieve_context_per_question,
)

load_dotenv()

# ── FAISS vector store cache ──────────────────────────────────
# Key: hash(resource, chunk_size, chunk_overlap) → FAISS vectorstore
# Patient records are static during a session — avoids re-embedding
# the same text on every turn (saves ~2.3s per turn on CPU).
_VECTOR_STORE_CACHE: dict[str, FAISS] = {}


def _make_cache_key(resource: str, chunk_size: int, chunk_overlap: int) -> str:
    return hashlib.sha256(
        f"{resource}|{chunk_size}|{chunk_overlap}".encode()
    ).hexdigest()


def encode_from_string(content: str, chunk_size: int, chunk_overlap: int):
    """Split text into chunks and build a FAISS vector store (with cache)."""
    cache_key = _make_cache_key(content, chunk_size, chunk_overlap)
    if cache_key in _VECTOR_STORE_CACHE:
        return _VECTOR_STORE_CACHE[cache_key]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.create_documents([content])

    for chunk in chunks:
        chunk.metadata["relevance_score"] = 1.0

    embeddings = BailianEmbeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Cache for reuse (same patient is queried many times in one session)
    _VECTOR_STORE_CACHE[cache_key] = vectorstore
    return vectorstore


def clear_vector_cache():
    """Clear the FAISS vector store cache (call between sessions)."""
    _VECTOR_STORE_CACHE.clear()


def rag_patient(question: str, resource: str, size: int, overlap: int, top_k: int) -> str:
    """Retrieve relevant context from patient resource using RAG.

    The FAISS index is cached by resource content hash — first call takes
    ~2.3s (CPU embed of all chunks), subsequent calls are instant (~1ms).
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not detected. Please set it in env or .env.")

    chunks_vector_store = encode_from_string(resource, chunk_size=size, chunk_overlap=overlap)
    chunks_query_retriever = chunks_vector_store.as_retriever(search_kwargs={"k": top_k})

    context = retrieve_context_per_question(question, chunks_query_retriever)

    rag_info = "".join(context)
    return rag_info
