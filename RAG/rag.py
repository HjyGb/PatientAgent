"""RAG function using LangChain for patient information retrieval."""

import os
from dotenv import load_dotenv

from RAG.helper_functions import (
    RecursiveCharacterTextSplitter,
    BailianEmbeddings,
    FAISS,
    retrieve_context_per_question,
)

load_dotenv()


def encode_from_string(content: str, chunk_size: int, chunk_overlap: int):
    """Split text into chunks and build a FAISS vector store."""
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
    return vectorstore


def rag_patient(question: str, resource: str, size: int, overlap: int, top_k: int) -> str:
    """Retrieve relevant context from patient resource using RAG."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not detected. Please set it in env or .env.")

    chunks_vector_store = encode_from_string(resource, chunk_size=size, chunk_overlap=overlap)
    chunks_query_retriever = chunks_vector_store.as_retriever(search_kwargs={"k": top_k})

    context = retrieve_context_per_question(question, chunks_query_retriever)

    rag_info = "".join(context)
    return rag_info
