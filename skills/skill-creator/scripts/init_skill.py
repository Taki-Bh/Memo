#!/usr/bin/env python3
"""
init_skill.py — scaffold a new skill folder.

Usage:
    python init_skill.py <skill-name> [--path skills] [--with-scripts] [--with-references] [--with-assets]

Creates:
    <path>/<skill-name>/SKILL.md
    <path>/<skill-name>/references/   (only with --with-references)
    <path>/<skill-name>/scripts/      (only with --with-scripts)
    <path>/<skill-name>/assets/       (only with --with-assets)

No external dependencies — stdlib only.
"""

import argparse
import re
import sys
from pathlib import Path

SKILL_TEMPLATE = """---
name: {name}
description: >
  TODO: One or two sentences. State BOTH what this skill does AND the
  specific phrases/contexts that should trigger it. Be generous with
  trigger phrasing — list variations of how a user might actually ask,
  not just one canonical phrasing. Write in third person
  ("This skill should be used when...").
---

# {title}

TODO: 1-2 sentence summary of what this skill does.

## When to trigger

- TODO: phrase or context 1
- TODO: phrase or context 2

## Steps

1. TODO: first concrete step
2. TODO: next step
3. TODO: ...

## Output format

TODO: what the final output should look like (file type, structure, tone).

## Edge cases

- TODO: things to watch for or explicitly avoid
"""


def slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def title_case(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new skill folder.")
    parser.add_argument("skill_name", help="Name of the skill (will be slugified)")
    parser.add_argument("--path", default="skills", help="Directory to create the skill folder in (default: skills)")
    parser.add_argument("--with-scripts", action="store_true", help="Create a scripts/ subfolder")
    parser.add_argument("--with-references", action="store_true", help="Create a references/ subfolder")
    parser.add_argument("--with-assets", action="store_true", help="Create an assets/ subfolder")
    parser.add_argument("--force", action="store_true", help="Overwrite SKILL.md if it already exists")
    args = parser.parse_args()

    slug = slugify(args.skill_name)
    if not slug:
        print(f"error: '{args.skill_name}' produced an empty slug", file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(args.path) / slug
    skill_md = skill_dir / "SKILL.md"

    if skill_md.exists() and not args.force:
        print(f"error: {skill_md} already exists (use --force to overwrite)", file=sys.stderr)
        sys.exit(1)

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(SKILL_TEMPLATE.format(name=slug, title=title_case(slug)))
    print(f"created {skill_md}")

    for flag, sub in (
        (args.with_scripts, "scripts"),
        (args.with_references, "references"),
        (args.with_assets, "assets"),
    ):
        if flag:
            subdir = skill_dir / sub
            subdir.mkdir(exist_ok=True)
            gitkeep = subdir / ".gitkeep"
            gitkeep.touch()
            print(f"created {subdir}/")

    print(f"\nNext: fill in the TODOs in {skill_md}, then run:")
    print(f"  python validate_skill.py {skill_dir}")


if __name__ == "__main__":
    main()
