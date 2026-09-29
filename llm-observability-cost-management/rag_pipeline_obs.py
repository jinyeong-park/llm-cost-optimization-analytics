"""rag_pipeline_obs.py - Complete RAG Pipeline with Langfuse Observability

Required packages:
    pip install langfuse chromadb sentence-transformers anthropic langchain langchain-community
"""

from langfuse import observe, Langfuse, get_client
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
import chromadb
import anthropic
import os

# LangChain imports for document loading
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

load_dotenv()

# Initialize chromadb with persistent storage
chroma = chromadb.PersistentClient(path="./chroma_db")
collection = chroma.get_or_create_collection(
    name="documents", metadata={"hnsw:space": "cosine"}
)

# initialize embedding model once
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # dim 384


# =============================================================================
# DOCUMENT INDEXING PIPELINE
# =============================================================================
@observe
def load_and_index_documents(docs_dir: str = "./docs") -> int:

    documents = load_markdown_docs(docs_dir)
    if not documents:
        return 0

    chunks = chunk_documents(documents)
    return index_chunks(chunks)


@observe()
def load_markdown_docs(docs_dir: str) -> List:
    """Load all markdown files from directory using LangChain."""
    if not os.path.exists(docs_dir):
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")

    # Use TextLoader for .md files (simpler, fewer dependencies)
    loader = DirectoryLoader(
        docs_dir,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    documents = loader.load()

    # Update current span with metadata (Langfuse SDK v3)
    get_client().update_current_span(
        metadata={"docs_loaded": len(documents), "docs_dir": docs_dir}
    )
    return documents


@observe()
def chunk_documents(
    documents: List, chunk_size: int = 1000, chunk_overlap: int = 200
) -> List:
    """Split documents into smaller chunks for retrieval."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)

    get_client().update_current_span(
        metadata={"total_chunks": len(chunks), "chunk_size": chunk_size}
    )
    return chunks


@observe()
def index_chunks(chunks: List) -> int:
    """Create embeddings and store in ChromaDB."""
    ids, documents, metadatas, embeddings = [], [], [], []

    for i, chunk in enumerate(chunks):
        embedding = embedding_model.encode(chunk.page_content).tolist()
        ids.append(f"chunk_{i}")
        documents.append(chunk.page_content)
        metadatas.append({"source": chunk.metadata.get("source", "unknown")})
        embeddings.append(embedding)

    collection.upsert(
        ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
    )

    get_client().update_current_span(
        metadata={"chunks_indexed": len(chunks), "embedding_model": "all-MiniLM-L6-v2"}
    )
    return len(chunks)


# =============================================================================
# RAG QUERY PIPELINE
# =============================================================================


@observe()
def rag_pipeline(query: str) -> str:
    """
    Complete RAG pipeline with full observability.
    Each step becomes a span in the trace.
    """
    query_embedding = embed_query(query)
    chunks = retrieve_chunks(query_embedding)
    context = build_context(chunks)
    response = generate_response(query, context)
    return response


@observe()
def embed_query(query: str) -> List[float]:
    """Embed the user query."""
    embedding = embedding_model.encode(query).tolist()

    get_client().update_current_span(
        metadata={"query_length": len(query), "embedding_dim": len(embedding)}
    )
    return embedding


@observe()
def retrieve_chunks(embedding: List[float], top_k: int = 5) -> List[Dict]:
    """Retrieve relevant document chunks from ChromaDB."""
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            chunks.append(
                {
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

    get_client().update_current_span(
        metadata={
            "chunks_retrieved": len(chunks),
            "avg_distance": (
                sum(c["distance"] for c in chunks) / len(chunks) if chunks else 0
            ),
        }
    )
    return chunks


@observe()
def build_context(chunks: List[Dict]) -> str:
    """Assemble retrieved chunks into context string."""
    if not chunks:
        return "No relevant context found."

    context_parts = []
    for i, chunk in enumerate(chunks):
        source = chunk["metadata"].get("source", "unknown")
        context_parts.append(f"[Source {i+1} - {source}]: {chunk['content']}")

    context = "\n\n".join(context_parts)

    get_client().update_current_span(
        metadata={"context_length": len(context), "num_chunks_used": len(chunks)}
    )
    return context


@observe(as_type="generation")
def generate_response(query: str, context: str) -> str:
    """Generate response using Claude with token tracking."""
    client = anthropic.Anthropic()

    prompt = f"""Use the following context to answer the question.
If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {query}

Answer:"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    # Log generation details including token usage
    get_client().update_current_generation(
        model="claude-sonnet-4-20250514",
        usage_details={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        metadata={"prompt_length": len(prompt)},
    )
    return response.content[0].text


if __name__ == "__main__":
    # Step 1: Index documents (run once or when docs change)
    print("Indexing documents from ./docs folder...")
    try:
        num_indexed = load_and_index_documents("./docs")
        print(f"Indexed {num_indexed} chunks")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Create a 'docs' folder with .md files first.")
        exit(1)

    # Step 2: Query the RAG pipeline
    print("\nQuerying RAG pipeline...")
    result = rag_pipeline("What is Llamaindex and how do I set up?")
    print(f"\nResponse:\n{result}")

    # Always flush in short-lived scripts
    get_client().flush()
