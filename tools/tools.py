from pathlib import Path 
import subprocess
from core.config import SUDO_PASSWORD


def read(path: str) -> str:
    """Read a file or list the contents of a directory."""
    target = Path(path)

    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    if target.is_dir():
        entries = []

        for item in sorted(target.iterdir()):
            if item.is_dir():
                entries.append(f"[DIR]  {item.name}")
            else:
                entries.append(f"[FILE] {item.name}")

        return "\n".join(entries)

    return target.read_text(encoding="utf-8")


def write(path: str, content: str) -> str:
    """Write text content to a file."""
    file_path = Path(path).expanduser()

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    return f"Successfully wrote to {path}"


def exec(command: str) -> str:
    """Execute a shell command and return its output (including errors)."""
    actual_command = command
    input_data = None
    
    if SUDO_PASSWORD and "sudo" in command:
        if "-S" not in command:
            actual_command = command.replace("sudo", "sudo -S", 1)
        input_data = f"{SUDO_PASSWORD}\n"

    try:
        result = subprocess.run(
            actual_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            input=input_data,
        )
    except subprocess.TimeoutExpired as e:
        output = ""
        if e.stdout:
            output += e.stdout
        if e.stderr:
            output += e.stderr
        output += "[Command timed out after 30 seconds]"
        final_output = f"[EXITCODE=-1]{output}"
        print(final_output)
        return final_output

    output = result.stdout
    if result.stderr:
        output += result.stderr

    final_output = f"[EXITCODE={result.returncode}]{output}"
    print(final_output)
    return final_output


TOOLS = {
    "read": read,
    "write": write,
    "exec": exec,
}
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": (
                "Read a file "
                "For files"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file or directory to read."
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write text content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the file to write."
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write to the file."
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "Execute a shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute."
                    }
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
]
