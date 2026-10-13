"""
qdrant_rag.py - A message-level RAG store for past conversations, backed by Qdrant.

Input format (what `ingest_file` digests):
{
  "entities": [
    {
      "name": "The Calamity Mod Controversy",
      "date": "2026-09-07T19:59:15.109556",
      "messages": [
        {"role": "user", "content": "..."},
        {"role": "llm",  "content": "..."}
      ]
    }
  ]
}

Design
------
* Every MESSAGE is its own retrievable unit. A search returns the individual
  messages (user or assistant) that are relevant, never a whole conversation.
* Very long messages are split into overlapping word windows; a hit then points at
  the relevant passage and tells you which message it came from.
* Assistant messages are embedded together with the user question that preceded
  them (as context only), so "what happened to X?" finds the answer even when the
  answer never repeats the question. The returned text is still just the message.
* Point IDs are deterministic (uuid5 of conversation / message / part) and each carries
  a content hash, so re-ingesting or updating only re-embeds what changed.
* The first part of each message stores the original message, so a conversation can be
  rebuilt exactly (`get_conversation`) and any message range can be fetched
  (`get_messages`) when you do want surrounding context.

Public API (class ConversationRAG)
----------------------------------
  Insert : insert_conversation, insert_many, ingest_file, append_messages
  Fetch  : search, get_message, get_messages, get_conversation, list_conversations,
           build_context, ask
  Update : update_conversation, upsert_conversation, update_chunk_payload
  Delete : delete_conversation, delete_chunks, delete_where, clear
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from qdrant_client import QdrantClient, models

ID_NAMESPACE = uuid.NAMESPACE_URL
ROLE_ALIASES = {
    "user": "user", "human": "user",
    "assistant": "assistant", "llm": "assistant", "model": "assistant",
    "ai": "assistant", "bot": "assistant",
}


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class ConversationExists(Exception):
    pass


class ConversationNotFound(Exception):
    pass


# --------------------------------------------------------------------------- #
# Embedding backends (pluggable)
# --------------------------------------------------------------------------- #
class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedder:
    """Local, no-API-key embeddings via fastembed (ONNX). Default: bge-small (384d)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)
        self.dim = len(next(iter(self._model.embed(["dimension probe"]))))

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.embed(texts)]


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Message:
    role: str
    content: str

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        role = ROLE_ALIASES.get(str(d.get("role", "user")).lower(), "user")
        return cls(role=role, content=str(d.get("content", "")))


def _to_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _ts(dt: datetime | None) -> float:
    return dt.timestamp() if dt else 0.0


@dataclass
class Conversation:
    name: str
    messages: list[Message]
    date: datetime | None = None
    id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            key = f"{self.name}|{self.date.isoformat() if self.date else ''}"
            self.id = str(uuid.uuid5(ID_NAMESPACE, key))

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        return cls(
            name=d.get("name") or "Untitled conversation",
            date=_to_dt(d.get("date")),
            messages=[Message.from_dict(m) for m in d.get("messages", [])],
            id=str(d.get("id", "")),
            metadata=d.get("metadata") or {},
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date.isoformat() if self.date else None,
            "metadata": self.metadata,
            "messages": [asdict(m) for m in self.messages],
        }


@dataclass
class Hit:
    """One retrieved message (or the relevant passage of a long message)."""
    id: str
    score: float
    conversation_id: str
    conversation_name: str
    date: str | None
    message_index: int
    part_index: int
    role: str
    text: str


@dataclass
class _Chunk:
    id: str
    embed_text: str
    content_hash: str
    payload: dict[str, Any]


# --------------------------------------------------------------------------- #
# Chunking (one message -> one or more points)
# --------------------------------------------------------------------------- #
def _split_words(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [text]
    step = max(1, size - overlap)
    out, i = [], 0
    while True:
        out.append(" ".join(words[i : i + size]))
        if i + size >= len(words):
            break
        i += step
    return out


def chunk_conversation(
    conv: Conversation, max_words: int, overlap: int, context_question: bool = True
) -> list[_Chunk]:
    chunks: list[_Chunk] = []
    date_iso = conv.date.isoformat() if conv.date else None
    messages = [m for m in conv.messages if m.content.strip()]  # empty messages carry no signal
    prev_user = ""
    for i, m in enumerate(messages):
        for p, part in enumerate(_split_words(m.content.strip(), max_words, overlap)):
            lines = [conv.name]
            if context_question and m.role == "assistant" and prev_user:
                lines.append("Question: " + " ".join(prev_user.split()[:60]))
            lines.append(f"{m.role}: {part}")
            embed_text = "\n".join(lines)
            digest = hashlib.sha256(embed_text.encode()).hexdigest()
            payload: dict[str, Any] = {
                "conversation_id": conv.id,
                "conversation_name": conv.name,
                "date": date_iso,
                "timestamp": _ts(conv.date),
                "message_index": i,
                "part_index": p,
                "role": m.role,
                "text": part,  # only the message (or passage) itself, never the context prefix
                "metadata": conv.metadata,
                "content_hash": digest,
            }
            if p == 0:  # exact original, for lossless reconstruction
                payload["message"] = {"role": m.role, "content": m.content}
            chunks.append(
                _Chunk(
                    id=str(uuid.uuid5(ID_NAMESPACE, f"{conv.id}:{i}:{p}")),
                    embed_text=embed_text,
                    content_hash=digest,
                    payload=payload,
                )
            )
        if m.role == "user":
            prev_user = m.content
    return chunks


# --------------------------------------------------------------------------- #
# The RAG store
# --------------------------------------------------------------------------- #
class ConversationRAG:
    def __init__(
        self,
        collection: str = "conversations_msg",
        url: str | None = None,
        api_key: str | None = None,
        path: str | None = None,
        embedder: Embedder | None = None,
        max_words: int = 180,
        overlap: int = 30,
        context_question: bool = True,
        batch_size: int = 64,
    ):
        """
        Connection precedence: `url` (server / Qdrant Cloud) > `path` (local on-disk) > in-memory.
        `context_question`: embed each assistant message together with the preceding user question.
        """
        if url:
            self.client = QdrantClient(url=url, api_key=api_key)
        elif path:
            self.client = QdrantClient(path=path)
        else:
            self.client = QdrantClient(":memory:")
        self.collection = collection
        self.embedder = embedder or FastEmbedder()
        self.max_words, self.overlap = max_words, overlap
        self.context_question, self.batch_size = context_question, batch_size
        self._ensure_collection()

    # ------------------------------------------------------------------ setup
    def _ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            self.collection,
            vectors_config=models.VectorParams(size=self.embedder.dim, distance=models.Distance.COSINE),
        )
        for field_name, schema in [
            ("conversation_id", models.PayloadSchemaType.KEYWORD),
            ("conversation_name", models.PayloadSchemaType.KEYWORD),
            ("role", models.PayloadSchemaType.KEYWORD),
            ("timestamp", models.PayloadSchemaType.FLOAT),
            ("message_index", models.PayloadSchemaType.INTEGER),
            ("part_index", models.PayloadSchemaType.INTEGER),
        ]:
            self.client.create_payload_index(self.collection, field_name, schema)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _filter(
        conversation_id: str | None = None,
        name: str | None = None,
        role: str | None = None,
        date_from: datetime | str | None = None,
        date_to: datetime | str | None = None,
        extra: list[models.Condition] | None = None,
    ) -> models.Filter | None:
        must: list[models.Condition] = list(extra or [])
        if conversation_id:
            must.append(models.FieldCondition(key="conversation_id", match=models.MatchValue(value=conversation_id)))
        if name:
            must.append(models.FieldCondition(key="conversation_name", match=models.MatchValue(value=name)))
        if role:
            role = ROLE_ALIASES.get(role.lower(), role)
            must.append(models.FieldCondition(key="role", match=models.MatchValue(value=role)))
        if date_from or date_to:
            must.append(
                models.FieldCondition(
                    key="timestamp",
                    range=models.Range(
                        gte=_ts(_to_dt(date_from)) if date_from else None,
                        lte=_ts(_to_dt(date_to)) if date_to else None,
                    ),
                )
            )
        return models.Filter(must=must) if must else None

    def _scroll_all(self, flt: models.Filter | None, with_payload: Any = True, page: int = 256):
        offset = None
        while True:
            points, offset = self.client.scroll(
                self.collection, scroll_filter=flt, limit=page, offset=offset,
                with_payload=with_payload, with_vectors=False,
            )
            yield from points
            if offset is None:
                break

    def _count(self, flt: models.Filter | None) -> int:
        return self.client.count(self.collection, count_filter=flt, exact=True).count

    def _exists(self, conversation_id: str) -> bool:
        return self._count(self._filter(conversation_id=conversation_id)) > 0

    def _embed_upsert(self, chunks: list[_Chunk]) -> None:
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]
            vectors = self.embedder.embed([c.embed_text for c in batch])
            self.client.upsert(
                self.collection,
                points=[models.PointStruct(id=c.id, vector=v, payload=c.payload) for c, v in zip(batch, vectors)],
            )

    def _sync(self, conv: Conversation) -> dict[str, int]:
        """Make Qdrant match `conv`: embed only new/changed points, delete stale ones."""
        new = {c.id: c for c in chunk_conversation(conv, self.max_words, self.overlap, self.context_question)}
        existing = {
            str(p.id): (p.payload or {}).get("content_hash")
            for p in self._scroll_all(self._filter(conversation_id=conv.id), with_payload=["content_hash"])
        }
        to_write = [c for cid, c in new.items() if existing.get(cid) != c.content_hash]
        stale = [cid for cid in existing if cid not in new]
        self._embed_upsert(to_write)
        if stale:
            self.client.delete(self.collection, points_selector=models.PointIdsList(points=stale))
        # keep conversation-level fields consistent on points we did not rewrite
        self.client.set_payload(
            self.collection,
            payload={
                "conversation_name": conv.name,
                "date": conv.date.isoformat() if conv.date else None,
                "timestamp": _ts(conv.date),
                "metadata": conv.metadata,
            },
            points=self._filter(conversation_id=conv.id),
        )
        return {"written": len(to_write), "unchanged": len(new) - len(to_write), "deleted": len(stale)}

    @staticmethod
    def _coerce(conv: Conversation | dict) -> Conversation:
        return conv if isinstance(conv, Conversation) else Conversation.from_dict(conv)

    @staticmethod
    def _to_hit(p: Any, score: float = 0.0) -> Hit:
        pl = p.payload
        return Hit(
            id=str(p.id), score=score,
            conversation_id=pl["conversation_id"], conversation_name=pl["conversation_name"],
            date=pl.get("date"), message_index=pl["message_index"], part_index=pl["part_index"],
            role=pl["role"], text=pl["text"],
        )

    # ----------------------------------------------------------------- INSERT
    def insert_conversation(self, conv: Conversation | dict) -> str:
        """Insert a new conversation. Raises ConversationExists if its id is already stored."""
        conv = self._coerce(conv)
        if self._exists(conv.id):
            raise ConversationExists(conv.id)
        self._sync(conv)
        return conv.id

    def insert_many(self, convs: Iterable[Conversation | dict], on_exists: str = "skip") -> dict[str, int]:
        """on_exists: 'skip' (default) | 'replace' | 'error'."""
        stats = {"inserted": 0, "replaced": 0, "skipped": 0}
        for c in convs:
            c = self._coerce(c)
            if self._exists(c.id):
                if on_exists == "error":
                    raise ConversationExists(c.id)
                if on_exists == "skip":
                    stats["skipped"] += 1
                    continue
                self._sync(c)
                stats["replaced"] += 1
            else:
                self._sync(c)
                stats["inserted"] += 1
        return stats

    def ingest_file(self, path: str | Path, on_exists: str = "replace") -> dict[str, int]:
        """Digest JSON conversations from {"entities": [...]} or a bare list.

        The default replace policy is idempotent: unchanged chunks are not re-embedded.
        """
        source = Path(path).expanduser()
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Conversation JSON file not found: {source}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {source} at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
        entities = data.get("entities") if isinstance(data, dict) else data
        if not isinstance(entities, list):
            raise ValueError("Expected a list of conversations under 'entities' (or a top-level JSON list).")
        if not entities:
            return {"inserted": 0, "replaced": 0, "skipped": 0}
        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                raise ValueError(f"Conversation at index {index} must be a JSON object.")
            if "messages" in entity and not isinstance(entity["messages"], list):
                raise ValueError(f"Conversation at index {index} has a non-list 'messages' field.")
        if on_exists not in {"skip", "replace", "error"}:
            raise ValueError("on_exists must be one of: skip, replace, error")
        return self.insert_many(entities, on_exists=on_exists)

    def append_messages(self, conversation_id: str, messages: list[Message | dict]) -> dict[str, int]:
        """Add messages to the end of a stored conversation (only the new ones are embedded)."""
        conv = self.get_conversation(conversation_id)
        conv.messages.extend(m if isinstance(m, Message) else Message.from_dict(m) for m in messages)
        return self._sync(conv)

    # ------------------------------------------------------------------ FETCH
    def search(
        self,
        query: str,
        top_k: int = 5,
        role: str | None = None,
        conversation_id: str | None = None,
        name: str | None = None,
        date_from: datetime | str | None = None,
        date_to: datetime | str | None = None,
        score_threshold: float | None = None,
    ) -> list[Hit]:
        """Semantic search returning the most relevant individual messages (best first)."""
        vec = self.embedder.embed([query])[0]
        res = self.client.query_points(
            self.collection,
            query=vec,
            query_filter=self._filter(conversation_id, name, role, date_from, date_to),
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [self._to_hit(p, p.score) for p in res.points]

    def get_message(self, point_id: str) -> dict | None:
        """Fetch a single stored point (message/passage) by id."""
        res = self.client.retrieve(self.collection, ids=[point_id], with_payload=True)
        return {"id": str(res[0].id), **res[0].payload} if res else None

    def get_messages(self, conversation_id: str, start: int = 0, end: int | None = None) -> list[Message]:
        """Fetch messages [start, end] (inclusive indices) of a conversation. Use this to widen a hit
        to its neighbours, e.g. get_messages(h.conversation_id, h.message_index - 1, h.message_index + 1)."""
        conds = [
            models.FieldCondition(key="part_index", match=models.MatchValue(value=0)),
            models.FieldCondition(key="message_index", range=models.Range(gte=max(0, start), lte=end)),
        ]
        pts = sorted(
            self._scroll_all(self._filter(conversation_id=conversation_id, extra=conds)),
            key=lambda p: p.payload["message_index"],
        )
        return [Message(**p.payload["message"]) for p in pts]

    def get_conversation(self, conversation_id: str) -> Conversation:
        """Reconstruct a full conversation (for management, not for RAG context)."""
        flt = self._filter(
            conversation_id=conversation_id,
            extra=[models.FieldCondition(key="part_index", match=models.MatchValue(value=0))],
        )
        pts = sorted(self._scroll_all(flt), key=lambda p: p.payload["message_index"])
        if not pts:
            raise ConversationNotFound(conversation_id)
        first = pts[0].payload
        return Conversation(
            id=conversation_id,
            name=first["conversation_name"],
            date=_to_dt(first.get("date")),
            metadata=first.get("metadata") or {},
            messages=[Message(**p.payload["message"]) for p in pts],
        )

    def list_conversations(self, limit: int | None = None) -> list[dict]:
        """Lightweight summaries (id, name, date, message count), newest first."""
        flt = self._filter(extra=[models.FieldCondition(key="part_index", match=models.MatchValue(value=0))])
        summaries: dict[str, dict] = {}
        for p in self._scroll_all(flt, with_payload=["conversation_id", "conversation_name", "date"]):
            pl = p.payload
            s = summaries.setdefault(
                pl["conversation_id"],
                {"id": pl["conversation_id"], "name": pl["conversation_name"], "date": pl["date"], "messages": 0},
            )
            s["messages"] += 1
        out = sorted(summaries.values(), key=lambda s: s["date"] or "", reverse=True)
        return out[:limit] if limit else out

    def build_context(self, query: str, top_k: int = 5, **filters: Any) -> str:
        """Format only the retrieved messages, grouped by conversation, ready for a prompt."""
        grouped: dict[str, list[Hit]] = {}
        for h in self.search(query, top_k=top_k, **filters):
            grouped.setdefault(h.conversation_id, []).append(h)
        blocks = []
        for group in grouped.values():
            group.sort(key=lambda h: (h.message_index, h.part_index))
            head = f"### {group[0].conversation_name} ({group[0].date or 'undated'})"
            blocks.append(head + "\n" + "\n".join(f"[{h.role}] {h.text}" for h in group))
        return "\n\n".join(blocks)

    def ask(self, question: str, llm: Callable[[str], str], top_k: int = 5, **filters: Any) -> str:
        """Full RAG round trip. `llm` is any callable(prompt) -> str (Anthropic SDK, OpenAI, local...)."""
        context = self.build_context(question, top_k=top_k, **filters)
        prompt = (
            "Answer the question using the excerpts from past conversations below. "
            "If they do not contain the answer, say so.\n\n"
            f"<past_messages>\n{context}\n</past_messages>\n\n"
            f"Question: {question}"
        )
        return llm(prompt)

    # ----------------------------------------------------------------- UPDATE
    def upsert_conversation(self, conv: Conversation | dict) -> dict[str, int]:
        """Insert or fully replace a conversation. Only changed messages are re-embedded."""
        return self._sync(self._coerce(conv))

    def update_conversation(
        self,
        conversation_id: str,
        *,
        name: str | None = None,
        date: datetime | str | None = None,
        messages: list[Message | dict] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """Partially update a stored conversation. `messages`, when given, replaces all messages."""
        conv = self.get_conversation(conversation_id)
        if name is not None:
            conv.name = name
        if date is not None:
            conv.date = _to_dt(date)
        if metadata is not None:
            conv.metadata = metadata
        if messages is not None:
            conv.messages = [m if isinstance(m, Message) else Message.from_dict(m) for m in messages]
        return self._sync(conv)

    def update_chunk_payload(self, point_id: str, payload: dict[str, Any]) -> None:
        """Low-level: patch payload fields on one point (no re-embedding).
        A later sync of the parent conversation rewrites points whose content changed."""
        self.client.set_payload(self.collection, payload=payload, points=[point_id])

    # ----------------------------------------------------------------- DELETE
    def delete_conversation(self, conversation_id: str) -> int:
        """Delete every point of a conversation. Returns the number of points removed."""
        flt = self._filter(conversation_id=conversation_id)
        n = self._count(flt)
        if n == 0:
            raise ConversationNotFound(conversation_id)
        self.client.delete(self.collection, points_selector=models.FilterSelector(filter=flt))
        return n

    def delete_chunks(self, point_ids: list[str]) -> None:
        self.client.delete(self.collection, points_selector=models.PointIdsList(points=point_ids))

    def delete_where(
        self,
        name: str | None = None,
        role: str | None = None,
        date_from: datetime | str | None = None,
        date_to: datetime | str | None = None,
    ) -> int:
        """Bulk delete by name / role / date range (e.g. everything older than a date)."""
        flt = self._filter(name=name, role=role, date_from=date_from, date_to=date_to)
        if flt is None:
            raise ValueError("Refusing to delete without a filter; use clear() to wipe the collection.")
        n = self._count(flt)
        self.client.delete(self.collection, points_selector=models.FilterSelector(filter=flt))
        return n

    def clear(self) -> None:
        """Drop and recreate the collection."""
        self.client.delete_collection(self.collection)
        self._ensure_collection()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cli() -> None:
    ap = argparse.ArgumentParser(description="Message-level conversation RAG on Qdrant")
    ap.add_argument("--url", default=os.getenv("QDRANT_URL"), help="Qdrant URL (e.g. http://localhost:6333)")
    ap.add_argument("--api-key", default=os.getenv("QDRANT_API_KEY"))
    project_root = Path(__file__).resolve().parent.parent
    default_db = project_root / "RAG" / "qdrant_data"
    default_input = project_root / "memory" / "conversations.json"
    ap.add_argument("--path", default=os.getenv("QDRANT_PATH", str(default_db)), help="local persistent Qdrant directory (ignored when --url is set)")
    ap.add_argument("--collection", default="conversations_msg")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest", help="index a conversations JSON export")
    s.add_argument("file", nargs="?", default=str(default_input), help=f"JSON file (default: {default_input})")
    s.add_argument("--on-exists", choices=["replace", "skip", "error"], default="replace")
    s = sub.add_parser("search", help="find relevant individual messages")
    s.add_argument("query"); s.add_argument("-k", type=int, default=5)
    s.add_argument("--role", choices=["user", "assistant"])
    sub.add_parser("list")
    s = sub.add_parser("get"); s.add_argument("id")
    s = sub.add_parser("delete"); s.add_argument("id")
    args = ap.parse_args()
    if args.cmd == "search" and args.k < 1:
        ap.error("-k must be at least 1")

    rag = ConversationRAG(collection=args.collection, url=args.url, api_key=args.api_key,
                          path=None if args.url else args.path)
    try:
        if args.cmd == "ingest":
            print(f"Ingested {args.file}: {rag.ingest_file(args.file, on_exists=args.on_exists)}")
        elif args.cmd == "search":
            hits = rag.search(args.query, top_k=args.k, role=args.role)
            if not hits:
                print("No matching messages found. Ingest conversations first or try another query.")
            for h in hits:
                print(f"[{h.score:.3f}] {h.conversation_name} | msg {h.message_index} ({h.role}) id={h.id}\n  {h.text[:500]}\n")
        elif args.cmd == "list":
            conversations = rag.list_conversations()
            if not conversations:
                print("No conversations indexed yet. Run the ingest command first.")
            for c in conversations:
                print(f"{c['id']}  {c['date']}  {c['messages']:>3} msgs  {c['name']}")
        elif args.cmd == "get":
            print(json.dumps(rag.get_conversation(args.id).to_dict(), indent=2, ensure_ascii=False))
        elif args.cmd == "delete":
            print(f"deleted {rag.delete_conversation(args.id)} points")
    finally:
        rag.client.close()


if __name__ == "__main__":
    _cli()
