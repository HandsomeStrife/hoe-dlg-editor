import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional
import os

class DbHandler:
    def __init__(self, db_path: str = "dlg_files.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
        
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_config (
                id INTEGER PRIMARY KEY,
                game_path TEXT NOT NULL
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS dlg_files (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                relative_path TEXT NOT NULL,
                is_translated BOOLEAN DEFAULT 0,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        
    def set_game_path(self, path: str) -> None:
        """Set or update the game path."""
        self.cursor.execute("DELETE FROM game_config")  # Clear existing
        self.cursor.execute("INSERT INTO game_config (game_path) VALUES (?)", (path,))
        self.conn.commit()
        
    def get_game_path(self) -> Optional[str]:
        """Get the configured game path."""
        self.cursor.execute("SELECT game_path FROM game_config LIMIT 1")
        result = self.cursor.fetchone()
        return result[0] if result else None
        
    def add_dlg_file(self, file_path: str, relative_path: str) -> None:
        """Add or update a DLG file in the database."""
        self.cursor.execute("""
            INSERT OR REPLACE INTO dlg_files (file_path, relative_path)
            VALUES (?, ?)
        """, (file_path, relative_path))
        self.conn.commit()
        
    def get_all_files(self) -> List[Tuple[str, str, bool]]:
        """Get all DLG files with their paths and translation status."""
        self.cursor.execute("""
            SELECT file_path, relative_path, is_translated 
            FROM dlg_files 
            ORDER BY relative_path
        """)
        return self.cursor.fetchall()
        
    def set_translated_status(self, file_path: str, is_translated: bool) -> None:
        """Mark a file as translated or not."""
        self.cursor.execute("""
            UPDATE dlg_files 
            SET is_translated = ?, last_modified = CURRENT_TIMESTAMP
            WHERE file_path = ?
        """, (is_translated, file_path))
        self.conn.commit()
        
    def is_file_translated(self, file_path: str) -> bool:
        """Check if a file is marked as translated."""
        self.cursor.execute("""
            SELECT is_translated 
            FROM dlg_files 
            WHERE file_path = ?
        """, (file_path,))
        result = self.cursor.fetchone()
        return bool(result[0]) if result else False
        
    def clear_all_files(self) -> None:
        """Clear all DLG files from the database."""
        self.cursor.execute("DELETE FROM dlg_files")
        self.conn.commit()
        
    def close(self):
        """Close the database connection."""
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def update_relative_path(self, file_path: str, new_relative_path: str) -> None:
        """Update the relative path for a file."""
        self.cursor.execute("""
            UPDATE dlg_files 
            SET relative_path = ?
            WHERE file_path = ?
        """, (new_relative_path, file_path))
        self.conn.commit()
        
    def get_relative_path(self, file_path: str) -> str:
        """Get the relative path for a file."""
        self.cursor.execute("""
            SELECT relative_path 
            FROM dlg_files 
            WHERE file_path = ?
        """, (file_path,))
        result = self.cursor.fetchone()
        return result[0] if result else None 