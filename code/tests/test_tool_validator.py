import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from safety.tool_validator import ToolValidator

@pytest.fixture
def validator():
    return ToolValidator()

def test_valid_action_is_kept(validator):
    actions = [
        {"action": "escalate_to_human", "parameters": {"priority": "high", "department": "billing", "summary": "needs help"}}
    ]
    validated = validator.validate_actions(actions)
    assert len(validated) == 1
    assert validated[0]["action"] == "escalate_to_human"

def test_hallucinated_tool_is_dropped(validator):
    actions = [
        {"action": "hack_mainframe", "parameters": {"target": "all"}}
    ]
    validated = validator.validate_actions(actions)
    assert len(validated) == 0

def test_missing_required_params_is_dropped(validator):
    actions = [
        {"action": "issue_refund", "parameters": {"amount": 50}} # Missing transaction_id and reason
    ]
    validated = validator.validate_actions(actions)
    assert len(validated) == 0

def test_mixed_actions(validator):
    actions = [
        {"action": "issue_refund", "parameters": {"transaction_id": "123", "amount": 50, "reason": "fraud"}},
        {"action": "fake_tool", "parameters": {}},
        {"action": "reset_password", "parameters": {"user_email": "test@test.com"}}
    ]
    validated = validator.validate_actions(actions)
    assert len(validated) == 2
    assert validated[0]["action"] == "issue_refund"
    assert validated[1]["action"] == "reset_password"
