"""
Main entry point for the MLE Hiring Challenge AI Support Triage Agent.
"""
import os
import csv
import json
import logging
from pathlib import Path
import sys
from dotenv import load_dotenv

# Ensure code is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from ingestion.document_loader import DocumentLoader
from retrieval.hybrid_retriever import HybridRetriever
from safety.injection_detector import get_detector
from safety.pii_detector import get_pii_detector
from agents.classifier_agent import ClassifierAgent
from agents.escalation_rules import EscalationRulesEngine
from agents.responder_agent import ResponderAgent
from safety.tool_validator import ToolValidator
from utils.language_detector import detect_language

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    repo_root = Path(__file__).parent.parent
    input_csv = repo_root / "support_tickets" / "support_tickets.csv"
    output_csv = repo_root / "support_tickets" / "output.csv"
    
    if not input_csv.exists():
        logging.error(f"Input CSV not found at {input_csv}")
        return

    # 1. Initialize Components
    logging.info("Initializing components...")
    doc_loader = DocumentLoader(str(repo_root / "data"))
    documents = doc_loader.load_all()
    
    retriever = HybridRetriever(documents)
    retriever.build_indices()
    
    injection_detector = get_detector()
    pii_detector = get_pii_detector()
    
    classifier = ClassifierAgent()
    escalation_rules = EscalationRulesEngine()
    responder = ResponderAgent()
    tool_validator = ToolValidator()

    # 2. Process Tickets
    results = []
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        tickets = list(reader)
        
    logging.info(f"Processing {len(tickets)} tickets...")
    
    for idx, row in enumerate(tickets, start=1):
        logging.info(f"Processing ticket {idx}/{len(tickets)}")
        
        # Support various CSV formats (capitalized vs lowercase)
        issue_raw = row.get("Issue", row.get("issue", ""))
        subject = row.get("Subject", row.get("subject", ""))
        company_raw = row.get("Company", row.get("company", ""))
        
        # Clean company filter
        company = company_raw.lower().strip()
        if company not in ["devplatform", "claude", "visa"]:
            company = None
            
        # Parse issue history
        try:
            history = json.loads(issue_raw)
            if isinstance(history, list) and len(history) > 0:
                # Use the latest message from the user
                ticket_text = ""
                for msg in reversed(history):
                    if msg.get("role") == "user":
                        ticket_text = msg.get("content", "")
                        break
                if not ticket_text:
                    ticket_text = issue_raw
            else:
                ticket_text = issue_raw
        except (json.JSONDecodeError, TypeError):
            ticket_text = issue_raw
            
        full_context = f"Subject: {subject}\n\nIssue: {ticket_text}"
        
        # Detect language
        language = detect_language(ticket_text)
        
        # Safety Layer
        injection_result = injection_detector.detect(full_context)
        pii_result = pii_detector.detect(full_context)
        
        # Classification
        classification = classifier.classify(full_context)
        
        # Retrieval
        retrieved_docs = []
        if not injection_result.is_injection and classification.request_type != "invalid":
            query = f"{classification.product_area} {subject} {ticket_text}"
            retrieved_tuples = retriever.retrieve(query, top_k=3, company_filter=company)
            for doc, score in retrieved_tuples:
                retrieved_docs.append({
                    "content": doc.content,
                    "metadata": {"source": doc.source}
                })
        
        # Escalation Decision
        decision = escalation_rules.evaluate(classification, injection_result, pii_result)
        
        # Responder
        response_gen = responder.generate_response(
            ticket_text=full_context,
            classification=classification,
            escalation=decision,
            retrieved_docs=retrieved_docs,
            pii_result=pii_result
        )
        
        # Output Validation
        valid_actions = tool_validator.validate_actions(response_gen.actions_taken)
        
        # Build CSV Row
        output_row = {
            "issue": row.get("Issue", row.get("issue", "")),
            "subject": subject,
            "company": company_raw,
            "status": decision.status,
            "product_area": classification.product_area,
            "response": response_gen.response,
            "justification": response_gen.justification,
            "request_type": classification.request_type,
            "confidence_score": str(classification.confidence_score),
            "source_documents": "|".join(response_gen.source_documents),
            "risk_level": decision.adjusted_risk,
            "pii_detected": "true" if pii_result.has_pii else "false",
            "language": language,
            "actions_taken": json.dumps(valid_actions)
        }
        
        results.append(output_row)
        
    # 3. Write Output
    logging.info("Writing results to output.csv...")
    expected_headers = [
        "issue", "subject", "company", "response", "product_area",
        "status", "request_type", "justification", "confidence_score",
        "source_documents", "risk_level", "pii_detected", "language",
        "actions_taken"
    ]
    
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=expected_headers)
        writer.writeheader()
        writer.writerows(results)
        
    logging.info("Pipeline completed successfully.")

if __name__ == "__main__":
    main()
