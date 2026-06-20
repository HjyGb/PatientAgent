"""Fusion retrieval: combine BM25 keyword search with FAISS vector search."""

import os
import sys
from typing import List
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
import numpy as np

# Allow imports from parent directory
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))
from helper_functions import (  # noqa: F401
    RecursiveCharacterTextSplitter,
    BailianEmbeddings,
    FAISS,
    show_context,
    replace_t_with_space_for_text,
)

# Load environment variables
load_dotenv()


def encode_text_and_get_split_documents(content: str, chunk_size: int = 200, chunk_overlap: int = 50):
    """Split text -> clean -> build vector index."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
    )
    texts = text_splitter.split_text(content)
    cleaned_texts = replace_t_with_space_for_text(texts)

    from RAG.helper_functions import BailianEmbeddings
    embeddings = BailianEmbeddings()
    vectorstore = FAISS.from_texts(cleaned_texts, embeddings)

    return vectorstore, cleaned_texts


def create_bm25_index(texts: List[str]) -> BM25Okapi:
    """Create a BM25 index from a list of tokenized texts."""
    tokenized_docs = [doc.split() for doc in texts]
    return BM25Okapi(tokenized_docs)


def _safe_minmax_norm(arr: np.ndarray) -> np.ndarray:
    """Min-max normalization; returns zeros when max == min to avoid division by zero."""
    if arr.size == 0:
        return arr
    a_min, a_max = np.min(arr), np.max(arr)
    if a_max == a_min:
        return np.zeros_like(arr)
    return (arr - a_min) / (a_max - a_min)


def fusion_retrieval(
    vectorstore,
    bm25: BM25Okapi,
    query: str,
    all_texts: List[str],
    k: int = 5,
    alpha: float = 0.5,
) -> List[Document]:
    """Hybrid retrieval combining BM25 keyword scores with FAISS vector scores.

    Args:
        vectorstore: FAISS vector store.
        bm25: Pre-built BM25 index.
        query: The search query.
        all_texts: All text chunks (aligned with BM25 index).
        k: Number of top results to return.
        alpha: Weight for vector scores; (1 - alpha) for BM25 scores.
    """
    # 1) Build Document objects from all_texts
    all_docs: List[Document] = [Document(page_content=t) for t in all_texts]

    # 2) BM25 scores (aligned with all_docs order)
    bm25_scores = bm25.get_scores(query.split())

    # 3) Vector retrieval scores (FAISS distance: smaller = more similar)
    vec_results = vectorstore.similarity_search_with_score(query, k=len(all_texts))
    content2dist = {doc.page_content: dist for doc, dist in vec_results}
    fallback = (max(content2dist.values()) + 1.0) if content2dist else 1.0
    vector_dists = np.array([content2dist.get(t, fallback) for t in all_texts], dtype=float)
    vector_scores = 1.0 - _safe_minmax_norm(vector_dists)  # distance -> similarity

    # 4) Normalize BM25 scores
    bm25_scores = _safe_minmax_norm(np.array(bm25_scores, dtype=float))

    # 5) Combine scores
    combined_scores = alpha * vector_scores + (1.0 - alpha) * bm25_scores

    # 6) Sort and return top-k
    sorted_indices = np.argsort(combined_scores)[::-1]
    top_indices = sorted_indices[:k]
    return [all_docs[i] for i in top_indices]


def run_demo():
    """Run a demo query using fusion retrieval."""
    content = (
        '1. Patient, male, 33 years old. Admitted due to right ear tinnitus with hearing loss. Diagnosed with nasopharyngeal carcinoma. Mild sinusitis; left mastoiditis.'
    )
    vectorstore, cleaned_texts = encode_text_and_get_split_documents(content)
    bm25 = create_bm25_index(cleaned_texts)

    query = "Have there been any symptoms like coughing recently?"
    top_docs = fusion_retrieval(vectorstore, bm25, query, all_texts=cleaned_texts, k=5, alpha=0.5)
    docs_content = [doc.page_content for doc in top_docs]
    show_context(docs_content)


if __name__ == "__main__":
    run_demo()
