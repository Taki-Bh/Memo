"""Install Memo's dependencies if they are missing.

Run automatically by run_memo.sh before the app starts. It is fast on repeat
launches: a stamp file records what was already installed, and nothing happens
unless requirements.txt or the extras below change.

Usage:
    python check_requirements.py                 # install only what is missing
    python check_requirements.py --force         # re-check everything
    python check_requirements.py --with-prototype  # also install RAG/requirements.txt
"""
import hashlib
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAIN_REQUIREMENTS = ROOT / "requirements.txt"
PROTOTYPE_REQUIREMENTS = ROOT / "RAG" / "requirements.txt"  # LangChain / Chroma demo only
STAMP = ROOT / ".deps_stamp"

# Packages Memo imports that requirements.txt does not list.
EXTRA_REQUIREMENTS = [
    "qdrant-client>=1.9.0",    # RAG vector store (RAG/conversation_rag.py)
    "fastembed>=0.3.2",        # local embeddings (BAAI/bge-small-en-v1.5)
    "ollama",                  # Ollama provider
    "google-genai",            # Gemini API provider
    "json_repair",             # tolerant JSON parsing (agents/jsonparser.py)
    "python-telegram-bot",     # Telegram bridge (tools/telegram)
    "python-dotenv",           # .env loading
]

# Browser used by the ChatGPT/Gemini web modes (core/config.py: PREF_BROWSER).
PLAYWRIGHT_BROWSERS = ["firefox"]


def read_requirements(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            lines.append(line)
    return lines


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def is_satisfied(requirement: str) -> bool:
    """True if the requirement is installed (and its version matches, when checkable)."""
    try:
        from packaging.requirements import Requirement
    except ImportError:
        Requirement = None

    if Requirement is not None:
        try:
            req = Requirement(requirement)
        except Exception:
            return False
        if req.marker is not None and not req.marker.evaluate():
            return True  # not needed on this platform
        try:
            installed = metadata.version(req.name)
        except metadata.PackageNotFoundError:
            return False
        return not req.specifier or req.specifier.contains(installed, prereleases=True)

    # Fallback without `packaging`: check the package name only.
    name = normalize(re.split(r"[<>=!~;\[ ]", requirement, maxsplit=1)[0])
    try:
        metadata.version(name)
        return True
    except metadata.PackageNotFoundError:
        return False


def fingerprint(requirements: list[str]) -> str:
    payload = "\n".join(sorted(requirements)) + f"\npython={sys.version_info[:2]}\nbrowsers={PLAYWRIGHT_BROWSERS}"
    return hashlib.sha256(payload.encode()).hexdigest()


def pip_install(packages: list[str]) -> None:
    print(f"[memo] Installing {len(packages)} package(s)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])


def install_playwright_browsers() -> None:
    try:
        metadata.version("playwright")
    except metadata.PackageNotFoundError:
        return
    for browser in PLAYWRIGHT_BROWSERS:
        print(f"[memo] Making sure Playwright's {browser} is installed...")
        try:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", browser])
        except (subprocess.CalledProcessError, OSError) as exc:
            # Non-fatal: API and Ollama providers work without a browser.
            print(f"[memo] Warning: could not install {browser} for Playwright ({exc}).")


def check_and_install(force: bool = False, with_prototype: bool = False) -> int:
    if not MAIN_REQUIREMENTS.exists():
        print(f"[memo] {MAIN_REQUIREMENTS.name} not found next to this script.")
        return 1

    requirements = read_requirements(MAIN_REQUIREMENTS) + EXTRA_REQUIREMENTS
    if with_prototype:
        requirements += read_requirements(PROTOTYPE_REQUIREMENTS)

    stamp = fingerprint(requirements)
    if not force and STAMP.exists() and STAMP.read_text().strip() == stamp:
        return 0  # nothing changed since the last successful run

    missing = [r for r in requirements if not is_satisfied(r)]
    try:
        if missing:
            pip_install(missing)
        install_playwright_browsers()
    except subprocess.CalledProcessError as exc:
        print(f"[memo] Dependency installation failed (pip exited with {exc.returncode}).")
        return 1

    STAMP.write_text(stamp)
    print("[memo] Dependencies ready." if missing else "[memo] All dependencies already installed.")
    return 0


if __name__ == "__main__":
    sys.exit(
        check_and_install(
            force="--force" in sys.argv,
            with_prototype="--with-prototype" in sys.argv,
        )
    )