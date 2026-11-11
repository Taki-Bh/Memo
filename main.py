# main.py

from core.interface import launch_in_terminal
from core.interface_new import start_interface
from core.interface_new import GUIInterface
USE_NEW_INTERFACE = True

def main():
    if USE_NEW_INTERFACE:
        start_interface()
    else:
        launch_in_terminal()
def main2():
    

    gi = GUIInterface()
    print(gi.run("hello"))
    print(gi.run("hello again"))   # does this also fail?
if __name__ == "__main__":
    main2()