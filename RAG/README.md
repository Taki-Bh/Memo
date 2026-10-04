 # RAG Architecture Skeleton using LangChain

This folder contains a minimal, robust skeleton for a Retrieval-Augmented Generation (RAG) application built using LangChain, ChromaDB, and OpenAI.

## Structure

- `requirements.txt`: Python dependencies needed for the RAG app.
- `ingest.py`: Loads sample text documents, splits them into chunks, computes embeddings, and stores them in a local Chroma vector database.
- `query.py`: Loads the vector store, sets up a RetrievalQA chain using ChatOpenAI, and answers questions based on the ingested documents.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set your OpenAI API key in a `.env` file:
   ```env
   OPENAI_API_KEY=your-api-key-here
   ```
3. Run ingestion (creates a sample text file and ingests it):
   ```bash
   python ingest.py
   ```
4. Run a query:
   ```bash
   python query.py
   ```
