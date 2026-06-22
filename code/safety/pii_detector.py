"""
PII Detection Module

Detects and handles Personally Identifiable Information including:
- Credit card numbers
- Social Security Numbers (SSN)
- Email addresses
- Phone numbers
- Physical addresses
- Account numbers

CRITICAL: Responses must NEVER echo back PII verbatim
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class PIIDetection:
    """Result of PII detection"""
    has_pii: bool
    pii_types: List[str]
    redacted_text: str
    confidence: float


class PIIDetector:
    """
    Multi-pattern PII detector
    
    Detects common PII patterns and provides redaction utilities
    """
    
    def __init__(self):
        # Credit card patterns (Visa, Mastercard, Amex, Discover)
        self.cc_patterns = [
            r'\b4[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{1,4}\b',  # Visa
            r'\b5[1-5][0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',  # Mastercard
            r'\b3[47][0-9]{2}[-\s]?[0-9]{6}[-\s]?[0-9]{5}\b',  # Amex
            r'\b6(?:011|5[0-9]{2})[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',  # Discover
        ]
        
        # SSN patterns
        self.ssn_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',
            r'\b\d{3}\s\d{2}\s\d{4}\b',
            r'\b\d{9}\b',  # 9 consecutive digits (careful - could be other numbers)
        ]
        
        # Email pattern
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Phone patterns (US and international)
        self.phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US: 123-456-7890
            r'\b\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b',  # US: (123) 456-7890
            r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',  # International
        ]
        
        # Address patterns (basic)
        self.address_patterns = [
            r'\b\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\b',
            r'\bP\.?O\.?\s+Box\s+\d+\b',
        ]
        
        # Account/ID numbers (generic)
        self.account_patterns = [
            r'\b(?:account|acct)[\s#:]*\d{6,}\b',
            r'\b(?:customer|member)[\s#:]*(?:id|number)[\s#:]*\d{6,}\b',
        ]
    
    def detect(self, text: str) -> PIIDetection:
        """
        Detect PII in text
        
        Args:
            text: Input text to scan
            
        Returns:
            PIIDetection with findings and redacted version
        """
        pii_types = []
        redacted = text
        has_pii = False
        
        # Check credit cards
        for pattern in self.cc_patterns:
            if re.search(pattern, text):
                pii_types.append("credit_card")
                redacted = re.sub(pattern, "[REDACTED_CC]", redacted)
                has_pii = True
        
        # Check SSN
        for pattern in self.ssn_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Verify it looks like SSN (not just any 9 digits)
                num = re.sub(r'[^0-9]', '', match.group())
                if len(num) == 9 and not num.startswith('000'):
                    pii_types.append("ssn")
                    redacted = redacted.replace(match.group(), "[REDACTED_SSN]")
                    has_pii = True
        
        # Check emails
        if re.search(self.email_pattern, text):
            pii_types.append("email")
            redacted = re.sub(self.email_pattern, "[REDACTED_EMAIL]", redacted)
            has_pii = True
        
        # Check phones
        for pattern in self.phone_patterns:
            if re.search(pattern, text):
                pii_types.append("phone")
                redacted = re.sub(pattern, "[REDACTED_PHONE]", redacted)
                has_pii = True
        
        # Check addresses
        for pattern in self.address_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                pii_types.append("address")
                redacted = re.sub(pattern, "[REDACTED_ADDRESS]", redacted, flags=re.IGNORECASE)
                has_pii = True
        
        # Check account numbers
        for pattern in self.account_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                pii_types.append("account_number")
                redacted = re.sub(pattern, "[REDACTED_ACCOUNT]", redacted, flags=re.IGNORECASE)
                has_pii = True
        
        # Remove duplicates
        pii_types = list(set(pii_types))
        
        confidence = 0.9 if has_pii else 0.95
        
        return PIIDetection(
            has_pii=has_pii,
            pii_types=pii_types,
            redacted_text=redacted,
            confidence=confidence
        )
    
    def get_safe_reference(self, text: str, pii_type: str) -> str:
        """
        Generate a safe reference to PII without exposing it
        
        Example: "4532123456789012" -> "card ending in 9012"
        """
        if pii_type == "credit_card":
            # Extract last 4 digits
            digits = re.sub(r'[^0-9]', '', text)
            if len(digits) >= 4:
                return f"card ending in {digits[-4:]}"
        
        elif pii_type == "phone":
            digits = re.sub(r'[^0-9]', '', text)
            if len(digits) >= 4:
                return f"phone ending in {digits[-4:]}"
        
        elif pii_type == "email":
            if "@" in text:
                domain = text.split("@")[1]
                return f"email address at {domain}"
        
        elif pii_type == "account_number":
            digits = re.sub(r'[^0-9]', '', text)
            if len(digits) >= 4:
                return f"account ending in {digits[-4:]}"
        
        return "the information provided"
    
    def redact_for_response(self, response: str, original_pii: List[str]) -> str:
        """
        Ensure response doesn't echo back PII from the ticket
        
        Args:
            response: Generated response
            original_pii: List of PII strings found in original ticket
            
        Returns:
            Redacted response
        """
        redacted = response
        
        for pii_item in original_pii:
            # Don't redact short strings (likely not actual PII)
            if len(pii_item) < 6:
                continue
            
            # Case-insensitive replacement
            if pii_item.lower() in redacted.lower():
                # Find actual case in response
                pattern = re.compile(re.escape(pii_item), re.IGNORECASE)
                redacted = pattern.sub("[REDACTED]", redacted)
        
        return redacted


# Singleton instance
_pii_detector = None

def get_pii_detector() -> PIIDetector:
    """Get singleton PII detector instance"""
    global _pii_detector
    if _pii_detector is None:
        _pii_detector = PIIDetector()
    return _pii_detector