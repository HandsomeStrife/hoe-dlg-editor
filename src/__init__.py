"""
DLG Editor package for reading and modifying game dialog files
while preserving binary structure and special control characters.
"""

from .dlg_handler import DlgHandler, DialogBranch, DialogChoice
from .editor import DlgEditor

__all__ = ['DlgHandler', 'DialogBranch', 'DialogChoice', 'DlgEditor']

__version__ = '0.1.1'