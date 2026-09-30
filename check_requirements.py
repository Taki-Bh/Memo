 import sys
import subprocess
import os

def check_and_install():
    req_path = 'requirements.txt'
    if not os.path.exists(req_path):
        return
    with open(req_path, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    missing = []
    for req in requirements:
        # Simple check using pkg_resources or importlib.metadata
        # Or just run pip install -r requirements.txt if we want to be safe, but the user asked to 'installs requirements if they do not exist'
        # Let's check using importlib.metadata
        pass
    
    # Alternatively, use pip check or simply run pip install -r requirements.txt which only installs missing/unmet requirements or we can check each package.
    # Let's do a quick check via pip
    try:
        import pkg_resources
        installed = {pkg.key for pkg in pkg_resources.working_set}
        # Parse requirements roughly
        for req in requirements:
            # extract package name before ==, >=, etc.
            name = req.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip().lower()
            if name not in installed:
                missing.append(req)
    except Exception:
        # Fallback to running pip install -r requirements.txt
        pass

    # Actually, pip install -r requirements.txt already skips already-satisfied packages unless --upgrade is specified!
    # So running python -m pip install -r requirements.txt is safe, fast, and robust.
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req_path])

if __name__ == '__main__':
    check_and_install()
