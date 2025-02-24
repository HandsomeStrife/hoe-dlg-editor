import tkinter as tk
from tkinter import ttk, messagebox
from ai_translator import AITranslator

class APIKeyDialog:
    def __init__(self, parent, translator: AITranslator):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("OpenAI API Key Configuration")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        window_width = 400
        window_height = 150
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.translator = translator
        self._create_widgets()
        
    def _create_widgets(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # API Key entry
        ttk.Label(
            main_frame,
            text="Enter your OpenAI API Key:",
            wraplength=350
        ).pack(pady=(0, 10))
        
        self.key_var = tk.StringVar()
        key_entry = ttk.Entry(main_frame, textvariable=self.key_var, width=50)
        key_entry.pack(pady=(0, 20))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(
            btn_frame,
            text="Save",
            command=self._save_key
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT)
        
    def _save_key(self):
        api_key = self.key_var.get().strip()
        if not api_key:
            messagebox.showerror(
                "Error",
                "Please enter an API key"
            )
            return
            
        if self.translator.save_api_key(api_key):
            messagebox.showinfo(
                "Success",
                "API key saved successfully"
            )
            self.dialog.destroy()
        else:
            messagebox.showerror(
                "Error",
                "Failed to save API key"
            ) 