from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import time

mouse = MouseController()
keyboard = KeyboardController()

def move_and_click(x: int, y: int, button: Button = Button.left):
    """Move the mouse to absolute coordinates and perform a click."""
    mouse.position = (x, y)
    time.sleep(0.05)  # Small stabilization delay
    mouse.click(button, 1)

def type_string(text: str, interval: float = 0.02):
    """Type a string naturally with an optional interval between keystrokes."""
    keyboard.type(text)
    

def press_key_combination(keys: list):
    """Press a combination of keys together (e.g., [Key.ctrl, 'c'])."""
    # Handle modifier keys and characters dynamically
    pressed = []
    try:
        for k in keys:
            # If it's a string representation of a special key, map it or use character
            key_obj = getattr(Key, k, k) if isinstance(k, str) and hasattr(Key, k) else k
            keyboard.press(key_obj)
            pressed.append(key_obj)
        time.sleep(0.05)
    finally:
        for key_obj in reversed(pressed):
            keyboard.release(key_obj)

if __name__ == "__main__":
    print("pynput primitives module loaded successfully.")