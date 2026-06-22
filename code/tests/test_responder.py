import pytest
import sys
import os
import json
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.responder_agent import ResponderAgent, GenerationOutput
from agents.classifier_agent import TicketClassification
from agents.escalation_rules import EscalationDecision
from safety.pii_detector import PIIDetection

@pytest.fixture
def responder():
    agent = ResponderAgent()
    return agent

def test_generate_response_success(responder):
    expected_result = GenerationOutput(
        response="Here is how to reset your password.",
        justification="User asked for password reset.",
        source_documents=["data/devplatform/auth.md"],
        actions_taken=[]
    )
    classification = TicketClassification(
        request_type="product_issue", product_area="auth", risk_level="low", confidence_score=0.9, reasoning=""
    )
    escalation = EscalationDecision(status="replied", reason="Safe", adjusted_risk="low")
    pii = PIIDetection(has_pii=False, pii_types=[], redacted_text="", confidence=0.9)
    docs = [{"content": "Reset password by...", "metadata": {"source": "data/devplatform/auth.md"}}]
    
    with patch('langchain_core.runnables.RunnableSequence.invoke', return_value=expected_result):
        output = responder.generate_response("How to reset password?", classification, escalation, docs, pii)
        assert "password" in output.response
        assert output.source_documents == ["data/devplatform/auth.md"]

def test_generate_response_pii_redaction(responder):
    # LLM accidentally leaks PII
    expected_result = GenerationOutput(
        response="I checked your card 4111111111111111.",
        justification="Checking card.",
        source_documents=[],
        actions_taken=[]
    )
    classification = TicketClassification(
        request_type="bug", product_area="billing", risk_level="low", confidence_score=0.9, reasoning=""
    )
    escalation = EscalationDecision(status="replied", reason="Safe", adjusted_risk="low")
    pii = PIIDetection(has_pii=False, pii_types=[], redacted_text="", confidence=0.9)
    
    with patch('langchain_core.runnables.RunnableSequence.invoke', return_value=expected_result):
        output = responder.generate_response("My card is 4111111111111111.", classification, escalation, [], pii)
        assert "[REDACTED_CC]" in output.response
        assert "4111111111111111" not in output.response

def test_generate_response_api_failure(responder):
    classification = TicketClassification(
        request_type="bug", product_area="billing", risk_level="low", confidence_score=0.9, reasoning=""
    )
    escalation = EscalationDecision(status="replied", reason="Safe", adjusted_risk="low")
    pii = PIIDetection(has_pii=False, pii_types=[], redacted_text="", confidence=0.9)
    
    with patch('langchain_core.runnables.RunnableSequence.invoke', side_effect=Exception("API Error")):
        output = responder.generate_response("Help", classification, escalation, [], pii)
        assert "We have received your request" in output.response
        assert output.actions_taken[0]["action"] == "escalate_to_human"
