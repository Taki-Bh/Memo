 # Memo

Memo is a desktop AI assistant that routes requests to skills — self-contained instruction packs inspired by Claude's skill system — and can operate on your local machine through a small, sandboxed tool layer (read, write, exec, and screenshot). It supports multiple LLM backends, including Gemini, ChatGPT, and local Ollama models, and ships with a PySide6 desktop UI.

> Status: work in progress. Memo is an active experiment rather than a hardened production tool. Review Known Issues & Security before using it with sensitive data or exposing it to untrusted prompts.

## Features

- Skill-based agent routing — a lightweight router matches requests against the SKILL.md skill index and can answer directly, load a skill, or continue an existing skill execution.
- Multi-provider LLM support — switch between Gemini, ChatGPT, and local Ollama models at runtime with /swap <provider>. Providers can use official APIs or browser automation through Playwright when configured for that path.
- Computer-use tool loop — the computer skill can inspect and operate on the local filesystem through read, write, exec, and screenshot.
- Checkpointed skill execution — long-running skill tasks can persist execution state in .skill_state/ and resume from a previous checkpoint.
- Conversation persistence — conversations can be saved to memory/conversations.json or another path.
- Desktop UI — a PySide6 application provides a dark glass/neumorphic interface with a sidebar, chat view, and auto-resizing composer. Qt Designer .ui layouts are supported.
- Bundled skill library — includes document generation, design, development, communication, and tooling skills.

## Architecture

text
User input
   │
   ▼
Assistant.send() ──► CommandParser
   │
   ├── normal message ──► LLM Provider.generate()
   │
   └── /agent or /computer ──► SkillRouterAgent
                                  │
                                  ├── matches the request against the skill index
                                  │
                                  └── SkillExecutionLoop
                                         ├── loads SKILL.md
                                         ├── calls Runner tools
                                         ├── checkpoints state in .skill_state/
                                         └── returns a result or follow-up question


### Main components

- core/ — provider abstraction, configuration, command parsing, and context handling.
- agents/ — routing, skill execution, state persistence, and prompts.
- tools/ — local read, write, exec, and screenshot implementations.
- runner/ — execution wrapper used by the skill loop.
- providers/ — Gemini, ChatGPT, and Ollama API/browser integrations.
- browser/ — Playwright browser-session management.
- skills/ — the SKILL.md-based skill library.
- ui/ — the PySide6 desktop application and Qt Designer layouts.
- memory/ — persisted conversation data.
- mcp-configs/ — MCP server configuration.

## Available Skills

| Skill | Purpose |
|---|---|
| computer_skill | Operate the local machine through read, write, exec, and screenshot |
| docx, pptx, xlsx, pdf | Generate and edit Office/PDF documents |
| canvas-design, theme-factory, frontend-design, algorithmic-art | Visual and UI design generation |
| web-artifacts-builder, webapp-testing | Build and test small web applications |
| mcp-builder | Scaffold MCP servers |
| skill-creator | Create and edit skills |
| slack-gif-creator, internal-comms, brand-guidelines, doc-coauthoring, claude-api | Communication, content, and integration helpers |

Each skill lives in skills/<name>/SKILL.md. YAML frontmatter provides the skill's name and description, which the router uses when deciding whether to load it.

## Installation

bash
git clone <your-repo-url>
cd Memo
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
playwright install                # required for browser-automation provider paths
npm install                       # required by pptxgenjs-based document generation


## Configuration

Provider credentials should be supplied through environment variables or the gitignored core/.env file rather than committed to source.

1. Copy core/.env.example to core/.env if the example exists.
2. Add only the provider credentials you intend to use, such as Gemini or OpenAI credentials.
3. Review core/config.py for local behavior flags, timeouts, and the configured Ollama model.
4. Never commit real credentials or other secrets.

See Known Issues & Security before running the project with sensitive data.

## Usage

### Desktop app

bash
python -m ui.main
# or
./run_memo.sh


### Terminal

bash
python main.py


### Commands

| Command | Effect |
|---|---|
| <message> | Normal chat turn using the active LLM provider |
| /agent <prompt> | Route a request through the skill router |
| /computer <prompt> | Force-route a request to computer_skill |
| /swap <chatgpt\|gemini\|ollama> | Switch the active LLM provider |
| /save [path] | Save the current conversation to the default or specified path |

## Skill Execution and Computer Access

When a request is routed to a skill, Memo loads that skill's instructions and executes its workflow step by step. Skills can use the Runner to perform operations on the local machine.

The computer skill follows an inspect → modify → verify workflow where practical. It is designed to preserve existing user data, use the least powerful operation necessary, and report execution failures rather than assuming an operation succeeded.

The execution state can be checkpointed so an interrupted skill can resume instead of restarting from the beginning.

## Known Issues & Security

Memo is not currently intended for production or untrusted public deployment. Important issues in the current snapshot include:

- Plaintext credential risk: core/config.py contains a plaintext SUDO_PASSWORD. Remove hardcoded credentials and use environment-based secret management. If this credential has ever been committed to Git history, treat it as exposed and rotate it rather than merely deleting the current copy.
- Broad exec capability: the exec tool can execute shell commands. Filesystem path protection for read/write does not by itself make shell execution safe. Any skill or prompt that can reach exec should be treated as having potentially broad local-system access.
- Repository hygiene: node_modules/, __pycache__/, output/, .skill_state/, and other generated artifacts should not be committed unless there is a deliberate reason to track them.
- Conversation privacy: memory/conversations.json can contain conversation history. Keep it out of version control unless those transcripts are intentionally being published.
- In-progress scaffolding: parts of the codebase, including alternate interface/debug paths and placeholder values, remain experimental and may need consolidation before a production release.

Before publishing the repository, review the full Git history for secrets, rotate any exposed credentials, and verify that generated or private data is excluded by .gitignore.

## Roadmap

- [ ] Connect the UI's MockAssistant to the real Assistant implementation.
- [ ] Replace plaintext credentials with proper secrets management.
- [ ] Tighten and test exec safety controls.
- [ ] Consolidate core/interface.py and core/interface_new.py.
- [ ] Expand automated tests around routing, skill execution, checkpoint recovery, and tool permissions.
- [ ] Improve repository hygiene and default .gitignore coverage.

## Contributing

Memo is an experimental project. When contributing, keep changes narrowly scoped, avoid committing secrets or generated state, and add verification for changes that affect skill routing, tool execution, persistence, or security boundaries.

## License

This project is licensed under the MIT License. You may use, copy, modify, publish, and distribute the software, including for commercial purposes, provided the original copyright notice and license are included in copies or substantial portions of the software.

The software is provided as is, without warranty of any kind. See the MIT License text distributed with the project for the complete terms.
