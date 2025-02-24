#!/usr/bin/env python3
"""Generate a markdown checklist of all DLG files in the database."""

import os
from pathlib import Path
from db_handler import DbHandler

def generate_checklist(db_path: str, output_file: str = "checklist.md"):
    """Generate a markdown checklist of all DLG files."""
    db = DbHandler(db_path)
    
    # Get all files from database
    files = db.get_all_files()
    
    # Group files by directory
    directories = {}
    for file_path, relative_path, is_translated in files:
        # Get directory path
        dir_path = str(Path(relative_path).parent)
        if dir_path not in directories:
            directories[dir_path] = []
        
        # Add file info
        directories[dir_path].append({
            'name': Path(relative_path).name,
            'path': relative_path,
            'translated': is_translated
        })
    
    # Generate markdown content
    content = ["# DLG Files Translation Checklist\n"]
    content.append("Status of all dialog files in the game.\n")
    content.append("- [ ] Unchecked/Not translated")
    content.append("- [x] Checked/Translated\n")
    
    # Sort directories
    for dir_path in sorted(directories.keys()):
        # Add directory header
        if dir_path == '.':
            content.append("### Root")
        else:
            content.append(f"### {dir_path}")
        content.append("")
        
        # Add files in directory
        for file_info in sorted(directories[dir_path], key=lambda x: x['name']):
            check = 'x' if file_info['translated'] else ' '
            content.append(f"- [{check}] `{file_info['path']}`")
        content.append("")
    
    # Add statistics
    total_files = len(files)
    translated_files = sum(1 for _, _, is_translated in files if is_translated)
    percentage = (translated_files / total_files * 100) if total_files > 0 else 0
    
    content.append("## Statistics")
    content.append(f"- Total files: {total_files}")
    content.append(f"- Translated: {translated_files}")
    content.append(f"- Progress: {percentage:.1f}%")
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    print(f"Checklist generated in {output_file}")
    db.close()

if __name__ == "__main__":
    # Get the database path from the user's home directory
    db_path = os.path.join(os.path.expanduser("~"), ".dlg_editor", "dlg_files.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        exit(1)
        
    generate_checklist(db_path) 