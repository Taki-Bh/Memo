---
name: skill-creator
description: Creates a new skill file for this assistant's skill system. Use this whenever the user asks to "create a skill", "make a skill for X", "add a skill", "turn this into a skill", or describes a repeatable task/workflow they want the assistant to be able to do reliably in the future. Also use when the user asks to update, fix, or improve an existing skill's triggering or instructions.
---

# Skill Creator

A meta-skill: given a natural-language prompt describing what the user wants,
this skill writes a new `SKILL.md` file and saves it into the `skills/`
folder so the assistant can discover and use it going forward.

## When to trigger

- "Create a skill that does X"
- "Make a skill for handling Y"
- "Turn what we just did into a skill"
- "Update the X skill to also handle Y"
- "Fix the Z skill, it's not triggering when it should"

Do NOT trigger this for one-off requests to just *do* X — only when the user
explicitly wants the capability saved/reusable.

## Step 1 — Capture intent

Extract or ask for (don't ask what you can infer from context):

1. **Name** — short, kebab-case identifier (e.g. `invoice-parser`,
   `weekly-report`). If updating an existing skill, reuse its exact
   existing name/folder — never rename.
2. **Trigger conditions** — what phrases, file types, or contexts should
   cause this skill to load? Be specific and generous — list variations
   of how a user might ask, not just one phrasing.
3. **What the skill should actually do** — the steps, the output format,
   any constraints or edge cases.
4. **Examples** (optional but helpful) — a sample input/output pair, if
   the user has one in mind or one appeared earlier in the conversation.

If the current conversation already contains a workflow the user wants
captured (they said "turn this into a skill"), pull the steps from what
was actually done rather than asking the user to re-describe it. Confirm
your extraction briefly before writing the file.

## Step 2 — Write the SKILL.md

Use this template:

```markdown
---
name: <kebab-case-name>
description: <One or two sentences. State BOTH what the skill does AND
  the specific contexts/phrases that should trigger it. Err on the side
  of a slightly "pushy" description — assistants tend to under-trigger
  skills, so spell out trigger phrases explicitly rather than being
  vague ("use this whenever the user mentions X, Y, or Z, even if they
  don't use the word 'skill'").>
---

# <Human-readable title>

<1-2 sentence summary of purpose>

## When to trigger
<Bullet list of concrete phrases / situations>

## Steps
<Numbered, concrete steps the assistant should follow. Prefer explicit
over clever — this is read and executed by the model at run time, so
ambiguity here becomes inconsistent behavior later.>

## Output format
<What the final output should look like — file type, structure, tone,
whatever applies>

## Edge cases
<Anything unusual to watch for: missing input, ambiguous requests,
things NOT to do>
```

Keep it under ~500 lines. If the skill is large or covers multiple
sub-cases (e.g. multiple platforms/formats), split details into a
`references/` subfolder and point to them from the main file rather than
inlining everything.

## Step 3 — Save it to the skills folder

Write the file to:

```
skills/<name>/SKILL.md
```

- If `skills/<name>/` doesn't exist, create it.
- If it already exists and this is a **new** skill with a name
  collision, ask the user whether to rename or overwrite — never
  silently overwrite.
- If this is an **update** to an existing skill, overwrite that skill's
  file in place and briefly show the user a before/after diff of what
  changed.

## Step 4 — Confirm

After writing, tell the user:
- The file path it was saved to
- The final `description` (since that's what governs future triggering
  — worth a quick sanity check from the user)
- One example prompt that should now trigger it

## Notes on writing good descriptions

The `description` field is the *only* thing that decides whether this
skill gets consulted later — the body is only read after triggering. So:

- Include concrete trigger phrases, not just abstract categories.
- Cover synonyms / rephrasings a real user might use.
- Mention relevant file types or keywords if applicable.
- When in doubt, write it slightly broader/pushier rather than narrower
  — under-triggering (skill silently not used) is a worse failure mode
  than a rare unnecessary trigger.
