import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os
from typing import Optional, Callable
from db_handler import DbHandler

class SetupWindow:
    def __init__(self, db: DbHandler, on_complete: Callable[[], None]):
        """Initialize setup window for game path selection and file scanning."""
        self.db = db
        self.on_complete = on_complete
        
        # Create window
        self.root = tk.Tk()
        self.root.title("DLG Editor Setup")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Center window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 400) // 2
        self.root.geometry(f"600x400+{x}+{y}")
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create and layout all widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Welcome text
        ttk.Label(
            main_frame,
            text="Welcome to DLG Editor",
            font=('TkDefaultFont', 16, 'bold')
        ).pack(pady=(0, 20))
        
        ttk.Label(
            main_frame,
            text="Please select your Heart of Eternity game folder:",
            wraplength=500
        ).pack(pady=(0, 10))
        
        # Path selection frame
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        browse_btn = ttk.Button(
            path_frame,
            text="Browse...",
            command=self._browse_folder
        )
        browse_btn.pack(side=tk.LEFT)
        
        # Progress frame
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=20)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress.pack(fill=tk.X)
        
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(
            self.progress_frame,
            textvariable=self.status_var,
            wraplength=500
        )
        self.status_label.pack(pady=(5, 0))
        
        # Initially hide progress frame
        self.progress_frame.pack_forget()
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, pady=20)
        
        self.scan_btn = ttk.Button(
            btn_frame,
            text="Scan for DLG Files",
            command=self._start_scan,
            state=tk.DISABLED
        )
        self.scan_btn.pack()
        
        # Check for existing path
        existing_path = self.db.get_game_path()
        if existing_path and os.path.exists(existing_path):
            self.path_var.set(existing_path)
            self.scan_btn.configure(state=tk.NORMAL)
            
    def _browse_folder(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(
            title="Select Heart of Eternity Game Folder"
        )
        if folder:
            self.path_var.set(folder)
            self.scan_btn.configure(state=tk.NORMAL)
            
    def _start_scan(self):
        """Start scanning for DLG files."""
        game_path = self.path_var.get()
        if not game_path or not os.path.exists(game_path):
            messagebox.showerror(
                "Error",
                "Please select a valid game folder"
            )
            return
            
        # Show progress frame
        self.progress_frame.pack(fill=tk.X, pady=20)
        self.scan_btn.configure(state=tk.DISABLED)
        
        # Clear existing files
        self.db.clear_all_files()
        
        # Save game path
        self.db.set_game_path(game_path)
        
        # Start scanning
        self._scan_files(game_path)
        
    def _scan_files(self, game_path: str):
        """Scan for DLG files recursively."""
        total_files = sum(1 for _ in Path(game_path).rglob("*.dlg"))
        if total_files == 0:
            messagebox.showerror(
                "Error",
                "No DLG files found in the selected folder"
            )
            self.progress_frame.pack_forget()
            self.scan_btn.configure(state=tk.NORMAL)
            return
            
        processed = 0
        for file_path in Path(game_path).rglob("*.dlg"):
            relative_path = str(file_path.relative_to(game_path))
            self.db.add_dlg_file(str(file_path), relative_path)
            
            processed += 1
            progress = (processed / total_files) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"Scanning: {relative_path}")
            self.root.update()
            
        self.status_var.set(f"Found {total_files} DLG files")
        self.root.after(1000, self._complete_setup)
        
    def _complete_setup(self):
        """Complete the setup and close window."""
        self.root.destroy()
        self.on_complete()
        
    def run(self):
        """Run the setup window."""
        self.root.mainloop() 