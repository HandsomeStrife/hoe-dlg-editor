import os
import re
import chardet
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class DialogBranch:
    text: str
    control_codes: List[str]
    choices: List['DialogChoice']
    next_branch: Optional['DialogBranch'] = None

@dataclass
class DialogChoice:
    text: str
    response_codes: List[str]
    outcome: Optional[str] = None
    outcome_codes: List[str] = None

@dataclass
class TextSection:
    text: str  # The Cyrillic/editable text
    start: int  # Start position in original binary
    end: int   # End position in original binary
    encoding: str  # The encoding used for this section

class DlgHandler:
    # Special control characters from the spec
    CONTROL_CHARS = {
        'BRANCH_SEP': '|',
        'CHOICE_MARKER': '>',
        'LINE_CONT': '\\',
        'VOICE_META': '‡ЋЌЏ',
        'INVENTORY': 'їїї',
        'CONDITION': '¬?',
        'DYNAMIC': '{D-',
        'REPUTATION': 'ъ',
        'TIME': '†',
        'COORDINATES': 'Џ'
    }

    def __init__(self, filepath: str):
        """Initialize the DLG handler with a file path."""
        self.filepath = filepath
        self.encoding = None
        self._original_binary = None
        self.text_sections = []  # List of TextSection objects

    def _analyze_binary(self) -> Dict[str, any]:
        """Analyze binary content to determine structure and encoding."""
        analysis = {
            'total_bytes': len(self._original_binary),
            'byte_counts': {},
            'non_cp1251_positions': [],
            'potential_text_ranges': []
        }
        
        # Count byte frequencies
        for i, byte in enumerate(self._original_binary):
            analysis['byte_counts'][byte] = analysis['byte_counts'].get(byte, 0) + 1
            
            # Check if byte is valid in CP1251
            try:
                bytes([byte]).decode('cp1251')
            except UnicodeDecodeError:
                analysis['non_cp1251_positions'].append(i)
        
        # Print analysis
        print("\nFile Analysis:")
        print(f"Total bytes: {analysis['total_bytes']}")
        print(f"Non-CP1251 bytes: {len(analysis['non_cp1251_positions'])} positions")
        print("\nFirst few non-CP1251 bytes:")
        for pos in analysis['non_cp1251_positions'][:5]:
            byte = self._original_binary[pos]
            context = self._original_binary[max(0, pos-5):min(len(self._original_binary), pos+6)]
            print(f"Position {pos}: 0x{byte:02x} (context: {context})")
            
        return analysis

    def read_file(self) -> None:
        """Read the DLG file and detect its encoding."""
        with open(self.filepath, 'rb') as f:
            self._original_binary = f.read()
            
        # Use CP1251 for text encoding
        self.encoding = 'cp1251'
        
        # Extract text sections
        self._extract_text_sections()

    def _extract_text_sections(self) -> None:
        """Extract sections of text while preserving exact binary structure."""
        # First, identify special binary sequences to preserve
        special_sequences = {
            1119: b'\x98\x04\x9d'  # Special control sequence found in analysis
        }
        
        # Create a mask of positions to skip (binary data)
        binary_positions = set()
        for pos, seq in special_sequences.items():
            for i in range(len(seq)):
                binary_positions.add(pos + i)
        
        # Convert to string, preserving binary positions
        content_parts = []
        byte_to_char_map = {}  # Map byte positions to character positions
        char_pos = 0
        current_pos = 0
        
        while current_pos < len(self._original_binary):
            if current_pos in binary_positions:
                byte_to_char_map[current_pos] = char_pos
                content_parts.append('␀')  # Use a special character as placeholder
                char_pos += 1
                current_pos += 1
                continue
                
            # Try to decode as CP1251
            try:
                char = self._original_binary[current_pos:current_pos + 1].decode(self.encoding)
                # Skip null bytes and control characters
                if char == '\x00' or ord(char) < 32:
                    byte_to_char_map[current_pos] = char_pos
                    content_parts.append('␀')
                else:
                    byte_to_char_map[current_pos] = char_pos
                    content_parts.append(char)
                char_pos += 1
                current_pos += 1
            except UnicodeDecodeError:
                byte_to_char_map[current_pos] = char_pos
                content_parts.append('␀')
                char_pos += 1
                current_pos += 1
            
        content = ''.join(content_parts)
        
        # Find text sections using a pattern that matches valid text sequences
        # Updated pattern to handle contractions and apostrophes properly
        text_pattern = r"""(?x)  # Enable verbose mode for better readability
            (?:
                # Match Cyrillic text with possible apostrophes and punctuation
                [А-Яа-яЁё][А-Яа-яЁё\s,.!?'"-]*[А-Яа-яЁё]
                |
                # Match Latin text with possible apostrophes and punctuation
                [A-Za-z][A-Za-z\s,.!?'"-]*[A-Za-z]
                |
                # Match mixed Cyrillic/Latin with possible apostrophes and punctuation
                [А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z\s,.!?'"-]*[А-Яа-яЁёA-Za-z]
            )
        """
        
        # Find all matches
        self.text_sections = []
        for match in re.finditer(text_pattern, content, re.VERBOSE):
            text = match.group(0)
            
            # Skip if the text has too many special characters
            if text.count('␀') > len(text) * 0.1:  # More than 10% special chars
                continue
                
            # Get exact byte positions using our mapping
            start_char = match.start()
            end_char = match.end()
            
            # Find the corresponding byte positions
            start_bytes = next(pos for pos, char_pos in byte_to_char_map.items() if char_pos == start_char)
            end_bytes = next(pos for pos, char_pos in byte_to_char_map.items() if char_pos == end_char - 1) + 1
            
            # Skip sections that overlap with binary data
            if any(pos in binary_positions for pos in range(start_bytes, end_bytes)):
                continue
            
            # Skip sections that are too short
            if len(text.strip()) < 2:
                continue
                
            # Clean up the text - remove any remaining special characters
            clean_text = text.strip().replace('␀', '')
            if not clean_text:  # Skip if nothing remains after cleaning
                continue
                
            # Calculate available space including trailing nulls
            available_space = self._calculate_available_space(start_bytes, end_bytes)
                
            self.text_sections.append(TextSection(
                text=clean_text,
                start=start_bytes,
                end=start_bytes + available_space,  # Use the full available space
                encoding=self.encoding
            ))

    def _calculate_available_space(self, start: int, initial_end: int) -> int:
        """Calculate available space including trailing null bytes.
        
        Args:
            start: Start position of the text section
            initial_end: Initial end position of the text section
            
        Returns:
            Total available space including trailing nulls
        """
        # Start from the initial end position
        current_pos = initial_end
        
        # Look for consecutive null bytes or spaces
        while current_pos < len(self._original_binary):
            byte = self._original_binary[current_pos:current_pos + 1]
            # Stop if we hit a non-null byte that's not a space
            if byte != b'\x00' and byte != b' ':
                break
            current_pos += 1
            
        # Calculate total available space
        return current_pos - start

    def get_editable_text(self) -> str:
        """Get all Cyrillic sections joined with newlines for editing."""
        return "\n".join(section.text for section in self.text_sections)

    def compare_files(self, other_path: str) -> List[str]:
        """Compare this file with another file and return list of differences."""
        differences = []
        
        with open(other_path, 'rb') as f:
            other_binary = f.read()
            
        if len(self._original_binary) != len(other_binary):
            differences.append(f"File sizes differ: Original={len(self._original_binary)}, New={len(other_binary)}")
            
        # Compare byte by byte
        for i, (orig_byte, new_byte) in enumerate(zip(self._original_binary, other_binary)):
            if orig_byte != new_byte:
                # Get context (5 bytes before and after)
                start = max(0, i - 5)
                end = min(len(self._original_binary), i + 6)
                
                orig_context = self._original_binary[start:end]
                new_context = other_binary[start:end]
                
                try:
                    # Try to decode the context
                    orig_text = orig_context.decode(self.encoding, errors='replace')
                    new_text = new_context.decode(self.encoding, errors='replace')
                except:
                    orig_text = str(orig_context)
                    new_text = str(new_context)
                
                differences.append(
                    f"Difference at position {i}:\n"
                    f"Original byte: {orig_byte} (context: {orig_text})\n"
                    f"New byte: {new_byte} (context: {new_text})"
                )
                
        return differences

    def save_with_updated_text(self, new_text: str, output_path: Optional[str] = None) -> None:
        """Save file with updated text sections while preserving exact binary structure."""
        # Split the new text into sections
        new_sections = new_text.strip().split("\n")
        
        if len(new_sections) != len(self.text_sections):
            raise ValueError(f"Number of text sections changed. Expected {len(self.text_sections)}, got {len(new_sections)}")
        
        # Create exact copy of original binary
        new_binary = bytearray(self._original_binary)
        
        # Replace each section
        for i, (section, new_section_text) in enumerate(zip(self.text_sections, new_sections)):
            try:
                # Only encode the actual text part
                new_bytes = new_section_text.encode(self.encoding)
                
                # Check if the new text fits in the available space
                available_space = section.end - section.start
                if len(new_bytes) > available_space:
                    raise ValueError(f"New text in section {i+1} is too long to fit in available space (max {available_space} bytes)")
                
                # Replace section while preserving exact length
                padded_bytes = new_bytes + b'\x00' * (available_space - len(new_bytes))
                new_binary[section.start:section.end] = padded_bytes
                
            except UnicodeEncodeError as e:
                raise ValueError(f"Section {i+1} contains characters that cannot be encoded in {self.encoding}")
        
        # Save to file
        output_path = output_path or self.filepath
        with open(output_path, 'wb') as f:
            f.write(new_binary)
            
        # Compare files if we saved to a different path
        if output_path != self.filepath:
            differences = self.compare_files(output_path)
            if differences:
                print("\nWarning: Differences found between original and new file:")
                for diff in differences:
                    print(diff)
                print()

    def save_file(self, output_path: Optional[str] = None) -> None:
        """Compatibility method for old interface."""
        raise NotImplementedError("Use save_with_updated_text instead")

    def parse_dialog(self) -> None:
        """Parse the raw content into a dialog tree structure."""
        if not self.text_sections:
            raise ValueError("No content loaded. Call read_file() first.")
        
        # Split into branches while preserving control codes
        branches = self._split_branches(self.get_editable_text())
        self.dialog_tree = self._build_tree(branches)

    def _split_branches(self, content: str) -> List[str]:
        """Split content into branches while preserving special sequences."""
        # Use regex to split on | but not within [] or {}
        pattern = r'\|(?![^\[]*\])(?![^\{]*\})'
        return [b.strip() for b in re.split(pattern, content) if b.strip()]

    def _build_tree(self, branches: List[str]) -> DialogBranch:
        """Build a dialog tree from branches."""
        if not branches:
            return None

        current_branch = branches[0]
        # Split into text and control codes
        text, codes = self._extract_codes(current_branch)
        
        # Parse choices (lines starting with >)
        choices = []
        choice_lines = re.findall(r'>.*?(?=(?:>|\Z))', current_branch, re.DOTALL)
        for choice in choice_lines:
            choice_text, choice_codes = self._extract_codes(choice.lstrip('>'))
            choices.append(DialogChoice(
                text=choice_text,
                response_codes=choice_codes
            ))

        return DialogBranch(
            text=text,
            control_codes=codes,
            choices=choices,
            next_branch=self._build_tree(branches[1:]) if len(branches) > 1 else None
        )

    def _extract_codes(self, text: str) -> Tuple[str, List[str]]:
        """Extract control codes from text while preserving their original position."""
        codes = []
        
        # Find all control sequences
        for name, char in self.CONTROL_CHARS.items():
            pattern = f"{re.escape(char)}[^{self.CONTROL_CHARS['BRANCH_SEP']}\n]*"
            matches = re.finditer(pattern, text)
            for match in matches:
                codes.append(match.group())
                
        # Remove codes from text while preserving structure
        clean_text = text
        for code in codes:
            clean_text = clean_text.replace(code, '', 1)
            
        return clean_text.strip(), codes

    def _tree_to_text(self, branch: DialogBranch) -> str:
        """Convert a dialog tree back to text format."""
        if not branch:
            return ""
            
        # Reconstruct the branch text with control codes
        text = branch.text
        for code in branch.control_codes:
            text += f" {code}"
            
        # Add choices
        for choice in branch.choices:
            text += f"\n> {choice.text}"
            for code in choice.response_codes:
                text += f" {code}"
            if choice.outcome:
                text += f"\n{choice.outcome}"
                if choice.outcome_codes:
                    for code in choice.outcome_codes:
                        text += f" {code}"
                        
        # Add next branch if exists
        if branch.next_branch:
            text += f"\n|{self._tree_to_text(branch.next_branch)}"
            
        return text 