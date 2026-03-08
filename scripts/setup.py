#!/usr/bin/env python3
"""
Setup script for EmberHeart: Origins
Initializes directories and checks dependencies
"""
import os
import sys
from pathlib import Path


def create_directories():
    """Create necessary directories"""
    dirs = [
        "state",
        "logs",
        "characters",
        "world",
        "scripts"
    ]

    for dir_name in dirs:
        path = Path(dir_name)
        path.mkdir(exist_ok=True)
        print(f"v Created directory: {dir_name}")


def check_env_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    example_file = Path(".env.example")

    if not env_file.exists():
        if example_file.exists():
            print("! .env file not found")
            print(f"  Copy {example_file} to .env and configure it")
            return False
        else:
            print("! No .env or .env.example found")
            return False
    else:
        print("v .env file exists")
        return True


def check_ollama():
    """Check if Ollama is accessible"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("v Ollama is running")
            if models:
                print("  Available models found")
            return True
        else:
            print("! Ollama is running but returned unexpected response")
            return False
    except:
        print("x Ollama is not accessible")
        print("  Please install and start Ollama: https://ollama.ai")
        return False


def check_dependencies():
    """Check if required Python packages are installed"""
    required = [
        "discord",
        "rank_bm25",
        "yaml",
        "dotenv",
        "aiohttp"
    ]

    missing = []
    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"v {package}")
        except ImportError:
            print(f"x {package}")
            missing.append(package)

    if missing:
        print("\nInstall missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True


def main():
    print("=" * 60)
    print("EmberHeart: Origins - Setup")
    print("=" * 60)
    print()

    print("Creating directories...")
    create_directories()
    print()

    print("Checking environment configuration...")
    env_ok = check_env_file()
    print()

    print("Checking Python dependencies...")
    deps_ok = check_dependencies()
    print()

    print("Checking Ollama...")
    ollama_ok = check_ollama()
    print()

    print("=" * 60)
    if env_ok and deps_ok and ollama_ok:
        print("v Setup complete!")
        print("\nNext steps:")
        print("  1. Configure .env with your Discord bot token")
        print("  2. Run: python main.py")
    else:
        print("! Setup incomplete")
        sys.exit(1)


if __name__ == "__main__":
    main()
