from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.syntax import Syntax
from rich.console import Console
from rich import box
from rich.panel import Panel
import os
from typing import List, Optional, Dict
from dlg_handler import DlgHandler, DialogBranch, DialogChoice

class DlgEditor:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.handler = DlgHandler(filepath)
        self.handler.read_file()
        self.handler.parse_dialog()
        
        # Create buffers for editing
        self.main_buffer = Buffer()
        self.preview_text = ""  # Store preview text separately
        self.status_text = ""   # Store status text separately
        
        # Load initial content
        self.main_buffer.text = self._format_dialog_tree(self.handler.dialog_tree)
        self.update_preview()
        
        # Create key bindings
        self.kb = KeyBindings()
        self._setup_keybindings()
        
        # Setup layout
        self.layout = Layout(
            HSplit([
                # Main editor area
                VSplit([
                    Window(
                        content=BufferControl(buffer=self.main_buffer),
                        width=80,
                        height=40,
                    ),
                    # Preview area using FormattedTextControl
                    Window(
                        content=FormattedTextControl(text=lambda: self.preview_text),
                        width=80,
                        height=40,
                    ),
                ]),
                # Status bar using FormattedTextControl
                Window(
                    content=FormattedTextControl(text=lambda: self.status_text),
                    height=1,
                    align=WindowAlign.LEFT,
                    style="class:status",
                ),
            ])
        )
        
        # Setup styling
        self.style = Style([
            ('status', 'reverse'),
            ('error', '#ff0000'),
            ('success', '#00ff00'),
        ])
        
        # Create application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            style=self.style,
            mouse_support=True,
        )

    def _setup_keybindings(self):
        @self.kb.add('c-s')  # Ctrl+S to save
        def _(event):
            self.save_file()
            
        @self.kb.add('c-q')  # Ctrl+Q to quit
        def _(event):
            event.app.exit()
            
        @self.kb.add('c-r')  # Ctrl+R to refresh preview
        def _(event):
            self.update_preview()

    def _format_dialog_tree(self, branch: Optional[DialogBranch], level: int = 0) -> str:
        """Format dialog tree for editing, preserving special characters and structure."""
        if not branch:
            return ""
            
        indent = "    " * level
        lines = []
        
        # Add main text with control codes
        text_line = branch.text
        if branch.control_codes:
            text_line += " " + " ".join(branch.control_codes)
        lines.append(indent + text_line)
        
        # Add choices
        for choice in branch.choices:
            choice_text = f"{indent}> {choice.text}"
            if choice.response_codes:
                choice_text += " " + " ".join(choice.response_codes)
            lines.append(choice_text)
            
            if choice.outcome:
                outcome_text = f"{indent}  {choice.outcome}"
                if choice.outcome_codes:
                    outcome_text += " " + " ".join(choice.outcome_codes)
                lines.append(outcome_text)
        
        # Add next branch with separator
        if branch.next_branch:
            lines.append(f"{indent}|")
            lines.append(self._format_dialog_tree(branch.next_branch, level))
            
        return "\n".join(lines)

    def update_preview(self):
        """Update the preview text with syntax highlighting."""
        try:
            # Parse current content
            content = self.main_buffer.text
            # Create syntax highlighted version
            syntax = Syntax(
                content,
                "text",
                theme="monokai",
                word_wrap=True,
                highlight_lines=True
            )
            # Update preview text
            self.preview_text = str(syntax)
            self.status_text = " VALID - Press Ctrl+S to save, Ctrl+Q to quit"
        except Exception as e:
            self.status_text = f" ERROR: {str(e)}"

    def save_file(self):
        """Save the current content back to the DLG file."""
        try:
            # Parse the edited content
            self.handler.raw_content = self.main_buffer.text
            self.handler.parse_dialog()
            
            # Save to a backup file first
            backup_path = self.filepath + ".bak"
            self.handler.save_file(backup_path)
            
            # If successful, save to original file
            self.handler.save_file(self.filepath)
            self.status_text = " File saved successfully!"
        except Exception as e:
            self.status_text = f" Error saving file: {str(e)}"

    def run(self):
        """Run the editor application."""
        self.status_text = " Press Ctrl+S to save, Ctrl+Q to quit, Ctrl+R to refresh preview"
        self.app.run() 