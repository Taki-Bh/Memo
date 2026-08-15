import os
import sys
import glob
import re
import warnings

SKILLS_DIR = "skills"
SKILL_INSTRUCTION="Before responding to any task, check whether it matches a skill in your index. If it does, you must load and follow that skill before proceeding."
def parse_frontmatter(md_path):
    """Extract YAML frontmatter (name, description) from a SKILL.md file
    without requiring a full YAML parser."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return None

    frontmatter_raw = match.group(1)
    data = {}
    for line in frontmatter_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip().strip('"').strip("'")

    return data


def build_skill_index(skills_dir=SKILLS_DIR):
    index = []

    if not os.path.isdir(skills_dir):
        warnings.warn(f"Skills directory '{skills_dir}' does not exist.")
        return index

    skill_md_paths = glob.glob(os.path.join(skills_dir, "*", "SKILL.md"))
    # case-insensitive fallback (e.g. skill.md, Skill.md)
    if not skill_md_paths:
        skill_md_paths = glob.glob(os.path.join(skills_dir, "*", "*[Ss][Kk][Ii][Ll][Ll].md"))

    if not skill_md_paths:
        warnings.warn(f"No SKILL.md files found under '{skills_dir}/*/'. Skill index will be empty.")
        return index

    for path in sorted(skill_md_paths):
        skill_folder = os.path.basename(os.path.dirname(path))
        frontmatter = parse_frontmatter(path)

        if not frontmatter:
            warnings.warn(f"Skipping '{path}': no valid frontmatter found.")
            continue

        name = frontmatter.get("name")
        description = frontmatter.get("description")

        if not name:
            warnings.warn(f"Skipping '{path}': missing 'name' in frontmatter.")
            continue
        if not description:
            warnings.warn(f"Skill '{name}' at '{path}' has no 'description' — it may never get triggered.")

        index.append({
            "name": name,
            "description": description or "",
            "folder": skill_folder,
            "path": path,
        })

    if not index:
        warnings.warn("Skill index is empty after parsing — check your SKILL.md files.")

    return index


def format_index_for_prompt(index):
    """Turn the index into the compact text block you inject into the system prompt."""
    if not index:
        return "No skills available."

    lines = ["Available skills:"]
    for skill in index:
        lines.append(f"- {skill['name']}: {skill['description']}")
    return "\n".join(lines)


"""if __name__ == "__main__":
    skills_dir = sys.argv[1] if len(sys.argv) > 1 else SKILLS_DIR

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        index = build_skill_index(skills_dir)
        for w in caught:
            print(f"[WARNING] {w.message}", file=sys.stderr)

    print(f"\nFound {len(index)} skill(s).\n")
    print(format_index_for_prompt(index))"""