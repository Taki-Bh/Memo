 # Memo

Memo is a desktop AI assistant that routes requests to skills — self-contained instruction packs inspired by Claude's skill system — and can operate on your local machine through a small, sandboxed tool layer (read, write, exec, and screenshot). It supports multiple LLM backends, including Gemini, ChatGPT, and local Ollama models, and ships with a PySide6 desktop UI.

> Status: work in progress. Memo is an active experiment rather than a hardened production tool. Review Known Issues & Security before using it with sensitive data or exposing it to untrusted prompts.

## Features

- Skill-based agent routing — a lightweight router matches requests against the SKILL.md skill index and can answer directly, load a skill, or continue an existing skill execution.
- Multi-provider LLM support — switch between Gemini, ChatGPT, and local Ollama models at runtime. Providers can use official APIs or browser automation through Playwright when configured for that path.
- Computer-use tool loop — the computer skill can inspect and operate on the local filesystem through read, write, exec, and screenshot.
- Checkpointed skill execution — long-running skill tasks can persist execution state in .skill_state/ and resume from a previous checkpoint.
- Conversation persistence — conversations can be saved to memory/conversations.json or another path.
- Desktop UI — a PySide6 application provides a dark glass/neumorphic interface with a sidebar, chat view, and auto-resizing composer. Qt Designer .ui layouts are supported.
- Bundled skill library — includes document generation, design, development, communication, and tooling skills.

## Architecture

```text
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
```
