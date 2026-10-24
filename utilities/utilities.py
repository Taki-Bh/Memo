import time
from pathlib import Path
from datetime import datetime
import json


def get_sync_llm_msg(el):
    print("Waiting for LLM response to finish...")
    print(el.count())
    cache_msg = el.inner_text()
    stop_chain = 0
    msg = ""
    while stop_chain < 5:
        time.sleep(0.016)
        cache_msg = msg
        msg = el.inner_text()
        msg = msg[msg.find(":") + 1:].strip()
        print(f"\r{msg}", end="", flush=True)
        if msg == cache_msg and msg != "":
            stop_chain += 1
        else:
            stop_chain = 0
    return msg

ROOT_DIR = Path(__file__).resolve().parent
if (ROOT_DIR.parent / "memory").exists() and not (ROOT_DIR / "memory").exists():
    PROJECT_ROOT = ROOT_DIR.parent
else:
    PROJECT_ROOT = ROOT_DIR

MEMORY_DIR = PROJECT_ROOT / "memory"


def get_top_relevant_conversations(query, top_k=3):
    """Return up to top_k unique conversations ranked by semantic relevance.

    The conversation RAG index must already exist in RAG/qdrant_data.
    Each result contains id, title, date, score, and relevant_messages.
    """
    if not isinstance(query, str) or not query.strip():
        return []
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        return []

    import sys

    rag_dir = PROJECT_ROOT / "RAG"
    db_path = rag_dir / "qdrant_data"
    if not db_path.exists():
        return []

    if str(rag_dir) not in sys.path:
        sys.path.insert(0, str(rag_dir))

    try:
        from conversation_rag import ConversationRAG
    except ImportError:
        return []

    rag = ConversationRAG(path=str(db_path))
    try:
        hits = rag.search(query.strip(), top_k=max(top_k * 3, top_k))
        results = []
        by_id = {}
        for hit in hits:
            result = by_id.get(hit.conversation_id)
            if result is None:
                if len(results) >= top_k:
                    continue
                result = {
                    "id": hit.conversation_id,
                    "title": hit.conversation_name,
                    "date": hit.date,
                    "score": hit.score,
                    "relevant_messages": [],
                }
                by_id[hit.conversation_id] = result
                results.append(result)
            result["score"] = max(result["score"], hit.score)
            if not any(
                message["message_index"] == hit.message_index
                and message["text"] == hit.text
                for message in result["relevant_messages"]
            ):
                result["relevant_messages"].append({
                    "role": hit.role,
                    "text": hit.text,
                    "score": hit.score,
                    "message_index": hit.message_index,
                })
        return results
    finally:
        rag.client.close()


def get_conversations():
    conversations_list = []
    _loaded_conversations_map = {}
    now = datetime.now()
    conversations_file = MEMORY_DIR / "conversations.json"
    try:
        with open(conversations_file, "rt") as f:
            conversations = json.load(f)
            data = conversations.get("entities", [])
            for i, entity in enumerate(data):
                if entity.get("archived", False):
                    continue
                title = entity.get("name", "Untitled Conversation")
                date_str = entity.get("date", now.isoformat())
                convs = entity.get("messages", [])
                try:
                    dt = datetime.fromisoformat(date_str)
                except Exception:
                    dt = now
                delta_days = (now.date() - dt.date()).days
                if delta_days == 0:
                    group = "Today"
                elif delta_days == 1:
                    group = "Yesterday"
                elif delta_days <= 7:
                    group = "Previous 7 Days"
                else:
                    group = "Older"
                conv_id = str(i)
                _loaded_conversations_map[conv_id] = convs
                conversations_list.append({"id": conv_id, "title": title, "group": group, "icon": "💬"})
        return conversations_list, _loaded_conversations_map
    except Exception as e:
        print(f"Error loading conversation file: {e}")


def update_conversation_name(conv_id, new_name):
    conversations_file = MEMORY_DIR / "conversations.json"
    try:
        with open(conversations_file, "rt") as f:
            conversations = json.load(f)
        data = conversations.get("entities", [])
        idx = int(conv_id)
        if 0 <= idx < len(data):
            data[idx]["name"] = new_name
            conversations["entities"] = data
            with open(conversations_file, "wt") as f:
                json.dump(conversations, f, indent=4)
            return True
        else:
            print(f"Conversation ID {conv_id} not found.")
            return False
    except Exception as e:
        print(f"Error updating conversation name: {e}")
        return False


def delete_conversation(conv_id):
    conversations_file = MEMORY_DIR / "conversations.json"
    try:
        with open(conversations_file, "rt") as f:
            conversations = json.load(f)
        data = conversations.get("entities", [])
        idx = int(conv_id)
        if 0 <= idx < len(data):
            data.pop(idx)
            conversations["entities"] = data
            with open(conversations_file, "wt") as f:
                json.dump(conversations, f, indent=4)
            return True
        else:
            print(f"Conversation ID {conv_id} not found.")
            return False
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return False


def archive_conversation(conv_id):
    conversations_file = MEMORY_DIR / "conversations.json"
    try:
        with open(conversations_file, "rt") as f:
            conversations = json.load(f)
        data = conversations.get("entities", [])
        idx = int(conv_id)
        if 0 <= idx < len(data):
            data[idx]["archived"] = True
            conversations["entities"] = data
            with open(conversations_file, "wt") as f:
                json.dump(conversations, f, indent=4)
            return True
        else:
            print(f"Conversation ID {conv_id} not found.")
            return False
    except Exception as e:
        print(f"Error archiving conversation: {e}")
        return False
