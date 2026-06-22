import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import json
from langchain_core.messages import AIMessage
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.classifier_agent import ClassifierAgent, TicketClassification

@pytest.fixture
def classifier():
    agent = ClassifierAgent()
    return agent

def test_empty_ticket(classifier):
    result = classifier.classify("")
    assert result.request_type == "invalid"
    assert result.product_area == "none"
    assert result.risk_level == "low"

def test_classify_success(classifier):
    expected_result = TicketClassification(
        request_type="bug",
        product_area="login",
        risk_level="medium",
        confidence_score=0.9,
        reasoning="User cannot login"
    )
    with patch('langchain_core.runnables.RunnableSequence.invoke', return_value=expected_result):
        result = classifier.classify("I cannot login to my account.")
        assert result.request_type == "bug"
        assert result.product_area == "login"
        assert result.risk_level == "medium"
        assert result.confidence_score == 0.9

def test_classify_api_failure(classifier):
    with patch('langchain_core.runnables.RunnableSequence.invoke', side_effect=Exception("API Error")):
        result = classifier.classify("Help me")
        assert result.request_type == "invalid"
        assert result.product_area == "error"
        assert result.risk_level == "high"
        assert result.confidence_score == 0.0
