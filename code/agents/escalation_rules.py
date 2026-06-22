"""
Escalation Rules Module

Deterministic rule-based engine to decide whether a ticket should be escalated to a human.
Applies business logic combining classification, safety signals, and PII detection.
"""

from typing import Literal
from dataclasses import dataclass

# Assuming these are available in the python path
try:
    from agents.classifier_agent import TicketClassification
    from safety.injection_detector import InjectionResult
    from safety.pii_detector import PIIDetection
except ImportError:
    from code.agents.classifier_agent import TicketClassification
    from code.safety.injection_detector import InjectionResult
    from code.safety.pii_detector import PIIDetection

@dataclass
class EscalationDecision:
    status: Literal["replied", "escalated"]
    reason: str
    adjusted_risk: Literal["low", "medium", "high", "critical"]

class EscalationRulesEngine:
    """
    Evaluates whether a support ticket must be escalated.
    """
    
    def __init__(self, min_confidence_threshold: float = 0.6):
        self.min_confidence_threshold = min_confidence_threshold
        
    def evaluate(
        self, 
        classification: TicketClassification, 
        injection_result: InjectionResult,
        pii_result: PIIDetection
    ) -> EscalationDecision:
        """
        Evaluate inputs and return deterministic escalation decision.
        """
        
        # 1. Safety First: Prompt injections are immediately escalated
        if injection_result.is_injection:
            return EscalationDecision(
                status="escalated",
                reason=f"Security alert: Prompt injection detected ({injection_result.reasoning}).",
                adjusted_risk="critical"
            )
            
        # 2. Request Type Rules
        if classification.request_type == "invalid":
            return EscalationDecision(
                status="escalated",
                reason="Ticket classified as invalid or nonsensical.",
                adjusted_risk="high" if classification.risk_level in ["low", "medium"] else classification.risk_level
            )
            
        # 3. Risk Level Overrides
        if classification.risk_level in ["critical", "high"]:
            return EscalationDecision(
                status="escalated",
                reason=f"High risk ticket ({classification.risk_level}). Human review required.",
                adjusted_risk=classification.risk_level
            )
            
        # 4. Confidence Threshold
        if classification.confidence_score < self.min_confidence_threshold:
            return EscalationDecision(
                status="escalated",
                reason=f"Classification confidence ({classification.confidence_score}) below threshold ({self.min_confidence_threshold}).",
                adjusted_risk=classification.risk_level
            )
            
        # 5. PII handling (e.g., if SSN is detected, maybe escalate to specialized team)
        # Assuming SSN or credit card might require human escalation, though we redact it
        if "ssn" in pii_result.pii_types or "credit_card" in pii_result.pii_types:
            return EscalationDecision(
                status="escalated",
                reason="Highly sensitive PII (SSN or Credit Card) detected.",
                adjusted_risk="high"
            )
            
        # Default: Reply automatically
        return EscalationDecision(
            status="replied",
            reason="Ticket is safe and eligible for automated response.",
            adjusted_risk=classification.risk_level
        )
