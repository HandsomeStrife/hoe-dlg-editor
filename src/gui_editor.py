import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
from tkinter.scrolledtext import ScrolledText
import re
from typing import Optional, List, Dict
from pathlib import Path
from dlg_handler import DlgHandler, TextSection
from db_handler import DbHandler

class SectionEditor(ttk.Frame):
    def __init__(self, parent, section: TextSection, index: int, **kwargs):
        super().__init__(parent, **kwargs)
        self.section = section
        self.index = index
        
        # Calculate max visible characters (approximate)
        self.max_chars = len(section.text)
        
        # Create frame with border
        self.configure(relief='solid', borderwidth=1, padding=5)
        
        # Section header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            header_frame,
            text=f"Section {index + 1}",
            font=('TkDefaultFont', 10, 'bold')
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text=f"(Max length: {self.max_chars} characters)",
            font=('TkDefaultFont', 9),
            foreground='gray'
        ).pack(side=tk.RIGHT)
        
        # Editor
        self.editor = tk.Text(
            self,
            wrap=tk.WORD,
            height=max(2, min(5, self.max_chars // 40)),  # Adaptive height
            font=('Courier', 11)
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        
        # Set initial content
        self.editor.insert('1.0', section.text)
        
        # Add validation
        self.editor.bind('<KeyRelease>', self._validate_length)
        
    def _validate_length(self, event=None):
        """Validate text length and update visual feedback"""
        current_text = self.editor.get('1.0', 'end-1c')
        current_len = len(current_text.encode(self.section.encoding))
        
        if current_len > (self.section.end - self.section.start):
            self.editor.configure(background='#ffe6e6')  # Light red
        else:
            self.editor.configure(background='white')
            
    def get_text(self) -> str:
        """Get the current text content"""
        return self.editor.get('1.0', 'end-1c')

class FileList(ttk.Frame):
    def __init__(self, parent, db: DbHandler, on_select: callable, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self.on_select = on_select
        
        # Create treeview
        self.tree = ttk.Treeview(
            self,
            columns=('path',),
            displaycolumns=(),
            selectmode='browse'
        )
        self.tree.heading('#0', text='DLG Files')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        
        # Load files
        self.refresh_files()
        
    def refresh_files(self):
        """Refresh the file list from database."""
        self.tree.delete(*self.tree.get_children())
        
        # Get all files from database
        files = self.db.get_all_files()
        
        # Create directory structure
        directories: Dict[str, str] = {}
        
        for file_path, relative_path, is_translated in files:
            # Split path into parts
            parts = Path(relative_path).parts
            
            # Create parent directories if needed
            current_path = ""
            for i, part in enumerate(parts[:-1]):
                parent_path = current_path
                current_path = str(Path(current_path) / part)
                
                if current_path not in directories:
                    directories[current_path] = self.tree.insert(
                        directories.get(parent_path, ''),
                        'end',
                        text=part,
                        values=()
                    )
            
            # Add file
            parent = directories.get(str(Path(relative_path).parent), '')
            item_id = self.tree.insert(
                parent,
                'end',
                text=parts[-1],
                values=(file_path,)
            )
            
            # Set color if translated
            if is_translated:
                self.tree.tag_configure('translated', foreground='green')
                self.tree.item(item_id, tags=('translated',))
                
    def _on_select(self, event):
        """Handle file selection."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            if item['values']:  # Only if it's a file (has a path)
                self.on_select(item['values'][0])

class DlgGuiEditor:
    def __init__(self, db_path: str = "dlg_files.db"):
        self.db = DbHandler(db_path)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("DLG Editor")
        self.root.geometry("1200x800")
        
        self._create_menu()
        self._create_layout()
        self._setup_bindings()
        
        # Initialize variables
        self.current_file = None
        self.handler = None
        self.section_editors = []
        
    def _create_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Mark as Translated", command=self.mark_translated, accelerator="Ctrl+T")
        file_menu.add_separator()
        file_menu.add_command(label="Rescan Files", command=self.rescan_files)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
    def _create_layout(self):
        """Create the main layout."""
        # Main paned window
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # File list frame
        file_frame = ttk.Frame(paned)
        self.file_list = FileList(
            file_frame,
            self.db,
            self.load_file
        )
        self.file_list.pack(fill=tk.BOTH, expand=True)
        paned.add(file_frame, weight=1)
        
        # Editor frame
        editor_frame = ttk.Frame(paned)
        paned.add(editor_frame, weight=3)
        
        # Instructions label
        self.instructions = ttk.Label(
            editor_frame,
            text="Select a file to edit from the list on the left.\nPress Ctrl+S to save changes, Ctrl+T to mark as translated.",
            wraplength=800
        )
        self.instructions.pack(fill=tk.X, pady=(0, 10))
        
        # Create scrollable canvas for sections
        canvas_frame = ttk.Frame(editor_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            padding=(5, 2)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def _setup_bindings(self):
        """Setup keyboard shortcuts."""
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-t>", lambda e: self.mark_translated())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        
        # Configure canvas scrolling
        self.canvas.bind('<Enter>', self._bound_to_mousewheel)
        self.canvas.bind('<Leave>', self._unbound_to_mousewheel)
        
    def load_file(self, file_path: str):
        """Load a file for editing."""
        try:
            self.current_file = file_path
            self.handler = DlgHandler(file_path)
            self.handler.read_file()
            
            # Clear existing editors
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            self.section_editors.clear()
            
            # Create new editors
            for i, section in enumerate(self.handler.text_sections):
                editor = SectionEditor(
                    self.scrollable_frame,
                    section,
                    i,
                    padding=(5, 5, 5, 15)
                )
                editor.pack(fill=tk.X, padx=5, pady=5)
                self.section_editors.append(editor)
            
            # Update status
            is_translated = self.db.is_file_translated(file_path)
            status = "Translated" if is_translated else "Not translated"
            self.status_var.set(f"Loaded: {Path(file_path).name} ({status})")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            
    def save_file(self):
        """Save the current file."""
        if not self.current_file or not self.handler:
            return
            
        try:
            # Collect text from all sections
            texts = [editor.get_text() for editor in self.section_editors]
            content = "\n".join(texts)
            
            # Create backup first
            backup_path = self.current_file + ".bak"
            self.handler.save_with_updated_text(content, backup_path)
            
            # If backup succeeds, save to original file
            self.handler.save_with_updated_text(content)
            self.status_var.set("File saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            
    def mark_translated(self):
        """Mark current file as translated."""
        if not self.current_file:
            return
            
        is_translated = self.db.is_file_translated(self.current_file)
        self.db.set_translated_status(self.current_file, not is_translated)
        self.file_list.refresh_files()
        
        status = "translated" if not is_translated else "not translated"
        self.status_var.set(f"Marked as {status}")
        
    def rescan_files(self):
        """Rescan game directory for DLG files."""
        game_path = self.db.get_game_path()
        if not game_path or not os.path.exists(game_path):
            messagebox.showerror(
                "Error",
                "Game path not found. Please restart the application to set it."
            )
            return
            
        # Clear and rescan
        self.db.clear_all_files()
        for file_path in Path(game_path).rglob("*.dlg"):
            relative_path = str(file_path.relative_to(game_path))
            self.db.add_dlg_file(str(file_path), relative_path)
            
        self.file_list.refresh_files()
        self.status_var.set("File list updated")
        
    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def run(self):
        """Run the editor application."""
        self.status_var.set("Ready - Select a file to edit")
        self.root.mainloop()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close() 