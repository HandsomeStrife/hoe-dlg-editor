import argparse
import sys
from pathlib import Path
import os
import traceback

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from dlg_handler import DlgHandler
from gui_editor import DlgGuiEditor

def main():
    parser = argparse.ArgumentParser(description='DLG File Editor')
    parser.add_argument('file', help='Path to the DLG file to edit')
    parser.add_argument('--output', '-o', help='Output file path (optional)')
    parser.add_argument('--validate', '-v', action='store_true', help='Validate file structure only')
    parser.add_argument('--print', '-p', action='store_true', help='Print dialog structure')
    parser.add_argument('--edit', '-e', action='store_true', help='Open in GUI editor')
    parser.add_argument('--compare', '-c', help='Compare with another file')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.file).exists():
        print(f"Error: File {args.file} not found")
        sys.exit(1)
    
    try:
        if args.edit:
            # Launch GUI editor
            print(f"Opening file in GUI editor: {args.file}")
            editor = DlgGuiEditor(args.file)
            editor.run()
            sys.exit(0)
        
        # Initialize handler for other operations
        handler = DlgHandler(args.file)
        
        # Read and parse file
        handler.read_file()
        
        if args.compare:
            # Compare with another file
            print(f"\nComparing {args.file} with {args.compare}...")
            differences = handler.compare_files(args.compare)
            if differences:
                print("\nDifferences found:")
                for diff in differences:
                    print(diff)
            else:
                print("\nFiles are identical.")
            sys.exit(0)
        
        if args.validate:
            # Run binary analysis
            print("\nAnalyzing file structure...")
            analysis = handler._analyze_binary()
            print("\nFile structure is valid.")
            sys.exit(0)
            
        if args.print:
            # Print the dialog structure
            print("\nDialog Structure:")
            print("================")
            print(handler._tree_to_text(handler.dialog_tree))
        
        if args.output:
            # Save to new file
            handler.save_file(args.output)
            print(f"\nSaved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 