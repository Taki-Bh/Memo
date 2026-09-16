from typing import Any
from tools.tools import read, write, exec,screenshot


class Runner:
    @staticmethod
    def run(command) -> Any:
       
        return exec(command)

    @staticmethod
    def read(path: str):
        return read(path)
    @staticmethod
    def write(path,text):
        
        return write(path,text)
    def screenshot():
        return screenshot()