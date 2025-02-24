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
    trailing_control: str = ""  # Additional metadata for trailing control characters

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
        # Define known control characters - only include actual control characters, not punctuation
        self._known_control_chars = ["†", "ъ", "Џ", "б", "H", "3"]  # Initial set of known control chars
        # Define characters that should never be treated as control characters
        self._excluded_control_chars = [" ", ".", ",", "!", "?", ":", ";", "-", "—", "(", ")", "[", "]"]

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

    def _is_file_reference(self, text):
        """Determine if a text section is a file reference rather than dialog."""
        text = text.strip()
        
        # Check for common file extensions
        common_extensions = ['.scr', '.dlg', '.itm', '.eff', '.ini', '.txt', '.json', '.cfg']
        for ext in common_extensions:
            if text.lower().endswith(ext):
                return True
                
        # Check for file naming patterns
        # No spaces + contains underscore or camelCase + contains dots or slashes
        if ' ' not in text and ('_' in text or (any(c.isupper() for c in text[1:]) and text[0].islower())):
            if '.' in text or '/' in text or '\\' in text:
                return True
                
        # No spaces + all ASCII + contains dot
        if ' ' not in text and all(ord(c) < 128 for c in text) and '.' in text:
            # Looks like a filename if it has extension-like pattern
            extension_pattern = re.search(r'\.[a-zA-Z0-9]{2,4}$', text)
            if extension_pattern:
                return True
                
        return False
        
    def read_file(self) -> None:
        """Read the DLG file and detect its encoding."""
        try:
            with open(self.filepath, 'rb') as f:
                self._original_binary = f.read()
                
            # Check for problematic bytes
            self._check_for_problematic_bytes()
                
            # Always use cp1251 for these files
            self.encoding = 'cp1251'
            
            # Extract text sections
            try:
                self._extract_text_sections()
            except Exception as e:
                print(f"Error extracting text sections: {e}")
                # Fallback to a simpler extraction method
                self._extract_text_sections_simple()
                
            # Filter out any sections with problematic characters
            self._filter_problematic_sections()
            
            # Apply a secondary control code filter
            original_count = len(self.text_sections)
            self.text_sections = [
                section for section in self.text_sections 
                if not self._is_likely_control_code(section.text.strip())
            ]
            filtered_count = original_count - len(self.text_sections)
            if filtered_count > 0:
                print(f"Secondary filter removed {filtered_count} additional control code sequences")
                
            # Third-pass filtering for extremely specific cases
            # Like the "ьэ,р" pattern or other similar short sequences
            # But preserve English text
            self.text_sections = [
                section for section in self.text_sections
                if not (
                    # Only apply this filter to non-English text
                    len(section.text.strip()) <= 5 and 
                    (',' in section.text or '.' in section.text) and 
                    ' ' not in section.text and
                    # Check if this is NOT primarily English
                    sum(1 for c in section.text if ord('a') <= ord(c.lower()) <= ord('z')) / len(section.text) < 0.3
                )
            ]
            
            # Fourth-pass filtering for file references
            self.text_sections = [
                section for section in self.text_sections
                if not self._is_file_reference(section.text)
            ]
            
            # Log detected trailing control characters for future improvement
            self._log_trailing_control_characters()
            
            # Sort sections by position in the file
            self.text_sections.sort(key=lambda section: section.start)
                
        except Exception as e:
            print(f"Error reading file: {e}")
            raise

    def _check_for_problematic_bytes(self):
        """Check for and handle problematic bytes in the binary data."""
        problematic_bytes = []
        # Common control code patterns
        control_patterns = [
            bytes([0xB0, 0xAF, 0xAB]),  # °ЏҐ pattern
            bytes([0xCC, 0xA4, 0xAB]),  # МФҐ pattern
            bytes([0xD0, 0xAB, 0xAB]),  # РҐҐ pattern
            # Add more patterns if identified
        ]
        
        # Check for individual problematic bytes
        for i, byte in enumerate(self._original_binary):
            # Check if this byte would cause a 'charmap' codec error
            try:
                char = bytes([byte]).decode('cp1251')
            except UnicodeDecodeError as e:
                if "charmap" in str(e):
                    problematic_bytes.append((i, byte))
        
        # Check for control code patterns
        marked_as_control = set()
        for i in range(len(self._original_binary) - 2):
            for pattern in control_patterns:
                if i + len(pattern) <= len(self._original_binary):
                    if self._original_binary[i:i+len(pattern)] == pattern:
                        # Mark this as a control code sequence
                        for j in range(i, i+len(pattern)):
                            marked_as_control.add(j)
        
        if problematic_bytes:
            print(f"Warning: Found {len(problematic_bytes)} problematic bytes that may cause 'charmap' codec errors.")
            print(f"First few problematic bytes: {problematic_bytes[:5]}")
            
            # Create a sanitized copy of the binary
            sanitized_binary = bytearray(self._original_binary)
            for pos, _ in problematic_bytes:
                # Replace problematic bytes with a safe value (space)
                sanitized_binary[pos] = 32  # ASCII space
                
            self._original_binary = sanitized_binary
            print("Sanitized binary data by replacing problematic bytes.")
            
        if marked_as_control:
            print(f"Identified {len(marked_as_control)} bytes as part of control code patterns.")
            # We don't modify these in the binary, but will use this information during extraction

    def _filter_problematic_sections(self):
        """Filter out sections with problematic characters."""
        valid_sections = []
        for section in self.text_sections:
            try:
                # Test if the text can be encoded and decoded without errors
                test_bytes = section.text.encode(self.encoding)
                test_text = test_bytes.decode(self.encoding)
                
                # Check for replacement character
                if '\ufffd' in section.text:
                    print(f"Warning: Skipping section with replacement character: {section.text[:20]}...")
                    continue
                
                # Check if this text is primarily English
                text = section.text.strip()
                english_chars = sum(1 for c in text if ord('a') <= ord(c.lower()) <= ord('z'))
                is_english = english_chars / len(text) > 0.5 if len(text) > 0 else False
                
                # For English text, apply minimal filtering
                if is_english:
                    # Only filter English text if it has unusual characters
                    unusual_chars = sum(1 for c in text if c in "ҐЏ°њ†ъЋЌ¬їѓ")
                    if unusual_chars > 0:
                        print(f"Filtering out English text with control characters: {text}")
                        continue
                    # Otherwise, keep it
                    valid_sections.append(section)
                    continue
                
                # For non-English text, apply standard filtering
                
                # Check if this is likely a control code rather than actual text
                if self._is_likely_control_code(section.text):
                    print(f"Filtering out control code sequence: {section.text}")
                    continue
                
                # Additional checks to filter out control sequences that look like text
                # 1. High percentage of non-Cyrillic characters
                cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
                non_cyrillic_ratio = 1 - (cyrillic_chars / len(text) if len(text) > 0 else 0)
                
                # 2. High percentage of unusual characters
                unusual_chars = sum(1 for c in text if c in "ҐЏ°њ†ъЋЌ¬їѓ")
                unusual_ratio = unusual_chars / len(text) if len(text) > 0 else 0
                
                # 3. Short sections with unusual characters
                is_short_unusual = len(text) <= 5 and unusual_chars > 0
                
                # Skip if it meets filtering criteria
                if non_cyrillic_ratio > 0.5 or unusual_ratio > 0.3 or is_short_unusual:
                    print(f"Filtering out control sequence: {text}")
                    continue
                
                # 4. Check if section looks like actual dialog text
                # Must have multiple letters and include spaces or punctuation for longer text
                has_good_text_pattern = (
                    sum(1 for c in text if c.isalpha()) >= 3 or
                    (len(text) > 10 and (' ' in text or any(p in text for p in '.,!?:;')))
                )
                
                if not has_good_text_pattern and len(text) < 15:
                    print(f"Filtering out non-text pattern: {text}")
                    continue

                valid_sections.append(section)
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"Warning: Skipping problematic section: {section.text[:20]}...")
                continue
                
        # Update the text sections list
        self.text_sections = valid_sections
        
    def _extract_text_sections_simple(self) -> None:
        """Simple fallback method to extract text sections."""
        self.text_sections = []
        
        # Look for sequences of printable characters
        current_pos = 0
        while current_pos < len(self._original_binary):
            # Find a potential text start (printable character)
            text_start = None
            while current_pos < len(self._original_binary):
                byte = self._original_binary[current_pos]
                # Skip null bytes and control characters
                if byte == 0 or byte < 32:
                    current_pos += 1
                    continue
                    
                # Try to decode as cp1251
                try:
                    char = self._safe_decode(bytes([byte]), self.encoding)
                    # Check if it's a likely start of a text section - looking for Cyrillic characters
                    if char.isprintable() and not char.isspace() and char != '\ufffd' and char != '□':
                        # Prefer to start with Cyrillic letters
                        if '\u0400' <= char <= '\u04FF' or char.isalpha():
                            text_start = current_pos
                            break
                except:
                    pass
                current_pos += 1
                
            if text_start is None:
                break
                
            # Find the end of this text section
            text_end = text_start
            text_bytes = bytearray()
            
            # Keep track of characters for additional validation
            text_chars = []
            unusual_char_count = 0
            
            while text_end < len(self._original_binary):
                byte = self._original_binary[text_end]
                
                # Stop at null bytes or control characters
                if byte == 0 or byte < 32:
                    break
                    
                # Try to decode
                try:
                    char = self._safe_decode(bytes([byte]), self.encoding)
                    if (char.isprintable() or char.isspace()) and char != '\ufffd' and char != '□':
                        # Track unusual characters
                        if char in "ҐЏ°њ†ъЋЌ¬їѓ":
                            unusual_char_count += 1
                            
                        text_chars.append(char)
                        text_bytes.append(byte)
                        text_end += 1
                    else:
                        break
                except:
                    break
            
            # If we found a text section
            if text_end > text_start:
                try:
                    # Try to decode the text
                    text = self._safe_decode(text_bytes, self.encoding)
                    
                    # Skip if it contains replacement character
                    if '\ufffd' in text or '□' in text:
                        current_pos = text_end + 1
                        continue
                    
                    # Skip if too many unusual characters in short text
                    unusual_ratio = unusual_char_count / len(text) if len(text) > 0 else 0
                    if len(text) <= 5 and unusual_ratio > 0.2:
                        current_pos = text_end + 1
                        continue
                    
                    # Look for trailing control characters like numbers at the end of dialog
                    # Common pattern in dialogs is text followed by control numbers/characters
                    clean_text = text
                    trailing_control = ""
                    
                    # Different types of trailing control character patterns:
                    
                    # 1. Number sequence at end
                    num_match = re.search(r'([^\d]+)(\d+)$', text)
                    if num_match:
                        clean_text = num_match.group(1)
                        trailing_control = num_match.group(2)
                    
                    # 2. Single non-Russian character after Russian text and punctuation
                    elif len(text) > 2:
                        # Look for a pattern where the last character is isolated
                        # Try to detect case where last char is a control code
                        
                        # Russian text typically ends with a letter, punctuation, or space
                        # If the last character breaks this pattern, it might be a control
                        last_char = text[-1]
                        prelast_char = text[-2] if len(text) > 1 else None
                        
                        # Never treat common punctuation or whitespace as a control character
                        if last_char in self._excluded_control_chars:
                            is_suspicious_last_char = False
                        else:
                            # Check if last char is suspiciously different from the rest of the text
                            is_last_russian = '\u0400' <= last_char <= '\u04FF'
                            is_text_mostly_russian = cyrillic_chars / len(text) > 0.7 if len(text) > 0 else False
                            
                            # Last character suspicious conditions:
                            # 1. Text is Russian but last char is not Russian letter
                            # 2. Last char follows punctuation (unlikely in natural text)
                            # 3. Significant script change between content and last char
                            # 4. Last char is a known control character
                            is_suspicious_last_char = (
                                (is_text_mostly_russian and not is_last_russian and last_char not in self._excluded_control_chars) or
                                (prelast_char and prelast_char in ",.;:!?" and last_char not in self._excluded_control_chars) or
                                (ord(prelast_char) - ord(last_char) > 500 if prelast_char else False) or
                                (last_char in self._known_control_chars)
                            )
                        
                        if is_suspicious_last_char:
                            clean_text = text[:-1]
                            trailing_control = last_char
                    
                    # 3. Known control characters at the end
                    for ctrl_char in self._known_control_chars:  # Use our adaptive list
                        if clean_text.endswith(ctrl_char) and ctrl_char not in self._excluded_control_chars:
                            clean_text = clean_text[:-len(ctrl_char)]
                            trailing_control = ctrl_char + trailing_control
                    
                    # Skip if it's too short or doesn't contain letters
                    # For longer text, require spaces or punctuation
                    has_good_text_pattern = (
                        sum(1 for c in clean_text if c.isalpha()) >= 3 or
                        (len(clean_text) > 10 and (' ' in clean_text or any(p in clean_text for p in '.,!?:;')))
                    )
                    
                    if len(clean_text.strip()) > 1 and any(c.isalpha() for c in clean_text) and has_good_text_pattern:
                        # Calculate available space (including trailing nulls)
                        available_space = self._calculate_available_space(text_start, text_end)
                        
                        # Store the section with metadata about trailing control characters
                        section = TextSection(
                            text=clean_text.strip(),
                            start=text_start,
                            end=text_start + available_space,
                            encoding=self.encoding
                        )
                        # Store the trailing control characters as metadata
                        section.trailing_control = trailing_control
                        
                        self.text_sections.append(section)
                except Exception as e:
                    print(f"Error processing section at position {text_start}: {e}")
                    
            # Move to the next position
            current_pos = text_end + 1

    def _extract_text_sections(self) -> None:
        """Extract sections of text while preserving exact binary structure."""
        self.text_sections = []
        
        # Find potential text sections
        current_pos = 0
        while current_pos < len(self._original_binary):
            # Skip null bytes and control characters
            if self._original_binary[current_pos] == 0 or self._original_binary[current_pos] < 32:
                current_pos += 1
                continue
                
            # Try to find a sequence of valid characters
            section_start = current_pos
            section_end = section_start
            
            # Keep track of characters for additional validation
            unusual_char_count = 0
            
            # Accumulate characters until we hit a null or control character
            while section_end < len(self._original_binary):
                byte = self._original_binary[section_end]
                if byte == 0 or byte < 32:
                    break
                
                # Check for unusual characters that might indicate control codes
                try:
                    char = self._safe_decode(bytes([byte]), self.encoding)
                    if char in "ҐЏ°њ†ъЋЌ¬їѓ":
                        unusual_char_count += 1
                except:
                    pass
                
                section_end += 1
                
            # If we found a potential section
            if section_end > section_start:
                try:
                    # Try to decode the section using our safe decode method
                    section_bytes = self._original_binary[section_start:section_end]
                    text = self._safe_decode(section_bytes, self.encoding)
                    
                    # Skip if it contains replacement character
                    if '\ufffd' in text or '□' in text:
                        current_pos = section_end + 1
                        continue
                    
                    # Skip if too many unusual characters in short text
                    unusual_ratio = unusual_char_count / len(text) if len(text) > 0 else 0
                    if len(text) <= 5 and unusual_ratio > 0.2:
                        current_pos = section_end + 1
                        continue
                        
                    # Count Cyrillic characters
                    cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
                    non_cyrillic_ratio = 1 - (cyrillic_chars / len(text) if len(text) > 0 else 0)
                    
                    # Skip sections with high percentage of non-Cyrillic characters
                    if len(text) < 15 and non_cyrillic_ratio > 0.5:
                        current_pos = section_end + 1
                        continue
                    
                    # Look for trailing control characters like numbers at the end of dialog
                    # Common pattern in dialogs is text followed by control numbers/characters
                    clean_text = text
                    trailing_control = ""
                    
                    # Different types of trailing control character patterns:
                    
                    # 1. Number sequence at end
                    num_match = re.search(r'([^\d]+)(\d+)$', text)
                    if num_match:
                        clean_text = num_match.group(1)
                        trailing_control = num_match.group(2)
                    
                    # 2. Single non-Russian character after Russian text and punctuation
                    # Like "Что?!б" where 'б' is the control character
                    # or "барона?H" where 'H' is the control character
                    elif len(text) > 2:
                        # Look for a pattern where the last character is isolated
                        # Try to detect case where last char is a control code
                        
                        # Count Cyrillic characters for analysis
                        cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
                        
                        # Russian text typically ends with a letter, punctuation, or space
                        # If the last character breaks this pattern, it might be a control
                        last_char = text[-1]
                        prelast_char = text[-2] if len(text) > 1 else None
                        
                        # Never treat common punctuation or whitespace as a control character
                        if last_char in self._excluded_control_chars:
                            is_suspicious_last_char = False
                        else:
                            # Check if last char is suspiciously different from the rest of the text
                            is_last_russian = '\u0400' <= last_char <= '\u04FF'
                            is_text_mostly_russian = cyrillic_chars / len(text) > 0.7 if len(text) > 0 else False
                            
                            # Last character suspicious conditions:
                            # 1. Text is Russian but last char is not Russian letter
                            # 2. Last char follows punctuation (unlikely in natural text)
                            # 3. Significant script change between content and last char
                            # 4. Last char is a known control character
                            is_suspicious_last_char = (
                                (is_text_mostly_russian and not is_last_russian and last_char not in self._excluded_control_chars) or
                                (prelast_char and prelast_char in ",.;:!?" and last_char not in self._excluded_control_chars) or
                                (ord(prelast_char) - ord(last_char) > 500 if prelast_char else False) or
                                (last_char in self._known_control_chars)
                            )
                        
                        if is_suspicious_last_char:
                            clean_text = text[:-1]
                            trailing_control = last_char
                    
                    # 3. Known control characters at the end
                    for ctrl_char in self._known_control_chars:  # Use our adaptive list
                        if clean_text.endswith(ctrl_char) and ctrl_char not in self._excluded_control_chars:
                            clean_text = clean_text[:-len(ctrl_char)]
                            trailing_control = ctrl_char + trailing_control
                    
                    # Skip if it's too short or doesn't contain letters
                    # For longer text, require spaces or punctuation
                    has_good_text_pattern = (
                        sum(1 for c in clean_text if c.isalpha()) >= 3 or
                        (len(clean_text) > 10 and (' ' in clean_text or any(p in clean_text for p in '.,!?:;')))
                    )
                    
                    if len(clean_text.strip()) > 1 and any(c.isalpha() for c in clean_text) and has_good_text_pattern:
                        # Calculate available space (including trailing nulls)
                        available_space = self._calculate_available_space(section_start, section_end)
                        
                        # Store the section with metadata about trailing control characters
                        section = TextSection(
                            text=clean_text.strip(),
                            start=section_start,
                            end=section_start + available_space,
                            encoding=self.encoding
                        )
                        # Store the trailing control characters as metadata
                        section.trailing_control = trailing_control
                        
                        self.text_sections.append(section)
                except Exception as e:
                    print(f"Error processing section at position {section_start}: {e}")
                    
            # Move to the next position
            current_pos = section_end + 1

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
        # Filter out problematic sections
        valid_sections = []
        for section in self.text_sections:
            try:
                # Test if the text can be encoded and decoded without errors
                test_bytes = section.text.encode(self.encoding)
                test_text = test_bytes.decode(self.encoding)
                valid_sections.append(section)
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"Warning: Skipping problematic section: {section.text[:20]}...")
                continue
        
        # Update the text sections list
        self.text_sections = valid_sections
        
        # Join the valid sections - show only the clean text without trailing control chars
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
        
        # Process sections
        cleaned_sections = new_sections
        
        # Replace each section
        for i, (section, new_section_text) in enumerate(zip(self.text_sections, cleaned_sections)):
            try:
                # If the text hasn't changed, skip this section
                if new_section_text == section.text:
                    continue
                
                # Handle encoding safely
                try:
                    # First try normal encoding
                    new_bytes = new_section_text.encode(self.encoding)
                except UnicodeEncodeError:
                    # If that fails, try with replacement
                    print(f"Warning: Section {i+1} contains characters that cannot be encoded in {self.encoding}. Using replacement.")
                    new_bytes = new_section_text.encode(self.encoding, errors='replace')
                
                # Check available space and handle trailing control characters
                has_trailing_control = hasattr(section, 'trailing_control') and section.trailing_control
                
                if has_trailing_control:
                    # Calculate how much space we need to preserve for trailing control
                    trailing_bytes = section.trailing_control.encode(self.encoding)
                    trailing_length = len(trailing_bytes)
                    
                    # Get total available space excluding the trailing control
                    total_available = section.end - section.start
                    available_for_text = total_available - trailing_length
                    
                    # If new text is too long to fit with the trailing control
                    if len(new_bytes) > available_for_text:
                        print(f"Warning: New text in section {i+1} is too long to fit with trailing control characters. Truncating.")
                        new_bytes = new_bytes[:available_for_text]
                    
                    # Add padding between text and control character
                    padding_length = available_for_text - len(new_bytes)
                    new_bytes = new_bytes + b'\x00' * padding_length + trailing_bytes
                else:
                    # No trailing control - handle as before
                    available_space = section.end - section.start
                    if len(new_bytes) > available_space:
                        print(f"Warning: New text in section {i+1} is too long ({len(new_bytes)} bytes) to fit in available space (max {available_space} bytes). Truncating.")
                        new_bytes = new_bytes[:available_space]
                    
                    # Fill the remaining space with null bytes
                    padding = b'\x00' * (available_space - len(new_bytes))
                    new_bytes = new_bytes + padding
                
                # Replace section while preserving exact length
                new_binary[section.start:section.end] = new_bytes
                
            except Exception as e:
                print(f"Warning: Error updating section {i+1}: {e}. Skipping this section.")
                continue
        
        # Save to file
        output_path = output_path or self.filepath
        try:
            with open(output_path, 'wb') as f:
                f.write(new_binary)
            
            print(f"File saved successfully to {output_path}")
            
            # Compare files if we saved to a different path
            if output_path != self.filepath:
                differences = self.compare_files(output_path)
                if differences:
                    print("\nWarning: Differences found between original and new file:")
                    for diff in differences:
                        print(diff)
                    print()
        except Exception as e:
            print(f"Error saving file: {e}")
            raise

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

    def _safe_decode(self, byte_data, encoding='cp1251'):
        """Safely decode bytes, handling the 'charmap' codec error."""
        try:
            return byte_data.decode(encoding)
        except UnicodeDecodeError as e:
            if "charmap" in str(e):
                # Handle the specific 'charmap' codec error
                # Replace problematic bytes with a placeholder
                result = ""
                for i, b in enumerate(byte_data):
                    try:
                        result += bytes([b]).decode(encoding)
                    except UnicodeDecodeError:
                        result += "□"  # Use a visible placeholder
                return result
            else:
                # For other errors, use the replace error handler
                return byte_data.decode(encoding, errors='replace') 

    def _is_likely_control_code(self, text):
        """Determine if a text sequence is likely a control code rather than actual dialog text."""
        # Trim the text
        text = text.strip()
        
        # Filter out script file references
        # Check for common file extensions
        common_extensions = ['.scr', '.dlg', '.itm', '.eff', '.ini', '.txt', '.json', '.cfg']
        for ext in common_extensions:
            if text.lower().endswith(ext):
                return True
                
        # Check for file naming patterns with underscores or camelCase without spaces
        if ('_' in text or (any(c.isupper() for c in text[1:]) and text[0].islower())) and ' ' not in text:
            # If it looks like a filename (no spaces, has extension marker or path separator)
            if ('.' in text or '/' in text or '\\' in text):
                return True
                
        # Known specific control patterns to filter
        known_patterns = ["МФҐ", "РҐҐ", "°Ґ", "°ЏҐ", "ьэ,р", "ьэ", "ь,р"]
        for pattern in known_patterns:
            if pattern in text or text in pattern:
                return True
                
        # Check if this is predominantly English text
        # English text should be preserved even if it doesn't match our dialog patterns
        english_chars = sum(1 for c in text if ord('a') <= ord(c.lower()) <= ord('z'))
        is_english = english_chars / len(text) > 0.5 if len(text) > 0 else False
        
        # If it's primarily English, preserve it unless it looks like a control code
        if is_english:
            # Only filter if it has unusual characters
            unusual_chars = sum(1 for c in text if c in "ҐЏ°њ†ъЋЌ¬їѓ")
            if unusual_chars > 0:
                return True
                
            # Also filter if it looks like a technical reference without spaces
            if ' ' not in text and len(text) > 4 and ('.' in text or '_' in text):
                if any(c.isdigit() for c in text) or any(c == '_' for c in text):
                    return True
                    
            # Otherwise, keep English text
            return False
        
        # For non-English text, apply more aggressive filters
        
        # Very short sequences are likely control codes unless they show clear dialog patterns
        if len(text) <= 5:
            # Check for unusual characters
            unusual_chars = sum(1 for c in text if c in "ҐЏ°њ†ъЋЌ¬їѓ")
            if unusual_chars > 0:
                return True
                
            # Short sequences with commas or special punctuation but no spaces are likely codes
            if "," in text and " " not in text:
                return True
                
            # Very short sequences with mixed Cyrillic and punctuation are often codes
            punctuation_count = sum(1 for c in text if c in ",.;:!?-—+=()[]{}")
            if punctuation_count > 0 and len(text) < 4:
                return True
                
            # Short sequences with no spaces are likely codes
            if " " not in text and len(text) < 5:
                # Only keep if it looks like a short word or exclamation
                if not (text.endswith("!") or text.endswith("?")):
                    return True
                
        # High percentage of non-Cyrillic characters in short text
        # Only apply to non-English text
        if len(text) < 10:
            cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
            latin_chars = sum(1 for c in text if ord('a') <= ord(c.lower()) <= ord('z'))
            
            # If it has neither significant Cyrillic nor Latin characters, it's likely a control code
            if cyrillic_chars < len(text) * 0.3 and latin_chars < len(text) * 0.3:
                return True
                
        # Lack of normal text patterns - no spaces in longer text
        if len(text) > 5 and ' ' not in text and not any(p in text for p in '.,!?:;'):
            return True
            
        # Common dialog text patterns
        # Dialog usually has spaces, punctuation, and complete words
        has_dialog_patterns = (
            ' ' in text or 
            any(p in text for p in '.,!?:;') or
            len(text.split()) > 1
        )
        
        # If it's not very short and doesn't have dialog patterns, might be a control code
        # But only for non-English text
        if not is_english and len(text) > 3 and not has_dialog_patterns:
            return True
            
        return False 

    def debug_show_binary(self, text: str) -> str:
        """Show the binary representation of a string for debugging."""
        try:
            # Encode the text using the file's encoding
            binary = text.encode(self.encoding)
            
            # Create a readable hex representation
            hex_repr = ' '.join([f'{b:02x}' for b in binary])
            
            # Create a readable ASCII/text representation
            text_repr = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in binary])
            
            return f"Text: {text}\nLength: {len(binary)} bytes\nHex: {hex_repr}\nASCII: {text_repr}"
        except Exception as e:
            return f"Error analyzing text: {e}" 

    def _log_trailing_control_characters(self):
        """Log all detected trailing control characters to help improve detection."""
        control_chars = {}
        for section in self.text_sections:
            if hasattr(section, 'trailing_control') and section.trailing_control:
                for char in section.trailing_control:
                    # Skip common punctuation and whitespace
                    if char in self._excluded_control_chars:
                        continue
                    if char not in control_chars:
                        control_chars[char] = 0
                    control_chars[char] += 1
        
        if control_chars:
            print("\nDetected trailing control characters:")
            for char, count in control_chars.items():
                # Get hex representation
                hex_val = ord(char)
                print(f"  '{char}' (0x{hex_val:04x}) - {count} occurrences")
            print(f"Total unique control characters: {len(control_chars)}")
            
            # Update our known patterns with newly discovered control characters
            # This helps adapt the detection to the specific game's control codes
            for char in control_chars.keys():
                # Never add excluded characters or common punctuation
                if char not in self._excluded_control_chars and char not in self._known_control_chars:
                    self._known_control_chars.append(char)
                    print(f"Added '{char}' to known control characters") 