#!/usr/bin/env python3
"""
DLG Editor launcher script.
This can be run directly or compiled with PyInstaller.
"""

import os
import sys

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.main import main

if __name__ == "__main__":
    main() 