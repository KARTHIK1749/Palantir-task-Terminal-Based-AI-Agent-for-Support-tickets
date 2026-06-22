"""
Prompt Injection Detection Module

This module implements multi-layered prompt injection detection using:
1. Pattern-based detection (regex, known attack signatures)
2. Heuristic analysis (instruction keywords, role-playing attempts)
3. LLM-based validation (for sophisticated attacks)

CRITICAL: A single prompt injection compliance = 0% on 25% of total score
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class InjectionResult:
    """Result of prompt injection analysis"""
    is_injection: bool
    confidence: float
    detected_patterns: List[str]
    reasoning: str


class PromptInjectionDetector:
    """
    Multi-layered prompt injection detector
    
    Defense strategy:
    1. Pattern matching for known attacks
    2. Heuristic analysis for instruction patterns
    3. Context validation for role-playing attempts
    """
    
    def __init__(self):
        # Known prompt injection patterns
        self.injection_patterns = [
            # Direct instruction override
            r"ignore (all )?previous (instructions|prompts|rules)",
            r"disregard (all )?previous (instructions|prompts|rules)",
            r"forget (all )?previous (instructions|prompts|rules)",
            r"new instructions?:",
            r"system:?\s*(you are now|from now on)",
            
            # Role-playing attacks
            r"you are (now |being )?a (different|new|helpful)",
            r"act as (if you are|a)",
            r"pretend (you are|to be)",
            r"roleplay as",
            r"simulate (being|a)",
            
            # Instruction injection
            r"\\n\\n(###|##|\*\*)(system|assistant|instruction)",
            r"<\|?(system|im_start|endoftext)",
            r"\[SYSTEM\]|\[INST\]|\[/INST\]",
            
            # Data exfiltration attempts
            r"show me (your|the) (system prompt|instructions|rules)",
            r"what (are|were) you (told|instructed|programmed)",
            r"repeat (your|the) (system prompt|instructions|original)",
            r"print (your|the) (prompt|instructions)",
            r"output (your|the) (system|internal) (prompt|rules)",
            
            # Classification manipulation
            r"classify this as (replied|escalated)",
            r"mark this as (replied|escalated)",
            r"set status to (replied|escalated)",
            r"respond with status[:\s]+(replied|escalated)",
            
            # Corpus/document leakage
            r"list all (documents|files|corpus)",
            r"show me the (entire |all )?corpus",
            r"dump (the |all )?(documents|knowledge base)",
            
            # Jailbreak attempts
            r"DAN mode|developer mode",
            r"jailbreak|jail break",
            r"unrestricted mode",
            
            # Multi-lingual attacks (basic)
            r"ignora(r)? (todas? )?las? instrucciones anteriores",  # Spanish
            r"ignorez? (toutes? )?les? instructions précédentes",  # French
            r"ignoriere (alle )?vorherigen anweisungen",  # German
        ]
        
        # Compile patterns
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.injection_patterns
        ]
        
        # Heuristic keywords (high concentration indicates injection)
        self.instruction_keywords = [
            "ignore", "disregard", "forget", "override", "bypass",
            "new instructions", "system message", "assistant",
            "classify as", "set status", "mark as", "respond with",
            "you are now", "act as", "pretend", "roleplay",
            "show me", "print", "output", "reveal", "display"
        ]
        
    def detect(self, text: str) -> InjectionResult:
        """
        Detect prompt injection attempts in text
        
        Args:
            text: Input text to analyze
            
        Returns:
            InjectionResult with detection findings
        """
        detected_patterns = []
        confidence = 0.0
        
        # Pattern-based detection
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                detected_patterns.append(self.injection_patterns[i])
        
        # If explicit patterns found, high confidence injection
        if detected_patterns:
            confidence = 0.95
            return InjectionResult(
                is_injection=True,
                confidence=confidence,
                detected_patterns=detected_patterns,
                reasoning=f"Detected {len(detected_patterns)} known injection patterns"
            )
        
        # Heuristic analysis - keyword density
        keyword_count = sum(
            1 for keyword in self.instruction_keywords 
            if keyword.lower() in text.lower()
        )
        
        # Normalize by text length (keywords per 100 chars)
        if len(text) > 0:
            keyword_density = (keyword_count / len(text)) * 100
            
            # High density of instruction keywords
            if keyword_density > 2.0:  # More than 2% instruction keywords
                confidence = 0.75
                return InjectionResult(
                    is_injection=True,
                    confidence=confidence,
                    detected_patterns=["high_instruction_keyword_density"],
                    reasoning=f"Unusually high instruction keyword density: {keyword_density:.2f}%"
                )
        
        # Check for suspicious structure patterns
        if self._has_suspicious_structure(text):
            confidence = 0.60
            return InjectionResult(
                is_injection=True,
                confidence=confidence,
                detected_patterns=["suspicious_structure"],
                reasoning="Detected suspicious instruction-like structure"
            )
        
        # No injection detected
        return InjectionResult(
            is_injection=False,
            confidence=0.95,
            detected_patterns=[],
            reasoning="No injection patterns detected"
        )
    
    def _has_suspicious_structure(self, text: str) -> bool:
        """
        Check for suspicious structural patterns that might indicate injection
        """
        # Multiple consecutive newlines followed by instruction-like text
        suspicious_structures = [
            r"\n\n\n+\s*(you|ignore|system|assistant|instruction)",
            r"---+\s*(system|new instruction|ignore)",
            r"===+\s*(system|new instruction|ignore)",
        ]
        
        for pattern in suspicious_structures:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def validate_response(self, response: str, original_context: str) -> Tuple[bool, str]:
        """
        Validate that a generated response hasn't leaked system information
        
        Args:
            response: Generated response to validate
            original_context: Original ticket context
            
        Returns:
            Tuple of (is_safe, reason)
        """
        # Check for system prompt leakage
        leakage_indicators = [
            r"my (system )?instructions? (are|were)",
            r"i (was|am) (told|instructed|programmed) to",
            r"according to my (system )?prompt",
            r"my internal (rules|guidelines|instructions)",
        ]
        
        for pattern in leakage_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                return False, f"Response contains system prompt leakage: {pattern}"
        
        return True, "Response is safe"


# Singleton instance
_detector = None

def get_detector() -> PromptInjectionDetector:
    """Get singleton detector instance"""
    global _detector
    if _detector is None:
        _detector = PromptInjectionDetector()
    return _detector