import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.escalation_rules import EscalationRulesEngine, EscalationDecision
from agents.classifier_agent import TicketClassification
from safety.injection_detector import InjectionResult
from safety.pii_detector import PIIDetection

@pytest.fixture
def engine():
    return EscalationRulesEngine()

def test_safe_ticket_is_replied(engine):
    classification = TicketClassification(
        request_type="bug", product_area="login", risk_level="low", confidence_score=0.9, reasoning=""
    )
    injection = InjectionResult(is_injection=False, confidence=0.9, detected_patterns=[], reasoning="")
    pii = PIIDetection(has_pii=False, pii_types=[], redacted_text="", confidence=0.9)
    
    decision = engine.evaluate(classification, injection, pii)
    assert decision.status == "replied"
    assert decision.adjusted_risk == "low"

def test_injection_is_escalated(engine):
    classification = TicketClassification(
        request_type="feature_request", product_area="login", risk_level="low", confidence_score=0.9, reasoning=""
    )
    injection = InjectionResult(is_injection=True, confidence=0.9, detected_patterns=["ignore previous"], reasoning="Inject")
    pii = PIIDetection(has_pii=False, pii_types=[], redacted_text="", confidence=0.9)
    
    decision = engine.evaluate(classification, injection, pii)
    assert decision.status == "escalated"
    assert decision.adjusted_risk == "critical"
    assert "Prompt injection" in decision.reason

def test_high_risk_is_escalated(engine):
    classification = TicketClassification(
        request_type="bug", product_area="login", risk_level="high", confidence_score=0.9, reasoning=""
    )
    injection = InjectionResult(is_injection=False, confidence=0.9, detected_patterns=[], reasoning="")
    pii = PIIDetection(has_pii=False, pii_types=[], redacted_text="", confidence=0.9)
    
    decision = engine.evaluate(classification, injection, pii)
    assert decision.status == "escalated"
    assert decision.adjusted_risk == "high"

def test_sensitive_pii_is_escalated(engine):
    classification = TicketClassification(
        request_type="bug", product_area="login", risk_level="medium", confidence_score=0.9, reasoning=""
    )
    injection = InjectionResult(is_injection=False, confidence=0.9, detected_patterns=[], reasoning="")
    pii = PIIDetection(has_pii=True, pii_types=["ssn", "email"], redacted_text="", confidence=0.9)
    
    decision = engine.evaluate(classification, injection, pii)
    assert decision.status == "escalated"
    assert decision.adjusted_risk == "high"
    assert "SSN" in decision.reason

def test_low_confidence_is_escalated(engine):
    classification = TicketClassification(
        request_type="bug", product_area="login", risk_level="medium", confidence_score=0.4, reasoning=""
    )
    injection = InjectionResult(is_injection=False, confidence=0.9, detected_patterns=[], reasoning="")
    pii = PIIDetection(has_pii=False, pii_types=[], redacted_text="", confidence=0.9)
    
    decision = engine.evaluate(classification, injection, pii)
    assert decision.status == "escalated"
    assert decision.adjusted_risk == "medium"
    assert "confidence" in decision.reason
