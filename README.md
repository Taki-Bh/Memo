# Memo

Memo is a desktop AI assistant that routes requests to **skills** — self-contained instruction packs (in the style of Claude's skill system) — and can act on your local machine through a small, sandboxed tool layer (read / write / execute / screenshot). It supports multiple LLM backends (Gemini, ChatGPT, local Ollama models) and ships with a PySide6 desktop UI.

> **Status: work in progress.** This is an active experiment, not a hardened tool. See [Known Issues & Security](#known-issues--security) before running it against anything you care about.

## Features

- **Skill-based agent routing** — a lightweight router LLM call reads a `SKILL.md` index (name + description frontmatter, à la Claude Skills) and decides whether to answer directly or hand off to a skill's full instructions.
- **Multi-provider LLM support** — swap between Gemini, ChatGPT, and local Ollama models at runtime with `/swap <provider>`, each with both an official-API path and a browser-automation fallback (via Playwright) for when no API key is configured.
- **Computer-use tool loop** — an execution loop gives the model `read`, `write`, `exec`, and `screenshot` tools to inspect and operate on the local filesystem, with a basic protected-path guard (`/etc`, `/boot`, `/usr`, `~/.ssh`, etc.).
- **Session/state persistence** — long-running skill executions checkpoint their state to disk (`.skill_state/`) so they can resume across turns; conversations can be saved to `memory/conversations.json`.
- **Desktop UI** — a PySide6 shell (glass/neumorphic dark theme, Qt Designer–editable `.ui` layouts) with a sidebar, chat view, and auto-resizing composer.
- **Bundled skill library** — ready-made skills for document generation (`docx`, `pptx`, `xlsx`, `pdf`), design (`canvas-design`, `theme-factory`, `frontend-design`, `algorithmic-art`), and dev tooling (`mcp-builder`, `skill-creator`, `webapp-testing`).

## Architecture

```
User input
   │
   ▼
Assistant.send()  ──►  CommandParser  (detects /agent, /swap, /save, /computer)
   │
   ├── plain message ──► LLM Provider.generate()  (JSON-formatted reply)
   │
   └── /agent, /computer ──► SkillRouterAgent
                                 │
                                 ├─ Router prompt: match request against the
                                 │  skill index → respond_directly | load_skill
                                 │  | continue_skill
                                 │
                                 └─ SkillExecutionLoop
                                       ├─ loads SKILL.md instructions
                                       ├─ calls tools via Runner (read/write/exec/screenshot)
                                       ├─ checkpoints progress to StateStore (.skill_state/)
                                       └─ returns a result / follow-up question
```

**LLM providers** (`providers/`) each implement two access paths:
- an **API path** (`*_api.py`) using the official SDK, and
- a **browser path** (`*_browser.py`, `*_page.py`, `*_parser.py`) that drives the provider's web UI with Playwright when no API key is available.

## Project Structure

```
Memo/
├── main.py                  # entry point
├── core/                    # provider abstraction, command parsing, config, context
├── agents/                  # SkillRouterAgent, execution loop, state store, prompts
├── tools/                   # read / write / exec / screenshot tool implementations
├── runner/                  # thin wrapper the execution loop calls into
├── providers/               # gemini / chatgpt / ollama (API + browser variants)
├── browser/                 # Playwright browser session manager
├── skills/                  # SKILL.md-based skill library (see below)
├── ui/                      # PySide6 desktop app (Qt Designer .ui files + widgets)
├── memory/                  # saved conversation entities (conversations.json)
└── mcp-configs/             # MCP server configuration
```

## Available Skills

| Skill | Purpose |
|---|---|
| `computer_skill` | Operate the local machine via `read` / `write` / `exec` / `screenshot` |
| `docx`, `pptx`, `xlsx`, `pdf` | Generate and edit Office/PDF documents |
| `canvas-design`, `theme-factory`, `frontend-design`, `algorithmic-art` | Visual/UI design generation |
| `web-artifacts-builder`, `webapp-testing` | Build and test small web apps |
| `mcp-builder` | Scaffold new MCP servers |
| `skill-creator` | Create and edit new skills |
| `slack-gif-creator`, `internal-comms`, `brand-guidelines`, `doc-coauthoring`, `claude-api` | Assorted content/communication helpers |

Each skill lives in `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`) that the router indexes to decide when to trigger it.

## Installation

```bash
git clone <your-repo-url>
cd Memo
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install                # needed for the browser-automation provider fallback
npm install                       # needed for pptxgenjs-based document generation
```

## Configuration

Provider credentials are expected as environment variables (see `core/.env`, which is gitignored) rather than committed to source. Before running:

1. Copy `core/.env.example` → `core/.env` (create this file if it doesn't exist) and fill in whichever provider keys you plan to use (Gemini, OpenAI).
2. Review `core/config.py` for local behavior flags (`USE_WEB_SCRAPING`, timeouts, the Ollama model tag). **Do not commit real secrets here** — see [Known Issues](#known-issues--security).

## Usage

### Desktop app

```bash
python -m ui.main
# or
./run_memo.sh
```

### Terminal

```bash
python main.py
```

Available commands from either interface:

| Command | Effect |
|---|---|
| `<message>` | Normal chat turn, answered by the current LLM provider |
| `/agent <prompt>` | Route the request through the skill router |
| `/computer <prompt>` | Force-route to the `computer_skill` for local system tasks |
| `/swap <chatgpt\|gemini\|ollama>` | Switch the active LLM provider |
| `/save [path]` | Save the current conversation to `memory/conversations.json` (or a custom path) |

## Known Issues & Security

This project isn't ready for production or public deployment as-is. Before pushing to GitHub or using it beyond local experimentation:

- **Hardcoded credential:** `core/config.py` currently contains a plaintext `SUDO_PASSWORD`. Remove it and load secrets from `core/.env` / environment variables instead — `git log` history will still retain it even if you delete it later, so consider this credential burned and rotate it.
- **`exec` tool is broad:** the `exec` tool runs arbitrary shell commands with only a substring check against the literal word `"suuudo"` (not `sudo`) as a guard, and the protected-path check in `tools.py` doesn't cover command execution at all — only `read`/`write` paths. Treat any skill or prompt that can reach this tool as having full shell access.
- **`node_modules/` appears to be tracked** — add it to `.gitignore` and run `git rm -r --cached node_modules` before your first push.
- **Stray artifacts:** a `$HOME/Desktop` directory and `__pycache__/`, `output/`, and `.skill_state/` session files are present in this snapshot — worth cleaning up or gitignoring before publishing.
- **`memory/conversations.json`** may contain real conversation history; gitignore it unless you intend to publish transcripts.
- Several modules (`main2()` debug entry point, placeholder `"xd"` signal payloads, an unused `interface.py` alongside `interface_new.py`) look like in-progress scaffolding rather than finished code paths.

## Roadmap

- [ ] Wire the UI's `MockAssistant` up to the real `Assistant` class
- [ ] Replace the plaintext credential with proper secrets management
- [ ] Tighten the `exec` tool's safety checks
- [ ] Consolidate `core/interface.py` and `core/interface_new.py`

## License

This project is licensed under the MIT License — you're free to use, copy, modify, merge, publish, and distribute this code (including for commercial purposes), provided the original copyright notice and this permission notice are included in all copies or substantial portions of the software. The software is provided "as is," without warranty of any kind, and the authors are not liable for any claim, damages, or other liability arising from its use.
