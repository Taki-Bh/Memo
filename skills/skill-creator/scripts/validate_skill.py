#!/usr/bin/env python3
"""
validate_skill.py — sanity-check a skill folder's structure and SKILL.md.

Usage:
    python validate_skill.py <skill-path>          # validate one skill
    python validate_skill.py <skills-dir> --all     # validate every skill in a directory

Checks:
    - SKILL.md exists
    - YAML frontmatter present with `name` and `description` fields
    - `name` matches the folder name (slugified)
    - description is non-empty and not still a TODO placeholder
    - body doesn't contain leftover "TODO" markers
    - body length is within a sane range (warns if very long)
    - referenced {base_dir} paths (scripts/, references/, assets/) exist if mentioned

No external dependencies — stdlib only. Exits non-zero if any skill fails.
"""

import argparse
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
FIELD_RE = re.compile(r"^([a-zA-Z_]+):\s*(.*)$")

MAX_BODY_WORDS = 5000  # soft ceiling in line with progressive-disclosure guidance


def slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def parse_frontmatter(text: str):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, None
    raw_fm, body = m.group(1), m.group(2)
    fields = {}
    current_key = None
    for line in raw_fm.splitlines():
        fm = FIELD_RE.match(line)
        if fm:
            current_key = fm.group(1)
            fields[current_key] = fm.group(2).strip()
        elif current_key and line.startswith((" ", "\t")):
            # continuation of a multi-line (block scalar) value
            fields[current_key] = (fields[current_key] + " " + line.strip()).strip()
    return fields, body


def validate_one(skill_dir: Path) -> list:
    errors = []
    warnings = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"missing SKILL.md in {skill_dir}"], []

    text = skill_md.read_text()
    fields, body = parse_frontmatter(text)

    if fields is None:
        return [f"{skill_md}: missing or malformed YAML frontmatter (need --- ... --- block)"], []

    name = fields.get("name", "")
    description = fields.get("description", "")

    if not name:
        errors.append(f"{skill_md}: frontmatter missing `name`")
    else:
        expected = slugify(skill_dir.name)
        if slugify(name) != expected:
            errors.append(f"{skill_md}: name '{name}' does not match folder '{skill_dir.name}'")

    if not description:
        errors.append(f"{skill_md}: frontmatter missing `description`")
    elif "TODO" in description:
        errors.append(f"{skill_md}: description still contains a TODO placeholder")
    elif len(description.split()) < 6:
        warnings.append(f"{skill_md}: description is very short — likely won't trigger reliably")

    if body is not None:
        if "TODO" in body:
            errors.append(f"{skill_md}: body still contains TODO placeholder(s)")
        word_count = len(body.split())
        if word_count > MAX_BODY_WORDS:
            warnings.append(
                f"{skill_md}: body is {word_count} words (> {MAX_BODY_WORDS}) — "
                f"consider moving detail into references/"
            )

        # check any {base_dir}/scripts|references|assets mentions resolve to real dirs
        for sub in ("scripts", "references", "assets"):
            if f"{sub}/" in body and not (skill_dir / sub).exists():
                warnings.append(f"{skill_md}: mentions {sub}/ but {skill_dir / sub} does not exist")

    for w in warnings:
        print(f"  warning: {w}")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate skill folder structure.")
    parser.add_argument("path", help="Path to a single skill folder, or a directory of skills with --all")
    parser.add_argument("--all", action="store_true", help="Treat <path> as a directory containing multiple skill folders")
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        sys.exit(1)

    targets = [d for d in sorted(root.iterdir()) if d.is_dir()] if args.all else [root]

    any_errors = False
    for skill_dir in targets:
        print(f"validating {skill_dir}")
        errors, _ = validate_one(skill_dir)
        if errors:
            any_errors = True
            for e in errors:
                print(f"  ERROR: {e}")
        else:
            print("  ok")

    sys.exit(1 if any_errors else 0)


if __name__ == "__main__":
    main()
