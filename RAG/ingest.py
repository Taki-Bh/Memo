import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

load_dotenv()

COLLECTION_NAME = "rag_collection"
QDRANT_PATH = "./qdrant_db"

def ingest_documents(file_path: str):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return
    
    loader = TextLoader(file_path)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)
    
    embeddings = OpenAIEmbeddings()
    
    client = QdrantClient(path=QDRANT_PATH)
    
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    
    vectorstore.add_documents(docs)
    print(f"Successfully ingested {len(docs)} chunks into Qdrant at {QDRANT_PATH}")

if __name__ == "__main__":
    sample_file = "sample.txt"
    if not os.path.exists(sample_file):
        with open(sample_file, "w") as f:
            f.write("LangChain is a framework for developing applications powered by language models.\nIt provides standard interfaces for chains, agents, and retrieval.\n")
    ingest_documents(sample_file)
