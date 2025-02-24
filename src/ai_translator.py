from openai import OpenAI
from pathlib import Path
import json
import os
from typing import List, Optional

class AITranslator:
    CONFIG_FILE = Path.home() / ".dlg_editor" / "openai_config.json"

    def __init__(self):
        """Initialize the AI translator."""
        self.client = None
        self.load_api_key()

    def load_api_key(self) -> bool:
        """Load OpenAI API key from config file."""
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    api_key = config.get('api_key')
                    if api_key:
                        self.client = OpenAI(api_key=api_key)
                        return True
            return False
        except Exception:
            return False

    def save_api_key(self, api_key: str) -> bool:
        """Save OpenAI API key to config file."""
        try:
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump({'api_key': api_key}, f)
            self.client = OpenAI(api_key=api_key)
            return True
        except Exception:
            return False

    def translate_text(self, text: str, max_bytes: int, encoding: str = 'cp1251', context: Optional[List[str]] = None) -> str:
        """Translate text while respecting byte limit constraints."""
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        try:
            # Build context section if available
            context_section = ""
            if context:
                context_section = "\nDialog Context (for reference only):\n"
                for i, ctx in enumerate(context):
                    if ctx != text:
                        context_section += f"Section {i+1}: {ctx}\n"

            def validate_translation(trans: str) -> bool:
                """Validate that the translation meets our requirements."""
                # Allow basic Latin characters, punctuation, and proper quote handling
                allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ,.!?-'\"() ")
                if not all(c in allowed_chars for c in trans if c not in {'\n', '\r', '\t'}):
                    return False
                
                # Check that it looks like English (at least some common English words)
                english_markers = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'of', 'for', 'with', 'you', 'are', 'is', 'be'}
                words = set(trans.lower().split())
                if not any(marker in words for marker in english_markers):
                    return False
                    
                return True

            def get_initial_translation() -> str:
                """Get initial translation attempt."""
                prompt = f"""Translate this Russian/Cyrillic dialog text into natural, fluent English.
Keep the translation concise but maintain meaning.

Original Russian text: {text}{context_section}

CRITICAL REQUIREMENTS:
1. Output MUST be in ENGLISH only
2. Use ONLY basic Latin characters (a-z, A-Z) and standard punctuation
3. Maximum length: {max_bytes} bytes when encoded in {encoding}
4. NO Cyrillic or special characters allowed
5. Preserve core meaning and tone
6. Be as concise as possible while maintaining clarity
7. PRESERVE ALL QUOTATION MARKS exactly as they appear
8. DO NOT split sentences at quotation marks
9. Keep all punctuation in its original position

Translation approach:
1. First, identify any quoted text and preserve its structure
2. Translate while maintaining all quotes and punctuation
3. Keep sentences intact - don't break them up
4. If shortening is needed, preserve quotes and sentence structure

Translate to English:"""

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system", 
                            "content": """You are an expert English translator that:
1. ALWAYS translates TO ENGLISH
2. Uses only basic Latin characters
3. Translates concisely while maintaining meaning
4. Preserves essential dialog tone"""
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )

                return response.choices[0].message.content.strip()

            def shorten_translation(previous: str, current_bytes: int) -> str:
                """Request a shorter version of the translation."""
                prompt = f"""The previous translation is too long ({current_bytes} bytes, maximum {max_bytes}).
Please provide a shorter version while maintaining the core meaning.

Original Russian: {text}
Previous translation: {previous}

CRITICAL REQUIREMENTS:
1. Must be SHORTER than the previous translation
2. Keep essential meaning and tone
3. Use simpler words and shorter phrases
4. PRESERVE ALL QUOTATION MARKS and punctuation
5. DO NOT split sentences at quotation marks
6. Maximum {max_bytes} bytes when encoded in {encoding}
7. Use only basic Latin characters

Translation approach:
1. Keep all quotes and punctuation intact
2. Shorten by using more concise wording
3. Maintain sentence and quote structure
4. Only remove content if absolutely necessary

Provide shorter translation:"""

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at creating concise translations while preserving core meaning."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,  # Lower temperature for more focused output
                    max_tokens=150
                )

                return response.choices[0].message.content.strip()

            # Main translation loop
            max_attempts = 3
            current_attempt = 0
            current_translation = get_initial_translation()

            while current_attempt < max_attempts:
                if not validate_translation(current_translation):
                    if current_attempt == max_attempts - 1:
                        raise ValueError("Translation failed: Output is not valid English with Latin characters")
                    current_attempt += 1
                    current_translation = get_initial_translation()
                    continue

                encoded = current_translation.encode(encoding)
                if len(encoded) <= max_bytes:
                    return current_translation

                # If too long, immediately try to shorten it
                current_attempt += 1
                current_translation = shorten_translation(current_translation, len(encoded))

            raise ValueError(f"Failed to get translation within byte limit after {max_attempts} attempts")

        except Exception as e:
            raise ValueError(f"Translation failed: {str(e)}")

    def has_valid_key(self) -> bool:
        """Check if we have a valid OpenAI API key configured."""
        return self.client is not None 