import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

PERSIST_DIRECTORY = "./chroma_db"

def ingest_documents(file_path: str):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return
    
    loader = TextLoader(file_path)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)
    
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(docs, embeddings, persist_directory=PERSIST_DIRECTORY)
    print(f"Successfully ingested {len(docs)} chunks into ChromaDB at {PERSIST_DIRECTORY}")

if __name__ == "__main__":
    sample_file = "sample.txt"
    if not os.path.exists(sample_file):
        with open(sample_file, "w") as f:
            f.write("LangChain is a framework for developing applications powered by language models.\nIt provides standard interfaces for chains, agents, and retrieval.\n")
    ingest_documents(sample_file)
