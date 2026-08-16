import os
import sys
import glob
import re
import warnings

SKILLS_DIR = "skills"
SKILL_INSTRUCTION="""

"""
import re




def parse_frontmatter(md_path):
    """Extract YAML frontmatter and body from a SKILL.md file.

    Returns a dictionary including the parsed metadata, name, description,
    and the full body content.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return None

    frontmatter_raw = match.group(1)
    data = {}
    current_key = None
    for raw_line in frontmatter_raw.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue

        # Continuation line (indented) -> append to the previous key
        if raw_line[:1] in (" ", "\t") and current_key:
            data[current_key] = (
                data[current_key] + " " + raw_line.strip()
            ).strip()
            continue

        if ":" in raw_line:
            key, _, value = raw_line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # ">" or "|" alone means "block scalar starts on next line" -> not real content
            if value in (">", "|", ">-", "|-"):
                value = ""
            data[key] = value
            current_key = key

    # Extract body content (everything after the frontmatter block)
    body = content
    parts = content.split("---", 2)
    if len(parts) >= 3:
        body = parts[2].strip()

    # Addons to the dictionary while retaining all original metadata fields
    return {
        "metadata": data,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "body": body,
    }

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

def fetch_skill(path: str):
    """Given a path to a SKILL.md file, reads it and returns a dictionary

    containing its metadata and body content.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Skill file not found at: {path}")


    data = parse_frontmatter(path)
    print(data)

    return {
        "path": path,
        "name": data["name"] or "",
        "description": data["description"] or "",
        "metadata": data["metadata"] ,
        "body": data["body"],
    }
"""if __name__ == "__main__":
    skills_dir = sys.argv[1] if len(sys.argv) > 1 else SKILLS_DIR

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        index = build_skill_index(skills_dir)
        for w in caught:
            print(f"[WARNING] {w.message}", file=sys.stderr)

    print(f"\nFound {len(index)} skill(s).\n")
    print(format_index_for_prompt(index))"""