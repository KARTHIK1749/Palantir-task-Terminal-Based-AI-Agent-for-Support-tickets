"""
Classifier Agent Module

Responsible for classifying incoming support tickets:
- product_area
- request_type
- risk_level

Uses deterministic generation with JSON schema validation.
"""

import os
from typing import Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


class TicketClassification(BaseModel):
    """Schema for ticket classification"""
    request_type: Literal["product_issue", "feature_request", "bug", "invalid"] = Field(
        description="Classification of the request type"
    )
    product_area: str = Field(
        description="Most relevant support category or domain area (e.g., 'billing', 'login', 'API', 'dashboard', 'unknown')"
    )
    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        description="Risk assessment of the ticket"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the classification (0.0 to 1.0)"
    )
    reasoning: str = Field(
        description="Brief explanation of the decision"
    )


class ClassifierAgent:
    """
    Agent responsible for deterministic ticket classification.
    """
    def __init__(self, model_name: str = "llama3-70b-8192", temperature: float = 0.0):
        # Determine API key
        api_key = os.environ.get("GROQ_API_KEY", "dummy_key_for_tests")
            
        self.llm = ChatGroq(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            max_retries=2
        )
        self.parser = PydanticOutputParser(pydantic_object=TicketClassification)
        
        from prompts.classifier_prompts import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_HUMAN_PROMPT
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", CLASSIFIER_SYSTEM_PROMPT),
            ("human", CLASSIFIER_HUMAN_PROMPT)
        ])
        
        self.chain = self.prompt | self.llm | self.parser
        
    def classify(self, ticket_text: str) -> TicketClassification:
        """
        Classifies the given ticket text.
        
        Args:
            ticket_text: The content of the support ticket
            
        Returns:
            TicketClassification object
        """
        if not ticket_text or not ticket_text.strip():
            return TicketClassification(
                request_type="invalid",
                product_area="none",
                risk_level="low",
                confidence_score=1.0,
                reasoning="Empty ticket text"
            )
            
        try:
            return self.chain.invoke({
                "ticket_text": ticket_text,
                "format_instructions": self.parser.get_format_instructions()
            })
        except Exception as e:
            # Fallback for API failures or parsing errors (safety first)
            return TicketClassification(
                request_type="invalid",
                product_area="error",
                risk_level="high",
                confidence_score=0.0,
                reasoning=f"Classification failed due to error: {str(e)}"
            )
