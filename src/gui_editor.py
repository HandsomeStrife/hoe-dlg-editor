import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
from tkinter.scrolledtext import ScrolledText
import re
import os
from typing import Optional, List, Dict
from pathlib import Path
from dlg_handler import DlgHandler, TextSection
from db_handler import DbHandler
from ai_translator import AITranslator
from api_key_dialog import APIKeyDialog

class BatchTranslationDialog:
    def __init__(self, parent, sections, translations):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Translation Results")
        self.dialog.geometry("1000x600")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add instructions
        ttk.Label(
            main_frame,
            text="Review the translations below. You can copy and paste them into the main editor.",
            wraplength=900
        ).pack(pady=(0, 10))
        
        # Create scrollable text area
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        self.text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=('Courier', 11),
            yscrollcommand=scrollbar.set
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text.yview)
        
        # Add the content
        for i, (section, translation) in enumerate(zip(sections, translations)):
            # Add section header
            self.text.insert('end', f"\n=== Section {i + 1} ===\n", 'header')
            # Add original text
            self.text.insert('end', "Original:\n", 'label')
            self.text.insert('end', f"{section.get_text()}\n", 'original')
            # Add translation
            self.text.insert('end', "Translation:\n", 'label')
            self.text.insert('end', f"{translation}\n", 'translation')
            
            # Add length info
            orig_len = len(section.get_text().encode(section.section.encoding))
            trans_len = len(translation.encode(section.section.encoding))
            max_len = section.max_chars
            self.text.insert('end', f"Length: {trans_len}/{max_len} bytes ", 'info')
            
            if trans_len > max_len + 10:
                self.text.insert('end', "(TOO LONG!)\n", 'error')
            elif trans_len > max_len:
                self.text.insert('end', "(Slight overflow)\n", 'warning')
            else:
                self.text.insert('end', "(OK)\n", 'ok')
            
        # Configure tags
        self.text.tag_configure('header', font=('Courier', 11, 'bold'))
        self.text.tag_configure('label', font=('Courier', 11, 'italic'))
        self.text.tag_configure('original', foreground='gray')
        self.text.tag_configure('translation', foreground='blue')
        self.text.tag_configure('info', foreground='gray')
        self.text.tag_configure('error', foreground='red')
        self.text.tag_configure('warning', foreground='orange')
        self.text.tag_configure('ok', foreground='green')
        
        # Make text read-only
        self.text.configure(state='disabled')
        
        # Add buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            btn_frame,
            text="Copy All",
            command=self._copy_all
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Close",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
    def _copy_all(self):
        """Copy all text to clipboard."""
        self.text.configure(state='normal')
        self.text.tag_add('sel', '1.0', 'end')
        self.text.event_generate('<<Copy>>')
        self.text.tag_remove('sel', '1.0', 'end')
        self.text.configure(state='disabled')

class SectionEditor(ttk.Frame):
    def __init__(self, parent, section: TextSection, index: int, translator: AITranslator = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.section = section
        self.index = index
        self.translator = translator
        self.is_selected = tk.BooleanVar(value=False)
        
        # Calculate max available characters based on total available space
        self.max_chars = section.end - section.start  # This now includes trailing null bytes
        
        # Create frame with border
        self.configure(relief='solid', borderwidth=1, padding=5)
        
        # Section header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Left side of header
        header_left = ttk.Frame(header_frame)
        header_left.pack(side=tk.LEFT)
        
        # Add checkbox for selection
        self.select_cb = ttk.Checkbutton(
            header_left,
            variable=self.is_selected,
            text=f"Section {index + 1}",
            style='Bold.TCheckbutton'
        )
        self.select_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add individual translate button
        if translator and translator.has_valid_key():
            self.translate_btn = ttk.Button(
                header_left,
                text="Translate",
                command=self._translate_section,
                width=10
            )
            self.translate_btn.pack(side=tk.LEFT)
        
        # Show both current and maximum available length
        current_len = len(section.text.encode(section.encoding))
        ttk.Label(
            header_frame,
            text=f"(Current: {current_len} bytes, Max available: {self.max_chars} bytes)",
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
        
        # Allow slight overflow (10 characters)
        allowed_overflow = min(10, self.max_chars * 0.1)  # 10% or 10 chars, whichever is smaller
        
        if current_len > self.max_chars + allowed_overflow:
            self.editor.configure(background='#ffe6e6')  # Light red
            # Update parent window's header to show overflow
            header_frame = self.winfo_children()[0]  # Get header frame
            for child in header_frame.winfo_children():
                if isinstance(child, ttk.Label) and child.cget('foreground') == 'gray':
                    child.configure(
                        text=f"(Current: {current_len} bytes, Max available: {self.max_chars} bytes) - OVERFLOW",
                        foreground='red'
                    )
        elif current_len > self.max_chars:
            self.editor.configure(background='#fff3e6')  # Light orange for slight overflow
            header_frame = self.winfo_children()[0]
            for child in header_frame.winfo_children():
                if isinstance(child, ttk.Label) and (child.cget('foreground') == 'gray' or child.cget('foreground') == 'red'):
                    child.configure(
                        text=f"(Current: {current_len} bytes, Max available: {self.max_chars} bytes) - SLIGHT OVERFLOW",
                        foreground='orange'
                    )
        else:
            self.editor.configure(background='white')
            header_frame = self.winfo_children()[0]
            for child in header_frame.winfo_children():
                if isinstance(child, ttk.Label) and (child.cget('foreground') == 'gray' or child.cget('foreground') == 'red' or child.cget('foreground') == 'orange'):
                    child.configure(
                        text=f"(Current: {current_len} bytes, Max available: {self.max_chars} bytes)",
                        foreground='gray'
                    )
            
    def get_text(self) -> str:
        """Get the current text content"""
        return self.editor.get('1.0', 'end-1c')
        
    def set_text(self, text: str):
        """Set the text content"""
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', text)
        self._validate_length()

    def _translate_section(self):
        """Translate the current section using OpenAI."""
        if not self.translator:
            return
            
        try:
            current_text = self.editor.get('1.0', 'end-1c')
            
            # Get all text sections from parent window for context
            context = []
            parent_frame = self.winfo_parent()
            if parent_frame:
                parent = self.nametowidget(parent_frame)
                for widget in parent.winfo_children():
                    if isinstance(widget, SectionEditor):
                        section_text = widget.get_text()
                        context.append(section_text)
            
            translation = self.translator.translate_text(
                current_text,
                self.max_chars,
                self.section.encoding,
                context=context
            )
            
            # Replace current text with translation
            self.editor.delete('1.0', 'end')
            self.editor.insert('1.0', translation)
            
            # Validate length after translation
            self._validate_length()
            
        except Exception as e:
            messagebox.showerror(
                "Translation Error",
                str(e)
            )

class FileList(ttk.Frame):
    def __init__(self, parent, db: DbHandler, on_select: callable, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self.on_select = on_select
        self.open_states = {}
        
        # Create treeview
        self.tree = ttk.Treeview(self, selectmode='browse')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Configure tags for different file states
        self.tree.tag_configure('translated', foreground='green')
        self.tree.tag_configure('not_required', font=('TkDefaultFont', 9, 'overstrike'), foreground='gray')
        
        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        
        # Load files
        self.refresh_files()
        
    def _store_open_states(self):
        """Store which nodes are currently open."""
        self.open_states = {
            self.tree.item(item)["text"]: self.tree.item(item)["open"]
            for item in self.tree.get_children("")
        }
        
    def _restore_open_states(self):
        """Restore previously open nodes."""
        for item in self.tree.get_children(""):
            if item in self.open_states:
                self.tree.item(item, open=self.open_states[item])
        
    def refresh_files(self, maintain_selection=False):
        """Refresh the file list from database."""
        # Store current selection and open states
        selected = self.tree.selection()
        selected_path = None
        if selected:
            selected_path = self.tree.item(selected[0])['values'][0] if selected else None
        self._store_open_states()
        
        self.tree.delete(*self.tree.get_children())
        
        # Get all files from database
        files = self.db.get_all_files()
        
        # Create directory structure
        directories: Dict[str, str] = {}
        file_items = []  # Store file items for selection
        
        for file_path, relative_path, is_translated in files:
            # Split path into parts
            # Check if file is marked as not required
            is_not_required = relative_path.startswith("NOT_REQUIRED:")
            if is_not_required:
                relative_path = relative_path.replace("NOT_REQUIRED:", "")
                
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
            
            # Set style based on file status
            if is_not_required:
                self.tree.item(item_id, tags=('not_required',))
            elif is_translated:
                self.tree.item(item_id, tags=('translated',))
            
            file_items.append((item_id, file_path, is_translated or is_not_required))
        
        # Restore open states
        self._restore_open_states()
        
        # Restore selection or select next untranslated
        if maintain_selection and selected_path:
            for item_id, path, _ in file_items:
                if path == selected_path:
                    self.tree.selection_set(item_id)
                    self.tree.see(item_id)
                    break
        
    def get_next_untranslated(self, current_path: Optional[str] = None) -> Optional[str]:
        """Get the path of the next untranslated file after the current one."""
        all_items = []
        
        def collect_items(parent=""):
            for item in self.tree.get_children(parent):
                if self.tree.item(item)["values"]:  # If it's a file
                    all_items.append(item)
                collect_items(item)
        
        collect_items()
        
        if not all_items:
            return None
            
        # Find current item index
        current_index = -1
        if current_path:
            for i, item in enumerate(all_items):
                if self.tree.item(item)["values"][0] == current_path:
                    current_index = i
                    break
        
        # Look for next untranslated file
        start_index = current_index + 1 if current_index >= 0 else 0
        
        # First search from current position to end
        for i in range(start_index, len(all_items)):
            item = all_items[i]
            if 'translated' not in self.tree.item(item)["tags"]:
                return self.tree.item(item)["values"][0]
                
        # If not found, search from beginning to current position
        for i in range(0, start_index):
            item = all_items[i]
            if 'translated' not in self.tree.item(item)["tags"]:
                return self.tree.item(item)["values"][0]
        
        return None
        
    def _on_select(self, event):
        """Handle file selection."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            if item['values']:  # Only if it's a file
                self.on_select(item['values'][0])

class DlgGuiEditor:
    def __init__(self, db_path: str = "dlg_files.db"):
        self.db = DbHandler(db_path)
        self.translator = AITranslator()
        
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
        file_menu.add_command(label="Mark as Not Required", command=self.mark_not_required, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Rescan Files", command=self.rescan_files)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Configure OpenAI API Key", command=self._show_api_key_dialog)
        
        # Debug menu
        debug_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Debug", menu=debug_menu)
        debug_menu.add_command(label="Analyze First Entry", command=self._analyze_first_entry)
        debug_menu.add_command(label="Save First Entry Binary", command=self._save_first_entry_binary)
        
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
        
        # Add translate button to toolbar
        toolbar_frame = ttk.Frame(editor_frame)
        toolbar_frame.pack(pady=(0, 10))
        
        self.translate_btn = ttk.Button(
            toolbar_frame,
            text="Translate Selected",
            command=self._translate_selected,
            state=tk.DISABLED
        )
        self.translate_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(
            toolbar_frame,
            text="Next untranslated",
            command=self._load_next_untranslated
        )
        self.next_btn.pack(side=tk.LEFT)
        
    def _setup_bindings(self):
        """Setup keyboard shortcuts."""
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-t>", lambda e: self.mark_translated())
        self.root.bind("<Control-n>", lambda e: self.mark_not_required())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        
        # Configure canvas scrolling
        self.canvas.bind('<Enter>', self._bound_to_mousewheel)
        self.canvas.bind('<Leave>', self._unbound_to_mousewheel)
        
    def _show_api_key_dialog(self):
        """Show dialog for configuring OpenAI API key."""
        APIKeyDialog(self.root, self.translator)
        # Refresh editors to show/hide translate buttons
        if self.current_file:
            self.load_file(self.current_file)
        
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
                    translator=self.translator,
                    padding=(5, 5, 5, 15)
                )
                editor.pack(fill=tk.X, padx=5, pady=5)
                self.section_editors.append(editor)
            
            # Enable translate button if we have sections
            self.translate_btn.configure(
                state=tk.NORMAL if self.section_editors else tk.DISABLED
            )
            
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
        """Mark current file as translated and move to next untranslated file."""
        if not self.current_file:
            return
            
        # First save the current file
        self.save_file()
            
        # Mark as translated
        is_translated = self.db.is_file_translated(self.current_file)
        self.db.set_translated_status(self.current_file, not is_translated)
        
        # Refresh file list while maintaining tree state
        self.file_list.refresh_files(maintain_selection=True)
        
        if not is_translated:  # If we just marked it as translated
            # Find and load next untranslated file
            next_file = self.file_list.get_next_untranslated(self.current_file)
            if next_file:
                self.load_file(next_file)
                status = "Marked as translated - Loaded next untranslated file"
            else:
                status = "Marked as translated - No more untranslated files"
        else:
            status = "Marked as not translated"
            
        self.status_var.set(status)
        
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
        
    def _translate_selected(self):
        """Translate all selected sections in a single batch."""
        if not self.translator.has_valid_key():
            messagebox.showerror(
                "Error",
                "OpenAI API key not configured. Please configure it in Settings."
            )
            return
            
        selected_sections = [
            editor for editor in self.section_editors
            if editor.is_selected.get()
        ]
        
        if not selected_sections:
            messagebox.showinfo(
                "Info",
                "Please select sections to translate"
            )
            return
            
        try:
            # Prepare batch translation request
            sections_text = []
            for editor in selected_sections:
                sections_text.append({
                    'text': editor.get_text(),
                    'max_length': editor.max_chars,
                    'index': editor.index
                })
            
            # Create prompt for batch translation
            prompt = "Translate the following sections from Russian to English. Each section has a maximum length limit in bytes.\n\n"
            for i, section in enumerate(sections_text):
                prompt += f"Section {i + 1} (max {section['max_length']} bytes):\n{section['text']}\n\n"
            
            prompt += "\nRequirements:\n"
            prompt += "1. Translate each section while preserving its meaning and tone\n"
            prompt += "2. Keep each translation within its specified byte limit\n"
            prompt += "3. Use only basic Latin characters (a-z, A-Z) and standard punctuation\n"
            prompt += "4. Maintain any greeting forms and exclamations\n"
            prompt += "5. Format the response with 'Section N:' on its own line, followed by the translation on the next line\n"
            prompt += "6. Keep each section's translation as a single paragraph\n"
            
            # Get batch translation
            response = self.translator.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert translator specializing in game dialog translation from Russian to English. Format each section's translation clearly with 'Section N:' headers."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse response and extract translations
            response_text = response.choices[0].message.content
            translations = []
            current_section = None
            current_text = []
            
            for line in response_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check for section header
                if line.lower().startswith('section ') and ':' in line:
                    # Save previous section if exists
                    if current_section is not None and current_text:
                        translations.append(' '.join(current_text))
                    current_section = line
                    current_text = []
                elif current_section is not None:
                    current_text.append(line)
            
            # Add the last section
            if current_section is not None and current_text:
                translations.append(' '.join(current_text))
            
            # Ensure we have the right number of translations
            if len(translations) != len(selected_sections):
                raise ValueError(f"Expected {len(selected_sections)} translations, but got {len(translations)}")
            
            # Show results in dialog
            BatchTranslationDialog(self.root, selected_sections, translations)
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Translation failed: {str(e)}"
            )
        
    def _load_next_untranslated(self):
        """Load the next untranslated file."""
        if self.current_file:
            # First save the current file
            self.save_file()
            
        # Find and load next untranslated file
        next_file = self.file_list.get_next_untranslated(self.current_file)
        if next_file:
            # Find the item in the tree that corresponds to this file
            def find_item_by_path(parent=""):
                for item in self.file_list.tree.get_children(parent):
                    if self.file_list.tree.item(item)["values"] and self.file_list.tree.item(item)["values"][0] == next_file:
                        return item
                    found = find_item_by_path(item)
                    if found:
                        return found
                return None
                
            item_id = find_item_by_path()
            if item_id:
                # Ensure parent folders are expanded
                parent = self.file_list.tree.parent(item_id)
                while parent:
                    self.file_list.tree.item(parent, open=True)
                    parent = self.file_list.tree.parent(parent)
                    
                # Select and scroll to the item
                self.file_list.tree.selection_set(item_id)
                self.file_list.tree.see(item_id)
            
            self.load_file(next_file)
            self.status_var.set("Loaded next untranslated file")
        else:
            self.status_var.set("No more untranslated files")
            messagebox.showinfo("Info", "No more untranslated files found")
        
    def mark_not_required(self):
        """Mark current file as not required for translation."""
        if not self.current_file:
            return
            
        # Get the relative path from the database
        relative_path = None
        files = self.db.get_all_files()
        for file_path, rel_path, _ in files:
            if file_path == self.current_file:
                relative_path = rel_path
                break
                
        if not relative_path:
            messagebox.showerror("Error", "Could not find file in database")
            return
            
        # Update the relative path to mark as not required
        if relative_path.startswith("NOT_REQUIRED:"):
            # Remove the not required status
            new_relative_path = relative_path.replace("NOT_REQUIRED:", "")
            self.db.update_relative_path(self.current_file, new_relative_path)
            status = "Marked as required for translation"
        else:
            # Add the not required status
            new_relative_path = "NOT_REQUIRED:" + relative_path
            self.db.update_relative_path(self.current_file, new_relative_path)
            status = "Marked as not required for translation"
            
            # Find and load next untranslated file
            next_file = self.file_list.get_next_untranslated(self.current_file)
            if next_file:
                self.load_file(next_file)
                status += " - Loaded next untranslated file"
            
        # Refresh file list while maintaining tree state
        self.file_list.refresh_files(maintain_selection=True)
        self.status_var.set(status)
        
    def _analyze_first_entry(self):
        """Analyze the binary structure of the first entry in the current file."""
        if not self.handler or not self.current_file:
            messagebox.showinfo("Debug", "No file is currently loaded")
            return
            
        result = self.handler.debug_first_entry()
        
        # Create a dialog to display the results
        dialog = tk.Toplevel(self.root)
        dialog.title("First Entry Analysis")
        dialog.geometry("800x600")
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create a frame with padding
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a scrollable text area
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget with monospaced font
        text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=('Courier', 10),
            yscrollcommand=scrollbar.set
        )
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)
        
        # Insert the analysis result
        text.insert(tk.END, result)
        text.config(state=tk.DISABLED)  # Make it read-only
        
        # Add a close button
        ttk.Button(frame, text="Close", command=dialog.destroy).pack(pady=(10, 0))
        
    def _save_first_entry_binary(self):
        """Save the binary data of the first entry to a file for analysis."""
        if not self.handler or not self.current_file:
            messagebox.showinfo("Debug", "No file is currently loaded")
            return
            
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")],
            title="Save First Entry Binary"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            self.handler.save_first_entry_binary(file_path)
            messagebox.showinfo(
                "Debug", 
                f"First entry binary saved to {file_path}\n"
                f"Analysis saved to {file_path}.txt"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save binary: {str(e)}")
        
    def run(self):
        """Run the editor application."""
        self.status_var.set("Ready - Select a file to edit")
        self.root.mainloop()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close() 