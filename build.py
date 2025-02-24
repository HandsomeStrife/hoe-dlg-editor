#!/usr/bin/env python3
"""Build script for creating DLG Editor executable using PyInstaller."""

import os
import sys
import shutil
from pathlib import Path
import PyInstaller.__main__

def get_version():
    """Get version from src/__init__.py"""
    with open("src/__init__.py", "r") as f:
        for line in f.readlines():
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("'\"")
    return "0.1.0"  # Default version if not found

def cleanup():
    """Clean up build artifacts."""
    print("Cleaning up previous builds...")
    paths = ["build", "dist"]
    for path in paths:
        if os.path.exists(path):
            shutil.rmtree(path)

def copy_resources():
    """Copy necessary resource files to dist directory."""
    print("Copying resources...")
    # Add any resource files that need to be included with the executable
    # Example: shutil.copy("resources/icon.ico", "dist/")

def build_executable():
    """Build the executable using PyInstaller."""
    print("Building executable...")
    
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # PyInstaller arguments
    args = [
        "run.py",  # Entry point
        "--name=DLGEditor",
        "--windowed",  # No console window
        "--onefile",   # Single executable
        "--clean",     # Clean PyInstaller cache
        "--noconfirm", # Replace existing build without asking
        # Add icon if you have one
        # "--icon=resources/icon.ico",
        # Hidden imports
        "--hidden-import=tkinter",
        "--hidden-import=ttkthemes",
        "--hidden-import=openai",
        # Add data files
        "--add-data=src;src",  # Include source files
    ]
    
    if sys.platform.startswith('win'):
        # Windows-specific options
        args.append("--runtime-tmpdir=.")
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)

def create_release_artifacts():
    """Create release artifacts (zip file, etc)."""
    print("Creating release artifacts...")
    version = get_version()
    dist_dir = Path("dist")
    
    # Create platform-specific name
    platform = "win" if sys.platform.startswith("win") else "linux"
    release_name = f"DLGEditor-{version}-{platform}"
    
    # Create release directory
    release_dir = dist_dir / release_name
    release_dir.mkdir(exist_ok=True)
    
    # Copy executable and any other necessary files
    if sys.platform.startswith("win"):
        shutil.copy(dist_dir / "DLGEditor.exe", release_dir)
    else:
        shutil.copy(dist_dir / "DLGEditor", release_dir)
    
    # Copy README and other documentation
    shutil.copy("README.md", release_dir)
    
    # Create zip file
    shutil.make_archive(str(dist_dir / release_name), "zip", release_dir)
    
    print(f"Release artifacts created in: {dist_dir}")

def main():
    """Main build process."""
    try:
        cleanup()
        build_executable()
        copy_resources()
        create_release_artifacts()
        print("Build completed successfully!")
    except Exception as e:
        print(f"Build failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 