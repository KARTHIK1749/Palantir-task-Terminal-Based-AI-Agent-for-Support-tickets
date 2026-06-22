"""
Language Detection Utility

Detects the primary language of text using character patterns and common words
"""

import re
from typing import Dict


class LanguageDetector:
    """
    Simple language detector for common languages
    
    Uses character patterns and common words to identify language
    """
    
    def __init__(self):
        # Common words by language (top 20 most frequent)
        self.common_words = {
            'en': {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
                   'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at'},
            'es': {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se',
                   'no', 'haber', 'por', 'con', 'su', 'para', 'como', 'estar', 'tener', 'le'},
            'fr': {'le', 'de', 'un', 'être', 'et', 'à', 'il', 'avoir', 'ne', 'je',
                   'son', 'que', 'se', 'qui', 'ce', 'dans', 'en', 'du', 'elle', 'au'},
            'de': {'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich',
                   'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht', 'ein', 'eine', 'als'},
            'pt': {'o', 'a', 'de', 'que', 'e', 'do', 'da', 'em', 'um', 'para',
                   'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais'},
            'it': {'il', 'di', 'e', 'la', 'che', 'per', 'un', 'in', 'è', 'a',
                   'non', 'una', 'da', 'le', 'si', 'come', 'dei', 'con', 'gli', 'del'},
            'zh': {'的', '一', '是', '不', '了', '在', '人', '有', '我', '他',
                   '这', '个', '们', '中', '来', '上', '大', '为', '和', '国'},
            'ja': {'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し',
                   'れ', 'さ', 'ある', 'いる', 'も', 'する', 'から', 'な', 'こと', 'として'},
            'hi': {'के', 'में', 'की', 'और', 'को', 'है', 'से', 'का', 'एक', 'पर',
                   'यह', 'कि', 'हैं', 'था', 'लिए', 'हो', 'गया', 'तक', 'साथ', 'करने'},
        }
        
        # Character ranges for script detection
        self.scripts = {
            'zh': (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            'ja': [(0x3040, 0x309F), (0x30A0, 0x30FF)],  # Hiragana, Katakana
            'hi': (0x0900, 0x097F),  # Devanagari
            'ar': (0x0600, 0x06FF),  # Arabic
            'ru': (0x0400, 0x04FF),  # Cyrillic
        }
    
    def detect(self, text: str) -> str:
        """
        Detect language of text
        
        Args:
            text: Input text
            
        Returns:
            ISO 639-1 language code (default: 'en')
        """
        if not text or not text.strip():
            return 'en'
        
        # Check script-based languages first
        script_lang = self._detect_by_script(text)
        if script_lang:
            return script_lang
        
        # For Latin-script languages, use word frequency
        return self._detect_by_words(text)
    
    def _detect_by_script(self, text: str) -> str:
        """Detect language by character script"""
        # Count characters in each script
        script_counts = {
            'zh': 0,
            'ja': 0,
            'hi': 0,
            'ar': 0,
            'ru': 0,
        }
        
        for char in text:
            code = ord(char)
            
            # Chinese
            if self.scripts['zh'][0] <= code <= self.scripts['zh'][1]:
                script_counts['zh'] += 1
            
            # Japanese
            for start, end in self.scripts['ja']:
                if start <= code <= end:
                    script_counts['ja'] += 1
                    break
            
            # Hindi
            if self.scripts['hi'][0] <= code <= self.scripts['hi'][1]:
                script_counts['hi'] += 1
            
            # Arabic
            if self.scripts['ar'][0] <= code <= self.scripts['ar'][1]:
                script_counts['ar'] += 1
            
            # Russian
            if self.scripts['ru'][0] <= code <= self.scripts['ru'][1]:
                script_counts['ru'] += 1
        
        # If any script has significant presence (>5%), return it
        total_chars = len(text)
        for lang, count in script_counts.items():
            if count / total_chars > 0.05:
                return lang
        
        return None
    
    def _detect_by_words(self, text: str) -> str:
        """Detect language by common words (for Latin-script languages)"""
        # Normalize text
        text_lower = text.lower()
        
        # Extract words (simple split)
        words = re.findall(r'\b[a-záéíóúàèìòùäëïöüñç]+\b', text_lower)
        
        if not words:
            return 'en'
        
        # Count matches for each language
        match_scores = {}
        for lang, common in self.common_words.items():
            matches = sum(1 for word in words if word in common)
            match_scores[lang] = matches / len(words)
        
        # Return language with highest match score
        if match_scores:
            best_lang = max(match_scores, key=match_scores.get)
            # Only return if confidence is reasonable (>5% match rate)
            if match_scores[best_lang] > 0.05:
                return best_lang
        
        # Default to English
        return 'en'


# Singleton
_detector = None

def get_language_detector() -> LanguageDetector:
    """Get singleton language detector"""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector


def detect_language(text: str) -> str:
    """Convenience function to detect language"""
    detector = get_language_detector()
    return detector.detect(text)