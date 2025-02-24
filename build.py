#!/usr/bin/env python3
"""Build script for creating DLG Editor executable using PyInstaller."""

import os
import sys
import shutil
from pathlib import Path
import PyInstaller.__main__
import tkinter
import site

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

def get_tkinter_path():
    """Get the tkinter installation path."""
    # Find tkinter package location
    tk_package = os.path.dirname(tkinter.__file__)
    
    # Find tcl/tk data files
    if sys.platform.startswith('win'):
        # On Windows, check common locations
        python_root = os.path.dirname(sys.executable)
        tcl_paths = [
            os.path.join(python_root, "tcl"),
            os.path.join(python_root, "Lib", "tcl"),
            os.path.join(site.getsitepackages()[0], "tcl"),
            os.path.join(site.getsitepackages()[0], "tk")
        ]
        
        for path in tcl_paths:
            if os.path.exists(path):
                return path, tk_package
    
    return None, tk_package

def build_executable():
    """Build the executable using PyInstaller."""
    print("Building executable...")
    
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Get tkinter paths
    tcl_path, tk_package = get_tkinter_path()
    
    # PyInstaller arguments
    args = [
        "run.py",  # Entry point
        "--name=DLGEditor",
        "--onefile",   # Single executable
        "--clean",     # Clean PyInstaller cache
        "--noconfirm", # Replace existing build without asking
        # Add icon if you have one
        # "--icon=resources/icon.ico",
        
        # Hidden imports for tkinter
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.font",
        "--hidden-import=tkinter.scrolledtext",
        "--hidden-import=ttkthemes",
        "--hidden-import=openai",
        
        # SQLite support
        "--hidden-import=sqlite3",
        "--hidden-import=sqlite3.dbapi2",
        
        # Add tkinter data files
        f"--add-data={tk_package};tkinter",
    ]
    
    # Add tcl/tk data files if found
    if tcl_path:
        args.append(f"--add-data={tcl_path};tcl")
    
    # Add source files
    args.append("--add-data=src;src")
    
    if sys.platform.startswith('win'):
        # Windows-specific options
        args.extend([
            "--runtime-tmpdir=.",
            # Collect all tkinter related dlls
            "--collect-all=tkinter",
            "--collect-all=_tkinter",
            "--collect-all=ttkthemes",
            # Collect SQLite DLLs
            "--collect-all=sqlite3",
            # Add Windows DLL collection
            "--collect-binaries=sqlite3",
        ])
        
        # Add SQLite DLL path if needed
        sqlite_dll = os.path.join(sys.prefix, 'DLLs', 'sqlite3.dll')
        if os.path.exists(sqlite_dll):
            args.append(f"--add-binary={sqlite_dll};.")
    
    print("Building with arguments:", args)
    
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
        create_release_artifacts()
        print("Build completed successfully!")
    except Exception as e:
        print(f"Build failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 