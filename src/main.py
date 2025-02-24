import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from gui_editor import DlgGuiEditor
from setup_window import SetupWindow
from db_handler import DbHandler

def main():
    # Initialize database in the user's home directory
    app_dir = os.path.join(os.path.expanduser("~"), ".dlg_editor")
    os.makedirs(app_dir, exist_ok=True)
    db_path = os.path.join(app_dir, "dlg_files.db")
    
    db = DbHandler(db_path)
    
    # Check if we need to run setup
    if not db.get_game_path():
        def on_setup_complete():
            # Launch main editor after setup
            with DlgGuiEditor(db_path) as editor:
                editor.run()
        
        # Show setup window
        setup = SetupWindow(db, on_setup_complete)
        setup.run()
    else:
        # Launch main editor directly
        with DlgGuiEditor(db_path) as editor:
            editor.run()

if __name__ == "__main__":
    main() 