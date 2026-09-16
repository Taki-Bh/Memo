import base64
import io
from PIL import ImageGrab
from pathlib import Path 
import subprocess
from core.config import SUDO_PASSWORD

HOME = Path.home().resolve()

PROTECTED_PATHS = [
    Path("/etc").resolve(),
    Path("/boot").resolve(),
    Path("/usr").resolve(),
    Path("/bin").resolve(),
    Path("/sbin").resolve(),
    Path("/var").resolve(),
    HOME / ".ssh",
]
def is_protected(path: str) -> bool:
    try:
        target = Path(path).expanduser().resolve()

        return any(
            target == protected or protected in target.parents
            for protected in PROTECTED_PATHS
        )
    except Exception:
        return True

def read(path: str) -> str:
    """Read a file or list the contents of a directory."""
    target = Path(path)

    if not target.exists():
        return f"Path does not exist: {path}"
    try:
        text=target.read_text(encoding="utf-8")
        return text
    except Exception as e:
        return f"Error reading file: {e}"
        

   

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
        return "Using sudo cmds isn't allowed."
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
        def decode_output(value):
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value or ""

        output = (
            decode_output(e.stdout)
            + decode_output(e.stderr)
            + "[Command timed out after 30 seconds]"
        )

        final_output = f"[EXITCODE=-1]{output}"
        print(final_output)
        return final_output

    output = result.stdout or ""

    if result.stderr:
        output += result.stderr

    final_output = f"[EXITCODE={result.returncode}]{output}"
    print(final_output)

    return final_output


def screenshot() -> str:
    """Take a screenshot, save it to a file, and return it as a base64 encoded text."""
    try:
        im = ImageGrab.grab()
        im.save("screenshot.png", format="PNG")
        buffered = io.BytesIO()
        im.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        return f"Error taking screenshot: {e}"

TOOLS = {
    "read": read,
    "write": write,
    "exec": exec,
    "screenshot": screenshot,
}
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Take a screenshot and return it as a base64 encoded text.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },

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
