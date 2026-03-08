#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

def print_box(text, color="\033[0m"):
    width = len(text) + 4
    print(f"{color}+" + "-" * (width - 2) + "+")
    print(f"| {text} |")
    print("+" + "-" * (width - 2) + "+\033[0m")

def main():
    print_box("EmberHeart Environment Doctor", "\033[1;34m")
    
    project_root = Path(__file__).parent.parent
    venv_path = project_root / "venv"
    venv_python = venv_path / "bin" / "python"
    
    current_python = sys.executable
    is_venv = "venv" in current_python or "virtualenv" in current_python
    
    print(f"\nCurrent Python: {current_python}")
    
    # 1. Check if we are in the venv
    if is_venv:
        print("\033[1;32m[v] You are running inside a virtual environment.\033[0m")
    else:
        print("\033[1;33m[!] You are NOT running inside the project's virtual environment.\033[0m")
        print(f"    Expected interpreter: {venv_python}")
    
    # 2. Check discord.py
    try:
        import discord
        from discord.ext import commands
        print(f"\033[1;32m[v] discord.py {discord.__version__} is available.\033[0m")
    except ImportError:
        print("\033[1;31m[x] discord.ext is MISSING in this environment.\033[0m")
        if not is_venv:
            print("\033[1;36m    FIX: This is likely because you haven't activated the venv.\033[0m")
    
    # 3. Provide Instructions
    print("\n" + "="*30)
    print("HOW TO FIX THIS:")
    print("="*30)
    
    if not is_venv:
        print("\n\033[1mOption A: Terminal (zsh/bash)\033[0m")
        print("Run this command to activate the environment:")
        print(f"  source {venv_path}/bin/activate")
        
        print("\n\033[1mOption B: VS Code\033[0m")
        print("1. Press Command+Shift+P")
        print("2. Type 'Python: Select Interpreter'")
        print(f"3. Select the one labeled './venv/bin/python'")
        
        print("\n\033[1mOption C: PyCharm\033[0m")
        print("1. Go to Settings > Project > Python Interpreter")
        print(f"2. Add/Select the interpreter at: {venv_python}")
    
    print("\nIf you've done the above and it still fails, run:")
    print(f"  source venv/bin/activate && pip install -r requirements.txt")
    print("="*30)

if __name__ == "__main__":
    main()
