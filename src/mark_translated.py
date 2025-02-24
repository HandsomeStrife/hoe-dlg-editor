#!/usr/bin/env python3
"""Utility to mark DLG files as translated from the command line."""

import os
import sys
from pathlib import Path
from db_handler import DbHandler

def mark_file_status(db_path: str, relative_path: str, status: str):
    """Mark a file's status in the database.
    
    status can be:
    - 'translated': File has been translated
    - 'untranslated': File needs translation
    - 'not_required': File doesn't need translation (empty/special case)
    """
    db = DbHandler(db_path)
    
    # Get all files to find the full path
    files = db.get_all_files()
    target_path = None
    
    # Normalize path separators
    relative_path = relative_path.replace('\\', '/')
    
    for file_path, rel_path, _ in files:
        if rel_path.replace('\\', '/') == relative_path:
            target_path = file_path
            break
    
    if target_path:
        # For now, we'll use the translated field, but we'll add a special note
        # in the relative_path to mark it as not required
        if status == 'not_required':
            # Add a special prefix to mark as not required
            new_rel_path = "NOT_REQUIRED:" + relative_path
            db.update_relative_path(target_path, new_rel_path)
            db.set_translated_status(target_path, True)  # Mark as translated
            print(f"Marked '{relative_path}' as not required for translation")
        else:
            # Remove the special prefix if it exists
            if db.get_relative_path(target_path).startswith("NOT_REQUIRED:"):
                db.update_relative_path(target_path, relative_path)
            db.set_translated_status(target_path, status == 'translated')
            print(f"Marked '{relative_path}' as {status}")
    else:
        print(f"Error: File '{relative_path}' not found in database")
    
    db.close()

def print_usage():
    print("Usage:")
    print("  python mark_translated.py <relative_path>       # Mark as translated")
    print("  python mark_translated.py -u <relative_path>    # Mark as untranslated")
    print("  python mark_translated.py -n <relative_path>    # Mark as not required")
    print("\nExample:")
    print('  python mark_translated.py -n "Data/ChrPreset/Pers/BC_IM_Commandant/BC_IM_Commandant_d9.dlg"')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        exit(1)
        
    db_path = os.path.join(os.path.expanduser("~"), ".dlg_editor", "dlg_files.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        exit(1)
    
    # Check for flags
    if sys.argv[1] == "-u":
        if len(sys.argv) < 3:
            print_usage()
            exit(1)
        mark_file_status(db_path, sys.argv[2], 'untranslated')
    elif sys.argv[1] == "-n":
        if len(sys.argv) < 3:
            print_usage()
            exit(1)
        mark_file_status(db_path, sys.argv[2], 'not_required')
    else:
        mark_file_status(db_path, sys.argv[1], 'translated') 