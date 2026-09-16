import base64
import io
from PIL import ImageGrab

path = './tools/tools.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if screenshot already added
if 'def screenshot' not in content:
    # Add imports at the top if not present
    imports = ''
    if 'import base64' not in content:
        imports += 'import base64\n'
    if 'import io' not in content:
        imports += 'import io\n'
    if 'from PIL import ImageGrab' not in content:
        imports += 'from PIL import ImageGrab\n'
    
    content = imports + content
    
    # Add screenshot function before TOOLS
    screenshot_func = '''
def screenshot() -> str:
    """Take a screenshot and return it as a base64 encoded text."""
    try:
        im = ImageGrab.grab()
        buffered = io.BytesIO()
        im.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        return f"Error taking screenshot: {e}"

'''
    content = content.replace('TOOLS = {', screenshot_func + 'TOOLS = {')
    content = content.replace('"exec": exec,', '"exec": exec,\n    "screenshot": screenshot,')
    
    def_snippet = '''    {
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
'''
    content = content.replace('TOOLS_DEFINITIONS = [', 'TOOLS_DEFINITIONS = [\n' + def_snippet)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Successfully updated tools.py')
else:
    print('Screenshot already exists in tools.py')
