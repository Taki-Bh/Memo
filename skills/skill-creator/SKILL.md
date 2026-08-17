---
name: skill-creator
description: >
  Creates and validates new skill files for this assistant's skill system,
  using plain Python scripts (no external dependencies). This skill should
  be used whenever the user wants to create a new skill, update an existing
  skill, or turn a workflow just performed in conversation into a reusable
  skill — including phrases like "create a skill for X", "make a skill
  that does Y", "turn this into a skill", or "add this as a skill".
---

# Skill Creator

Scaffolds a new skill folder via `scripts/init_skill.py`, fills in the
content, then checks it with `scripts/validate_skill.py`. Deterministic
parts (folder structure, frontmatter format) are handled by the scripts;
only the actual content is written by the agent.

## When to trigger

- "Create a skill for X"
- "Make a skill that does Y"
- "Turn this into a skill" (referring to something just done in the conversation)
- "Update/fix the X skill" (X is an existing skill, not this one)

## Step 1 — Capture intent
Infer reasonable defaults from the user's request. For broad requests such as ‘create a module that does quaternion math,’ infer the name, common operations, output format, and resources without asking. Ask only when a required decision cannot reasonably be inferred.. If the user just said "turn
this into a skill," extract the steps from what was actually done in the
conversation rather than re-asking.

Otherwise gather:

1. **Name** — short, kebab-case (e.g. `invoice-parser`). If updating an
   existing skill, reuse its exact existing name — never rename.
2. **Trigger phrases** — concrete examples of how a user would ask for
   this, in their own words. Get variety, not just one canonical phrasing.
3. **What it should do** — the steps, in order.
4. **Output format** — what the final result looks like.
5. **Does it need bundled resources?**
   - `scripts/` — only if there's code that would otherwise be rewritten
     identically each time (e.g. a PDF-rotation routine)
   - `references/` — only for documentation the agent should consult
     while working (schemas, policies, API docs)
   - `assets/` — only for files used *in* the output (templates, logos,
     boilerplate)
   Most skills need none of these — don't create empty scaffolding for
   the sake of it.

## Step 2 — Scaffold it

```bash
python scripts/init_skill.py <skill-name> --path skills [--with-scripts] [--with-references] [--with-assets]
```

This creates `skills/<skill-name>/SKILL.md` pre-filled with a TODO
template, plus any requested subfolders. Use `--force` to overwrite an
existing `SKILL.md` when updating a skill.

If updating an existing skill rather than creating one, skip this step
and edit the existing `SKILL.md` directly.

## Step 3 — Fill in the content

Replace every `TODO` in the generated `SKILL.md`. Guidelines:

- **description**: The single most important field — it's the *only*
  thing that decides whether this skill gets consulted later (the body
  is only read after triggering). State both what the skill does and the
  specific contexts/phrases that should trigger it. Write in third
  person ("This skill should be used when..."). Err generous — list
  multiple phrasings, since under-triggering (skill silently ignored) is
  a worse failure than an occasional unnecessary trigger.
- **body**: imperative, verb-first instructions ("Extract the totals,
  then...") rather than second person ("You should extract..."). Keep it
  under ~5,000 words — if it's running long, move detail into
  `references/<topic>.md` and point to it from the body instead of
  inlining everything.
- Any script in `scripts/` should be plain, dependency-free Python
  (stdlib only) unless the user's environment is confirmed to have
  something else available — don't assume `uv`, `pip install`, or
  network access at skill-run time.

## Step 4 — Validate

```bash
python scripts/validate_skill.py skills/<skill-name>
```

Or validate every skill at once:

```bash
python scripts/validate_skill.py skills --all
```

This checks: frontmatter has `name` + `description`, `name` matches the
folder, no leftover `TODO`s, description isn't too short to trigger
reliably, body isn't excessively long, and any `scripts/`/`references/`/
`assets/` mentioned in the body actually exist on disk. Exits non-zero
if anything fails — fix and re-run before telling the user it's done.

## Step 5 — Confirm with the user

Report:
- The path the skill was saved to
- The final `description` (worth a quick sanity check — this is what
  governs future triggering)
- One example prompt that should now trigger it

## Updating an existing skill

- Reuse the exact folder name and `name` field — never version/rename
  (`invoice-parser`, not `invoice-parser-v2`).
- Edit `SKILL.md` directly rather than re-running `init_skill.py`
  (or use `--force` if you do re-run it, since it won't preserve
  existing content).
- Show the user a brief before/after of what changed.
- Re-run `validate_skill.py` after editing.

## Reference

`scripts/init_skill.py` and `scripts/validate_skill.py` are plain
Python 3, standard library only — no `pip install` or `uv` required.
Run them with `python <script>.py --help` for full argument lists.
