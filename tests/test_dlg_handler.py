import pytest
from pathlib import Path
import tempfile
from src.dlg_handler import DlgHandler, DialogBranch, DialogChoice

@pytest.fixture
def sample_dlg_content():
    return (
        "First line ‡ЋЌЏ0041 ¬?QR5=1\n"
        "> Choice 1 їїїHERB03>=2\n"
        "Response 1 {D-ITEM}\n"
        "|Second line †D1430\n"
        "> Choice 2 ъ3\n"
        "Response 2 Џ[102,45,887]"
    )

@pytest.fixture
def temp_dlg_file(sample_dlg_content):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dlg') as f:
        f.write(sample_dlg_content.encode('cp1251'))
    yield Path(f.name)
    Path(f.name).unlink()

def test_read_file(temp_dlg_file):
    handler = DlgHandler(str(temp_dlg_file))
    handler.read_file()
    assert handler.raw_content is not None
    assert handler.encoding in ['cp1251', 'utf-8']

def test_parse_dialog(temp_dlg_file):
    handler = DlgHandler(str(temp_dlg_file))
    handler.read_file()
    handler.parse_dialog()
    
    assert isinstance(handler.dialog_tree, DialogBranch)
    assert "First line" in handler.dialog_tree.text
    assert "‡ЋЌЏ0041" in handler.dialog_tree.control_codes
    assert len(handler.dialog_tree.choices) == 1
    
    assert handler.dialog_tree.next_branch is not None
    assert "Second line" in handler.dialog_tree.next_branch.text
    assert "†D1430" in handler.dialog_tree.next_branch.control_codes

def test_save_file(temp_dlg_file):
    handler = DlgHandler(str(temp_dlg_file))
    handler.read_file()
    handler.parse_dialog()
    
    # Save to new file
    output_file = str(temp_dlg_file) + '.new'
    handler.save_file(output_file)
    
    # Read back and verify
    new_handler = DlgHandler(output_file)
    new_handler.read_file()
    new_handler.parse_dialog()
    
    assert new_handler.dialog_tree.text == handler.dialog_tree.text
    assert new_handler.dialog_tree.control_codes == handler.dialog_tree.control_codes
    
    # Cleanup
    Path(output_file).unlink()

def test_control_codes_preservation(temp_dlg_file):
    handler = DlgHandler(str(temp_dlg_file))
    handler.read_file()
    handler.parse_dialog()
    
    # Check all special control codes are preserved
    tree_text = handler._tree_to_text(handler.dialog_tree)
    assert "‡ЋЌЏ0041" in tree_text
    assert "¬?QR5=1" in tree_text
    assert "їїїHERB03>=2" in tree_text
    assert "{D-ITEM}" in tree_text
    assert "†D1430" in tree_text
    assert "ъ3" in tree_text
    assert "Џ[102,45,887]" in tree_text 