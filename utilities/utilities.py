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
