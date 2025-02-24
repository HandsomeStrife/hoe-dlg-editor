# DLG File Editor

A Python-based editor for game dialog (.dlg) files that preserves binary structure and special control characters. Specifically designed to handle CP1251-encoded text with mixed Cyrillic and English content.

## Features

- Read and parse .dlg files with proper encoding detection
- Preserve binary structure and special control characters
- GUI editor for safe text modification
- Automatic backup creation
- Binary structure validation
- File comparison tool
- Support for CP1251 encoding (Cyrillic text)
- Maintain dialog tree structure with branches and choices
- Handle special control codes and game logic markers

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### GUI Editor
```bash
python src/main.py path/to/dialog.dlg --edit
```
Opens the graphical editor where you can safely modify text while preserving binary structure.

### Command Line Options
```bash
# Validate file structure and analyze binary content
python src/main.py dialog.dlg --validate

# Print dialog structure
python src/main.py dialog.dlg --print

# Compare two files
python src/main.py dialog.dlg --compare other_dialog.dlg

# Save to new file
python src/main.py dialog.dlg --output new_dialog.dlg
```

### Safety Features
- Automatic backup creation before saving changes
- Text length validation to prevent buffer overflows
- Binary structure preservation
- Special character and control code protection
- File comparison tool to verify changes

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
│   ├── main.py           # Command line interface
│   ├── dlg_handler.py    # Core file handling
│   └── gui_editor.py     # GUI implementation
├── tests/
│   └── test_dlg_handler.py
├── samples/              # Example DLG files
├── requirements.txt
└── README.md
```

## License

MIT License 