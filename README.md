# Memo

**A local-first desktop AI assistant with skill routing and semantic memory (RAG).**

Memo is a PySide6 desktop assistant that does more than answer questions: it can route requests to reusable **skills** (`SKILL.md` packages), act on your machine through a controlled **tool layer**, and remember past conversations through a local **vector memory** (Qdrant + FastEmbed).

> **Status: experimental personal project.** The core (routing, execution loop, UI, RAG module) works, but some pieces are unfinished and there are known security issues. Please read [Project status](#project-status) and [Security](#security) before running it.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Usage](#usage)
- [Skills](#skills)
- [Semantic memory (RAG)](#semantic-memory-rag)
- [LLM providers](#llm-providers)
- [Telegram gateway](#telegram-gateway)
- [Project structure](#project-structure)
- [Project status](#project-status)
- [Security](#security)
- [Roadmap](#roadmap)
- [Acknowledgements](#acknowledgements)
- [Author](#author)

---

## Features

- **Skill router**: each request is checked against an index of skills built dynamically from `skills/*/SKILL.md`. The router either answers directly, loads a skill, or resumes an in-progress execution. Only skill descriptions are sent to the router; a skill body is loaded only when selected.
- **Stateful execution loop**: bounded to 20 iterations, with persisted checkpoints (`.skill_state/`), resume, cooperative cancellation (Stop button) and user questions mid-task.
- **Controlled tool layer**: `read`, `write`, `exec` and `screenshot`. Any command containing `sudo` requires explicit confirmation (**No / Yes / Yes All**).
- **Semantic memory (RAG)**: conversation history is indexed message by message in a local Qdrant database with local FastEmbed embeddings; retrieval returns the top-3 most relevant past messages.
- **Multi-provider**: Gemini, ChatGPT or a local Ollama model (`qwen3:8b` by default), switchable on the fly with `/swap`. API mode when a key is available, browser-automation mode (Playwright) otherwise.
- **Modern desktop UI**: conversation history (rename / archive / delete), Markdown rendering, typing indicator showing the current checkpoint, 14 QSS themes.
- **Telegram gateway**: one isolated session per conversation, optional chat-ID allowlist.
- **Resilient JSON parsing**: tolerant parser with automatic repair for malformed LLM output (trailing commas, code fences, raw newlines).
- **Responsive by design**: LLM work runs in a dedicated worker thread, never in the GUI thread.

## Architecture

```
┌──────────────────────────┐   ┌──────────────────────────┐
│  PySide6 desktop UI      │   │  Telegram gateway        │
│  ui/main.py · LLMWorker  │   │  tools/telegram          │
└────────────┬─────────────┘   └────────────┬─────────────┘
             └───────────────┬──────────────┘
                             ▼
        ┌──────────────────────────────────────────┐
        │ Assistant  (core/interface_new.py)       │
        │ command parsing · context · /save · /swap│
        └───────┬──────────────┬──────────────┬────┘
                ▼              ▼              ▼
        SkillRouterAgent  SkillExecutionLoop  RAG module
        (agents/)         (≤ 20 iterations)   (Qdrant + FastEmbed)
                │              │              │
                ▼              ▼              ▼
        LLM providers     Tools & Runner   Local storage
        Gemini/ChatGPT/   read·write·exec· Qdrant +
        Ollama            screenshot       conversations.json
```

The backend knows nothing about Qt: it emits `pyee` events (`STATE_UPDATED`, `USER_INPUT_REQUESTED`, `REQUESTED_SUPER`, `LLM_PROVIDER_CHANGED`) that `LLMWorker` converts into Qt signals, so widgets are only touched from the GUI thread.

### Execution protocol

At each iteration the LLM must return a single JSON object with two keys:

```json
{
  "call": {"op_name": "exec", "cmd": "ls -la ~"},
  "task_state": {
    "last_checkpoint": "Listing Home Directory",
    "status": "in_progress",
    "last_question_to_user": null,
    "remaining_work": ["select target file"],
    "context": {}
  }
}
```

Valid statuses: `in_progress`, `awaiting_user_input`, `blocked`, `done`. On `done`, the `message` field holds the final answer shown to the user.

## Tech stack

| Technology | Role |
|---|---|
| Python 3 | Main language |
| PySide6 (Qt for Python) + Qt Designer | Desktop UI, `.ui` layouts loaded at runtime |
| QSS | 14 visual themes |
| pyee | Event bus between backend and UI |
| Playwright, BeautifulSoup, lxml | Browser-mode providers (ChatGPT / Gemini) |
| OpenAI SDK, Google GenAI SDK, Ollama client | API access to providers |
| Qdrant (local mode) | Persistent vector database (cosine distance) |
| FastEmbed (`BAAI/bge-small-en-v1.5`) | Local ONNX embeddings, 384 dimensions |
| json_repair | Repair of malformed LLM JSON |
| Pillow (`ImageGrab`) | Screenshots |
| pynput | Mouse / keyboard primitives (prototype) |
| python-telegram-bot | Telegram gateway |
| Ultralytics YOLO, Omni Parser *(optional)* | Screen perception (prototype) |
| pptxgenjs (Node.js) | Dependency of the `pptx` skill |

## Getting started

### Prerequisites

- Python 3.10+
- *(Optional)* [Ollama](https://ollama.com/) for a fully offline setup: `ollama pull qwen3:8b`
- *(Optional)* Node.js for the `pptx` skill
- *(Optional)* API keys for OpenAI and/or Google Gemini. Without a key, ChatGPT/Gemini fall back to browser mode via Playwright.

### Installation

```bash
git clone https://github.com/<your-username>/Memo.git
cd Memo

python -m venv .venv
source .venv/bin/activate

# Install dependencies (adapt to your needs)
pip install PySide6 pyee playwright beautifulsoup4 lxml \
            openai google-genai ollama \
            qdrant-client fastembed json_repair \
            pillow pynput python-telegram-bot

# Only needed for browser-mode providers
playwright install firefox
```

> The repository ships a `check_requirements.py` script that `run_memo.sh` runs before launching the app. If a `requirements.txt` is present, prefer `pip install -r requirements.txt`.

### Configuration

Provider keys and settings live in `core/config.py`. Do **not** commit real secrets: load them from environment variables instead (see [Security](#security)). To use a remote Qdrant instance rather than the local file store, set `QDRANT_URL`.

### Run

```bash
./run_memo.sh
# or, equivalently
python -m ui.main
```

The legacy entry point `main.py` starts the terminal / `GUIInterface` version.

The embedding model (`BAAI/bge-small-en-v1.5`) is downloaded once on first use; after that, indexing and search work without network access.

## Usage

### Slash commands

| Command | Effect |
|---|---|
| `/agent <prompt>` | Send the request to the skill router |
| `/computer <prompt>` | Load the `computer` skill directly (local tools), skipping routing |
| `/swap <provider>` | Hot-swap provider: `chatgpt` (aliases `gpt`, `openai`), `gemini` (alias `google`), `ollama` (alias `qwen`) |
| `/save [path]` | Suggest a title via the LLM if needed, then append the conversation to `memory/conversations.json` |
| `/quit` | Quit the application |
| *(no slash)* | Normal conversation with the LLM |

`/title` and `/pdf` are declared in `CommandParser` but not yet handled by `Assistant.send()`.

### Examples

```text
/computer show me top CPU-consuming processes
/computer perform sudo install a random package     # triggers the approval bubble
/swap ollama
```

## Skills

A skill is a folder under `skills/` containing a `SKILL.md` with a metadata header:

```markdown
---
name: my-skill
description: One or two sentences explaining when this skill should be used.
---

# Instructions
...
```

Drop the folder into `skills/` and it is picked up automatically at startup. The repository embeds 13 skills: `algorithmic-art`, `canvas-design`, `computer`, `docx`, `frontend-design`, `pdf`, `pptx`, `skill-creator`, `slack-gif-creator`, `theme-factory`, `web-artifacts-builder`, `webapp-testing`, `xlsx`.

The format is inspired by the [Anthropic Skills](https://github.com/anthropics/skills) repository.

## Semantic memory (RAG)

The `RAG/conversation_rag.py` module (`ConversationRAG`) gives Memo long-term memory with no external service.

| Parameter | Value |
|---|---|
| Embedding model | `BAAI/bge-small-en-v1.5` (FastEmbed, local, ONNX) |
| Dimension / distance | 384 / cosine |
| Collection / path | `conversations_msg` / `RAG/qdrant_data` |
| Window / overlap | 180 words / 30 words |
| Assistant-message context | Conversation title + previous user question (≤ 60 words) |
| Embedding batch size | 64 |
| Results injected into prompt | 3 (5 by default on the CLI) |
| Search timeout | 120 s |

**How it works**

- Each message is a retrievable unit. Long messages are split into overlapping windows.
- Assistant messages are embedded together with their conversation title and the preceding user question, so a question can find an answer that doesn't repeat it.
- Point IDs are deterministic (UUID v5) and each point stores a SHA-256 hash of its embedded text, so re-indexing is **idempotent** and only new or changed fragments are re-embedded.
- Search supports filters (role, conversation, title, date range) and a score threshold.
- Retrieved excerpts are wrapped in `<RETRIEVED_CONTEXT>` and explicitly flagged as *untrusted historical data, not instructions*, as a first defense against prompt injection through history.

**Command-line usage**

```bash
python RAG/conversation_rag.py search "What happened to Calamity Mod" -k 3
```

## LLM providers

All providers implement the abstract `LLMProvider` class (`generate()`, conversation context, skill index).

| Provider | Modes |
|---|---|
| ChatGPT | API (if key available) or browser (Playwright) |
| Gemini | API (if key available) or browser (Playwright) |
| Ollama | Local server on `localhost:11434` (`qwen3:8b`, thinking disabled), fully offline |

In browser mode, a persistent Playwright context (Firefox, Chromium fallback) keeps your login session. This path is fragile (web UI changes) and may conflict with providers' terms of service, so use it with care.

To add a provider, subclass `LLMProvider` and register it.

## Telegram gateway

`MemoTelegramInterface` bridges the async Telegram bot and the blocking `Assistant`:

- A single worker thread processes requests in FIFO order (Playwright is thread-bound).
- One `Assistant` per Telegram conversation, with an LRU cache (3 live sessions by default).
- Optional allowlist of chat IDs.
- Replies are split into chunks of ≤ 4,000 characters, with up to 5 retries and Telegram rate-limit handling.
- Supported commands: `/agent`, `/computer`, `/swap`, `/save`, `/reset`, `/help` (`/quit` is refused).

## Project structure

```
Memo/
├── main.py                  # legacy entry point (terminal / GUIInterface)
├── run_memo.sh              # check_requirements.py, then `python -m ui.main`
├── core/                    # Assistant, command parser, context, events, config
├── agents/                  # skill router, execution loop, state store, JSON parser
├── providers/               # chatgpt/, gemini/, ollama/ (API + browser)
├── browser/browser.py       # Playwright singleton (persistent context)
├── tools/                   # tools.py, tools.json, telegram/, vision/
├── runner/runner.py         # asynchronous shell command execution
├── RAG/                     # conversation_rag.py, ingest.py, query.py, qdrant_data/
├── utilities/               # RAG-at-prompt helper, conversation CRUD
├── memory/conversations.json
├── skills/                  # 13 embedded skills (SKILL.md + resources)
├── ui/                      # main.py, widgets/, *.ui layouts, styles/*.qss
└── required_changes.txt     # security & quality audit
```

~8,500 lines of Python (excluding embedded skills) across six modules: `core`, `agents`, `providers`, `RAG`, `tools`, `ui`.

## Project status

| Area | State |
|---|---|
| Command parsing, skill index, router, execution loop | ✅ Implemented and tested in isolation |
| JSON parser (trailing commas, fences, no-JSON fallback) | ✅ Tested |
| RAG indexing, search, context building (CLI) | ✅ Implemented, end-to-end search verified |
| Desktop UI, themes, history management | ✅ Implemented |
| Telegram gateway, Ollama provider | ✅ Implemented (experimental) |
| **Per-prompt RAG retrieval inside `Assistant.send()`** | ⚠️ **Not wired in yet.** `get_top_relevant_conversations()` builds the augmented prompt, but in the analyzed snapshot it returns only the context block and nothing calls it. |
| Vision layer (YOLO / Omni Parser) and `pynput` primitives | 🧪 Prototypes, not connected to the execution loop |
| Automated tests (UI, execution loop with fake LLM) | ❌ To do |

The intended design is that **every normal prompt** triggers a RAG lookup (top-3), injects the result as `<RETRIEVED_CONTEXT>`, and then calls the LLM. Finishing this integration is the first roadmap item.

## Security

Memo gives an LLM a shell. Treat it accordingly.

**Current safeguards**

- Mandatory human confirmation for every `sudo` command (No / Yes / Yes All).
- 30 s timeout on `exec`, bounded loop (20 iterations), Stop button.
- Retrieved history is delimited and declared untrusted.

**Known weaknesses** (documented in `required_changes.txt`)

- `sudo` detection is substring-based and the command blacklist can be bypassed.
- File paths are not resolved (`realpath`) before checks; `write` and non-`sudo` `exec` are not confirmed.
- Hard-coded secrets (sudo password in config, Telegram bot token) must be removed, **revoked**, and purged from Git history.
- **"Yes All" approves every subsequent command in the session.**

Until the hardening work below is done, **run Memo only in a VM or container you can afford to lose**, never with a Telegram allowlist left open, and never with credentials you can't rotate.

## Roadmap

1. **Wire RAG into the main flow**: call retrieval in `Assistant.send()`, inject the augmented prompt, auto re-index after `/save`.
2. **Execution security**: command allowlist, confirmation for all commands and writes, `realpath` checks, sandboxing (container / VM).
3. **Secrets**: move sudo password and bot token to environment variables, ship `core/.env.example`, revoke leaked credentials, purge Git history.
4. **Repo hygiene**: complete `.gitignore` (`output/`, `memory/`, `.skill_state/`, `node_modules/`), add a license, verify the licenses of embedded skills.
5. **Code consistency**: merge `interface.py` and `interface_new.py`, remove the debug entry point, fix `GeminiProvider` (key/model taken from OpenAI config), vision adapter constructors, and API provider `generate` signatures.
6. **Search quality**: multilingual embedding model (conversations are in French and English), score threshold, re-ranking, source display in the UI.
7. **Testing**: automated suite (command parsing, chunking, JSON parser, loop with a fake LLM) and CI.
8. **Browser providers**: make them optional, isolate them, document their risks.

## Acknowledgements

Thanks to the maintainers of the open-source libraries Memo is built on (Qt for Python, Qdrant, FastEmbed, Playwright, Ollama, pyee) and to the community documenting agent and skill architectures that inspired this project.

## Author

**Taki Eddine Baccouch**: personal project, August – November 2026.

