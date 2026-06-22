"""
Document Loader Module

Loads and processes support documentation from the corpus.
Handles multiple formats: .md, .txt, .html
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class Document:
    """Represents a support document"""
    content: str
    source: str  # Relative path from repo root
    company: str  # devplatform, claude, visa
    title: str
    metadata: Dict


class DocumentLoader:
    """
    Loads support documentation from the data/ directory
    
    Supports:
    - Markdown (.md)
    - Plain text (.txt)
    - HTML (.html)
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.documents: List[Document] = []
        
    def load_all(self) -> List[Document]:
        """
        Load all documents from the corpus
        
        Returns:
            List of Document objects
        """
        if not self.data_dir.exists():
            raise ValueError(f"Data directory not found: {self.data_dir}")
        
        print(f"Loading documents from {self.data_dir}...")
        
        # Load from each company directory
        for company in ["devplatform", "claude", "visa"]:
            company_dir = self.data_dir / company
            if company_dir.exists():
                self._load_from_directory(company_dir, company)
        
        print(f"Loaded {len(self.documents)} documents")
        return self.documents
    
    def _load_from_directory(self, directory: Path, company: str):
        """Recursively load documents from a directory"""
        for file_path in directory.rglob("*"):
            if file_path.is_file() and self._is_valid_file(file_path):
                try:
                    doc = self._load_document(file_path, company)
                    if doc:
                        self.documents.append(doc)
                except Exception as e:
                    print(f"Warning: Failed to load {file_path}: {e}")
    
    def _is_valid_file(self, file_path: Path) -> bool:
        """Check if file should be loaded"""
        valid_extensions = {'.md', '.txt', '.html', '.htm'}
        return file_path.suffix.lower() in valid_extensions
    
    def _load_document(self, file_path: Path, company: str) -> Optional[Document]:
        """Load a single document"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                return None
            
            # Get relative path from data_dir parent (repo root)
            repo_root = self.data_dir.parent
            relative_path = str(file_path.relative_to(repo_root))
            
            # Extract title from content or filename
            title = self._extract_title(content, file_path)
            
            # Create metadata
            metadata = {
                'file_type': file_path.suffix,
                'file_size': len(content),
                'company': company,
            }
            
            return Document(
                content=content,
                source=relative_path,
                company=company,
                title=title,
                metadata=metadata
            )
        
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from document content or filename"""
        # Try to find markdown title
        md_title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if md_title_match:
            return md_title_match.group(1).strip()
        
        # Try HTML title
        html_title_match = re.search(r'<title>(.+?)</title>', content, re.IGNORECASE)
        if html_title_match:
            return html_title_match.group(1).strip()
        
        # Use filename
        return file_path.stem.replace('_', ' ').replace('-', ' ').title()
    
    def get_documents_by_company(self, company: str) -> List[Document]:
        """Get all documents for a specific company"""
        return [doc for doc in self.documents if doc.company == company]
    
    def get_document_by_source(self, source: str) -> Optional[Document]:
        """Get a document by its source path"""
        for doc in self.documents:
            if doc.source == source:
                return doc
        return None