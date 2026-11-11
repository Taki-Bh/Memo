import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams


COLLECTION_NAME = "rag_collection"
QDRANT_PATH = "./qdrant_db"

# Local embedding model.
# No API key, OpenAI account, or LLM is required.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def ingest_documents(file_path: str):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    # Load document
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    # Split document into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    docs = text_splitter.split_documents(documents)

    # Local embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # Local Qdrant database
    client = QdrantClient(path=QDRANT_PATH)

    # all-MiniLM-L6-v2 produces 384-dimensional vectors
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE,
            ),
        )

    # Connect LangChain to Qdrant
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    # Store embeddings + documents
    vectorstore.add_documents(docs)

    print(
        f"Successfully ingested {len(docs)} chunks "
        f"into Qdrant at {QDRANT_PATH}"
    )


if __name__ == "__main__":
    sample_file = "sample.txt"

    if not os.path.exists(sample_file):
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(
                "LangChain is a framework for developing applications "
                "powered by language models.\n"
                "It provides standard interfaces for chains, agents, "
                "and retrieval.\n"
            )

    ingest_documents(sample_file)
