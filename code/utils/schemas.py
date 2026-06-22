"""
Output Schema Validation

Defines and validates the output schema for support ticket responses
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
import json


class TicketResponse(BaseModel):
    """
    Complete output schema for a single ticket
    
    Matches the required output columns in output.csv
    """
    # Primary outputs
    status: Literal["replied", "escalated"] = Field(
        description="Whether to reply directly or escalate to human"
    )
    product_area: str = Field(
        description="Most relevant support category or domain area"
    )
    response: str = Field(
        description="User-facing answer grounded in support corpus"
    )
    justification: str = Field(
        description="Explanation of the decision and response"
    )
    request_type: Literal["product_issue", "feature_request", "bug", "invalid"] = Field(
        description="Classification of the request type"
    )
    
    # Extended outputs
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the response (0.0 to 1.0)"
    )
    source_documents: str = Field(
        default="",
        description="Pipe-separated file paths of corpus documents used"
    )
    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        description="Risk assessment of the ticket"
    )
    pii_detected: bool = Field(
        description="Whether PII was detected in the ticket"
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 language code (e.g., en, fr, es)"
    )
    actions_taken: str = Field(
        default="[]",
        description="JSON array of API tool calls"
    )
    
    @field_validator('actions_taken')
    @classmethod
    def validate_actions_json(cls, v):
        """Ensure actions_taken is valid JSON"""
        if not v:
            return "[]"
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError("actions_taken must be a JSON array")
            return v
        except json.JSONDecodeError:
            raise ValueError("actions_taken must be valid JSON")
    
    @field_validator('source_documents')
    @classmethod
    def validate_source_documents(cls, v):
        """Ensure source documents are pipe-separated or empty"""
        if not v:
            return ""
        # Check that paths don't contain invalid characters
        if "|" in v:
            paths = v.split("|")
            for path in paths:
                if not path.strip():
                    raise ValueError("Empty path in source_documents")
        return v
    
    def to_csv_row(self) -> dict:
        """Convert to CSV row format"""
        return {
            'status': self.status,
            'product_area': self.product_area,
            'response': self.response,
            'justification': self.justification,
            'request_type': self.request_type,
            'confidence_score': self.confidence_score,
            'source_documents': self.source_documents,
            'risk_level': self.risk_level,
            'pii_detected': self.pii_detected,
            'language': self.language,
            'actions_taken': self.actions_taken,
        }


class ToolCall(BaseModel):
    """
    Represents a single tool/action call
    
    Must match schema in data/api_specs/internal_tools.json
    """
    action: str = Field(description="Tool name")
    parameters: dict = Field(default_factory=dict, description="Tool parameters")
    
    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "parameters": self.parameters
        }


def validate_output(response: TicketResponse) -> tuple[bool, Optional[str]]:
    """
    Validate a ticket response
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # Pydantic validation happens automatically
        # Additional custom validations
        
        # Check response is not empty
        if not response.response.strip():
            return False, "Response cannot be empty"
        
        # Check justification is not empty
        if not response.justification.strip():
            return False, "Justification cannot be empty"
        
        # Check confidence is reasonable
        if response.confidence_score == 0.0:
            return False, "Confidence score cannot be exactly 0.0"
        
        # Validate actions_taken is proper JSON
        try:
            actions = json.loads(response.actions_taken)
            if not isinstance(actions, list):
                return False, "actions_taken must be a JSON array"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in actions_taken: {e}"
        
        return True, None
    
    except Exception as e:
        return False, str(e)