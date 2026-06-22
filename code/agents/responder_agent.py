"""
Responder Agent Module

Generates the final response, justification, tool calls, and source citations.
Enforces safety, corpus grounding, and strict JSON outputs.
"""
import os
import json
from typing import List, Dict
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

try:
    from agents.classifier_agent import TicketClassification
    from agents.escalation_rules import EscalationDecision
    from safety.pii_detector import PIIDetection, get_pii_detector
except ImportError:
    from code.agents.classifier_agent import TicketClassification
    from code.agents.escalation_rules import EscalationDecision
    from code.safety.pii_detector import PIIDetection, get_pii_detector

class GenerationOutput(BaseModel):
    response: str = Field(description="User-facing response grounded in corpus or safe escalation message.")
    justification: str = Field(description="Explanation of why this response and actions were chosen.")
    source_documents: List[str] = Field(description="List of file paths of corpus documents used. Empty if none used.")
    actions_taken: List[dict] = Field(description="List of JSON tool calls. Empty array if none.")

class ResponderAgent:
    """
    Agent responsible for generating the final ticket response and tool actions.
    """
    def __init__(self, model_name: str = "llama3-70b-8192", temperature: float = 0.0):
        api_key = os.environ.get("GROQ_API_KEY", "dummy_key_for_tests")
        self.llm = ChatGroq(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            max_retries=2
        )
        self.parser = PydanticOutputParser(pydantic_object=GenerationOutput)
        self.pii_detector = get_pii_detector()
        self.tools_schema = self._load_tools_schema()
        
        from prompts.responder_prompts import RESPONDER_SYSTEM_PROMPT, RESPONDER_HUMAN_PROMPT
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", RESPONDER_SYSTEM_PROMPT),
            ("human", RESPONDER_HUMAN_PROMPT)
        ])
        
        self.chain = self.prompt | self.llm | self.parser
        
    def _load_tools_schema(self) -> str:
        # Load from data/api_specs/internal_tools.json
        tools_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "api_specs", "internal_tools.json")
        try:
            with open(tools_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return "[]"
            
    def generate_response(
        self,
        ticket_text: str,
        classification: TicketClassification,
        escalation: EscalationDecision,
        retrieved_docs: List[Dict],
        pii_result: PIIDetection
    ) -> GenerationOutput:
        
        # Format documents
        docs_str = ""
        for doc in retrieved_docs:
            source = doc.get("metadata", {}).get("source", "unknown")
            content = doc.get("content", "")
            docs_str += f"\n--- Source: {source} ---\n{content}\n"
            
        if not docs_str:
            docs_str = "No relevant documents found."
            
        try:
            output = self.chain.invoke({
                "ticket_text": ticket_text,
                "request_type": classification.request_type,
                "product_area": classification.product_area,
                "status": escalation.status,
                "reason": escalation.reason,
                "documents": docs_str,
                "tools_json": self.tools_schema,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Post-processing: Apply PII redaction to the response text to ensure safety
            response_pii = self.pii_detector.detect(output.response)
            if response_pii.has_pii:
                output.response = response_pii.redacted_text
                
            return output
            
        except Exception as e:
            # Fallback safe response
            return GenerationOutput(
                response="We have received your request and a support agent will review it shortly.",
                justification=f"Fallback triggered due to generation error: {str(e)}",
                source_documents=[],
                actions_taken=[{"action": "escalate_to_human", "parameters": {"priority": "high", "department": "general", "summary": "Generation failed."}}]
            )
