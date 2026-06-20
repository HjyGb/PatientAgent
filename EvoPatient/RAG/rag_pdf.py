"""RAG pipeline for PDF documents."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Allow imports from parent directory
sys.path.append(str(Path.cwd().parent))
from helper_functions import (  # noqa: F401
    PyPDFLoader,
    RecursiveCharacterTextSplitter,
    OpenAIEmbeddings,
    FAISS,
    replace_t_with_space,
    retrieve_context_per_question,
    show_context,
)
from evaluation.evalute_rag import evaluate_rag  # noqa: F401

# Load environment variables
load_dotenv()


def encode_pdf(path: Path, chunk_size: int = 1000, chunk_overlap: int = 200):
    """Encode a PDF into a FAISS vector store."""
    loader = PyPDFLoader(str(path))
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
    )
    texts = text_splitter.split_documents(documents)
    cleaned_texts = replace_t_with_space(texts)

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(cleaned_texts, embeddings)
    return vectorstore


def run_demo():
    """Run a demo query on a PDF document."""
    pdf_path = Path("../data/Multi-Agent Collaboration via Cross-Team Orchestration.pdf")
    chunks_vector_store = encode_pdf(pdf_path, chunk_size=1000, chunk_overlap=200)
    chunks_query_retriever = chunks_vector_store.as_retriever(search_kwargs={"k": 2})

    test_query = "What is the main content of this article?"
    context = retrieve_context_per_question(test_query, chunks_query_retriever)
    show_context(context)

    evaluate_rag(chunks_query_retriever)


if __name__ == "__main__":
    run_demo()
