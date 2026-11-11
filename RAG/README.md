# RAG — conversation memory search

This directory contains two RAG examples:

- `conversation_rag.py`: message-level semantic search over `../memory/conversations.json`, using Qdrant and local FastEmbed embeddings. It does not require an OpenAI API key or a running Qdrant server.
- `ingest.py` and `query.py`: the original LangChain text-document example. Its separate collection and database are not used by the conversation tool.

## 1. Install dependencies

From the project root, create/activate your usual virtual environment, then run:

```bash
python -m pip install -r RAG/requirements.txt
```

FastEmbed downloads its embedding model on first use. Allow network access for that initial download; subsequent embedding runs use the local model. The default model is `BAAI/bge-small-en-v1.5` (384 dimensions).

## 2. Index your conversation history

From the project root (`/home/taki/Programs/Memo` in this setup):

```bash
python RAG/conversation_rag.py ingest
```

By default this reads `./memory/conversations.json` and stores the vector database in `./RAG/qdrant_data`. The input supports either an `{"entities": [...]}` JSON object or a top-level list. Existing conversation records are updated safely: unchanged chunks are not re-embedded.

You can also specify another export:

```bash
python RAG/conversation_rag.py ingest /path/to/conversations.json
```

The first run may take a while while the embedding model is downloaded and messages are indexed. Re-running ingestion synchronizes changed records.

## 3. Search the indexed messages

```bash
python RAG/conversation_rag.py search "What did I discuss about Terraria Calamity?"
python RAG/conversation_rag.py search "project setup and Python dependencies" -k 10
python RAG/conversation_rag.py search "my original question" --role user
```

Results are individual messages/passages with similarity scores, conversation names, message indexes, and point IDs. This tool retrieves relevant context; it does not generate an LLM-written answer by default.

## 4. Browse and manage records

```bash
python RAG/conversation_rag.py list
python RAG/conversation_rag.py get CONVERSATION_ID
python RAG/conversation_rag.py delete CONVERSATION_ID
```

`get` reconstructs a conversation using the ID printed by `list`. `delete` removes the indexed points for that conversation; it does not alter the source JSON file. Avoid deleting records unless intended.

## Configuration

Global options must appear before the subcommand:

```bash
python RAG/conversation_rag.py --path /path/to/vector_db search "your query"
```

- `--path`: local persistent Qdrant directory; defaults to `RAG/qdrant_data`.
- `--collection`: collection name; defaults to `conversations_msg`.
- `--url` and `--api-key`: optional remote Qdrant connection. Set `QDRANT_URL` and `QDRANT_API_KEY` environment variables instead if preferred.
- `QDRANT_PATH`: environment variable alternative to `--path`.

The vector database contains embedded conversation content. Treat it as private data and do not commit or share it unintentionally.

## Implementation notes

- User and assistant messages are indexed individually; long messages are split into overlapping word windows.
- Assistant embeddings include the preceding user question as retrieval context, while returned excerpts contain only the matching message passage.
- IDs are deterministic, and content hashes allow changed chunks to be updated without re-embedding everything.
- The Python API (`ConversationRAG`) also supports fetching conversations, filtering searches, updates, and deletion. See docstrings in `conversation_rag.py`.
