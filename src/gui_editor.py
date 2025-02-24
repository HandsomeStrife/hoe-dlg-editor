import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
from tkinter.scrolledtext import ScrolledText
import re
from typing import Optional, List
from dlg_handler import DlgHandler, TextSection

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

class DlgGuiEditor:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.handler = DlgHandler(filepath)
        self.handler.read_file()
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"DLG Editor - {filepath}")
        self.root.geometry("1000x800")
        
        self._create_menu()
        self._create_layout()
        self._setup_bindings()
        
        # Load initial content
        self.section_editors: List[SectionEditor] = []
        self.load_content()
        
    def _create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
    def _create_layout(self):
        """Create the main layout"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Instructions label
        instructions = ttk.Label(
            main_frame, 
            text="Edit text sections below (Cyrillic and English). Each section must fit within its original space.\nText will highlight in red if it exceeds the maximum length. Press Ctrl+S to save.",
            wraplength=800
        )
        instructions.pack(fill=tk.X, pady=(0, 10))
        
        # Create scrollable canvas for sections
        canvas_frame = ttk.Frame(main_frame)
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
        
        # Pack scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Configure canvas scrolling
        self.canvas.bind('<Enter>', self._bound_to_mousewheel)
        self.canvas.bind('<Leave>', self._unbound_to_mousewheel)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN,
            padding=(5, 2)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def _setup_bindings(self):
        """Setup keyboard shortcuts"""
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        
    def load_content(self):
        """Create editor for each text section"""
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
                padding=(5, 5, 5, 15)  # Add some spacing between sections
            )
            editor.pack(fill=tk.X, padx=5, pady=5)
            self.section_editors.append(editor)
        
        # Show number of sections in status bar
        num_sections = len(self.handler.text_sections)
        self.status_var.set(f"Ready - {num_sections} editable text sections loaded")
            
    def save_file(self):
        """Save the edited text back to the file"""
        try:
            # Collect text from all sections
            texts = [editor.get_text() for editor in self.section_editors]
            content = "\n".join(texts)
            
            # Create backup first
            backup_path = self.filepath + ".bak"
            self.handler.save_with_updated_text(content, backup_path)
            
            # If backup succeeds, save to original file
            self.handler.save_with_updated_text(content)
            self.status_var.set("File saved successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error saving file - check section lengths")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            self.status_var.set("Error saving file")
            
    def run(self):
        """Run the GUI editor"""
        self.root.mainloop() 