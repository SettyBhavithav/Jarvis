"""
JARVIS V2 - Automatic Memory Extraction
Analyzes conversational turns to automatically identify personal facts, preferences, habits, and tasks.
"""
import re
from typing import Optional, Dict, Any
from core.schemas import MemoryCategory

class MemoryExtractor:
    def extract_candidate(self, text: str) -> Optional[Dict[str, Any]]:
        text_lower = text.lower().strip()

        # Explicit commands: "remember that...", "memorize..."
        explicit_match = re.search(r"(?:remember|memorize|save)\s+(?:that\s+)?(.*)", text, re.IGNORECASE)
        if explicit_match:
            fact = explicit_match.group(1).strip()
            return {
                "text": fact,
                "category": MemoryCategory.GENERAL,
                "importance": 0.8
            }

        # User Preferences: "my favorite...", "i prefer...", "i like..."
        pref_match = re.search(r"(?:my favorite|i prefer|i like|i love|i always use)\s+(.*)", text, re.IGNORECASE)
        if pref_match:
            return {
                "text": text.strip(),
                "category": MemoryCategory.PREFERENCE,
                "importance": 0.7
            }

        # Project facts: "i am working on...", "my project is..."
        proj_match = re.search(r"(?:i am working on|my project is|we are building)\s+(.*)", text, re.IGNORECASE)
        if proj_match:
            return {
                "text": text.strip(),
                "category": MemoryCategory.PROJECT,
                "importance": 0.75
            }

        return None

# Global Extractor Singleton
memory_extractor = MemoryExtractor()
