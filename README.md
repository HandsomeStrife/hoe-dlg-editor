# DLG File Editor

A Python-based editor for game dialog (.dlg) files that preserves binary structure and special control characters. Specifically designed to handle CP1251-encoded text with mixed Cyrillic and English content.

## Features

- Read and parse .dlg files with proper encoding detection
- Preserve binary structure and special control characters
- Modern GUI with file browser and editor
- SQLite database for file tracking and translation status
- Automatic game folder scanning
- Track translation progress with visual indicators
- Support for CP1251 encoding (Cyrillic text)
- Maintain dialog tree structure with branches and choices
- Handle special control codes and game logic markers

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd dlg-editor
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Editor

There are several ways to run the editor:

1. Using the launcher script (recommended):
   ```bash
   python run.py
   ```

2. From the source directory:
   ```bash
   cd src
   python main.py
   ```

The editor will store its database and configuration in `~/.dlg_editor/` directory.

## Building Executable

To create a standalone executable:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build the executable:
   ```bash
   pyinstaller --name dlg_editor --windowed --onefile run.py
   ```

The executable will be created in the `dist` directory.

## Usage

### First Launch
On first launch, the editor will:
1. Create a SQLite database to track files and translation status
2. Show a setup window to select your Heart of Eternity game folder
3. Automatically scan for all .dlg files in the game directory
4. Display a progress bar during the initial scan

### Main Interface
The editor window is divided into two main sections:
- **Left Panel**: File Browser
  - Shows all .dlg files in a tree structure
  - Green text indicates translated files
  - Click any file to open it for editing
- **Right Panel**: Editor
  - Shows editable text sections
  - Validates text length against original space
  - Highlights overflow text in red

### Keyboard Shortcuts
- `Ctrl+S`: Save changes to current file
- `Ctrl+T`: Toggle translation status (marks file as green)
- `Ctrl+Q`: Quit editor

### Menu Options
- **File**
  - Save: Save current file changes
  - Mark as Translated: Toggle translation status
  - Rescan Files: Update file list from game directory
  - Exit: Close the editor

### Safety Features
- Automatic backup creation before saving changes
- Text length validation to prevent buffer overflows
- Binary structure preservation
- Special character and control code protection
- SQLite database for persistent translation tracking

## Dialog File Structure

The editor handles the following special elements:

- Branch separators (`|`)
- Choice markers (`>`)
- Line continuation (`\`)
- Voice metadata (`‡ЋЌЏ`)
- Inventory checks (`їїї`)
- Conditions (`¬?`)
- Dynamic inserts (`{D-}`)
- Reputation markers (`ъ`)
- Time restrictions (`†`)
- Coordinate triggers (`Џ`)

## Text Handling

- Supports mixed Cyrillic and English text
- Preserves CP1251 encoding
- Maintains exact byte positions
- Protects special binary sequences
- Validates text length against original space

## Database Structure

The editor uses SQLite to track:
- Game installation path
- All discovered .dlg files
- Translation status of each file
- Last modification timestamps

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
```

### Type Checking
```bash
mypy src/
```

### Project Structure
```
dlg-editor/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point and setup
│   ├── db_handler.py     # Database management
│   ├── dlg_handler.py    # DLG file handling
│   ├── gui_editor.py     # Main editor interface
│   └── setup_window.py   # First-run setup
├── tests/
│   └── test_dlg_handler.py
├── samples/              # Example DLG files
├── requirements.txt
└── README.md
```

## License

MIT License 