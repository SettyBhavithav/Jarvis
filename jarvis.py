"""
====================================================================
🤖 JARVIS V2: AUTONOMOUS MULTIMODAL AI AGENT OS
====================================================================
Primary Entry Point & CLI Launcher
Maintains 100% backward compatibility with 'python jarvis.py' command.
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add workspace directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import run_jarvis
from core.health_check import health_checker

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["health", "--health", "-h"]:
        health_checker.print_report()
    else:
        run_jarvis()
