# main.py

from core.interface import launch_in_terminal
from core.interface_new import start_interface
USE_NEW_INTERFACE = True
def main():
    if USE_NEW_INTERFACE:
        start_interface()
    else:
        launch_in_terminal()

if __name__ == "__main__":
    main()