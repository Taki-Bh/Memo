from pathlib import Path
import subprocess


DATA_FILE = Path("data.txt")


def run_git(*args: str) -> None:
    """Run a Git command and raise an error if it fails."""
    subprocess.run(["git", *args], check=True)


def increment_value() -> None:
    """Read the integer in data.txt, increment it, and save it."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"{DATA_FILE} does not exist.")

    content = DATA_FILE.read_text(encoding="utf-8").strip()

    try:
        value = int(content)
    except ValueError as exc:
        raise ValueError(
            f"{DATA_FILE} must contain a single integer."
        ) from exc

    DATA_FILE.write_text(f"{value + 1}\n", encoding="utf-8")


def main() -> None:
    increment_value()

    run_git("add", str(DATA_FILE))
    run_git("commit", "-m", "Increment data value")
    run_git("push", "origin", "master")


if __name__ == "__main__":
    main()