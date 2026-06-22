"""
Hybrid Retrieval Module

Combines dense vector search (FAISS) with sparse keyword search (BM25)
for robust document retrieval.

Strategy:
1. Vector search finds semantically similar documents
2. BM25 finds keyword-matching documents
3. Results are combined and re-ranked
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np

# Vector search
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS or sentence-transformers not available")

# Keyword search
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("Warning: rank-bm25 not available")

from ingestion.document_loader import Document, DocumentLoader


class HybridRetriever:
    """
    Hybrid retrieval combining vector and keyword search
    
    Components:
    - Dense retrieval: sentence-transformers + FAISS
    - Sparse retrieval: BM25
    - Fusion: Reciprocal Rank Fusion (RRF)
    """
    
    def __init__(
        self,
        documents: List[Document],
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: str = "code/.cache"
    ):
        self.documents = documents
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings model (lightweight and fast)
        if FAISS_AVAILABLE:
            print(f"Loading embedding model: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        else:
            self.embedding_model = None
            self.embedding_dim = 384  # Default dimension
        
        # Initialize indices
        self.faiss_index = None
        self.bm25_index = None
        self.doc_texts = [doc.content for doc in documents]
        
    def build_indices(self, force_rebuild: bool = False):
        """
        Build or load FAISS and BM25 indices
        
        Args:
            force_rebuild: If True, rebuild even if cache exists
        """
        faiss_cache = self.cache_dir / "faiss_index.bin"
        embeddings_cache = self.cache_dir / "embeddings.pkl"
        bm25_cache = self.cache_dir / "bm25_index.pkl"
        
        # Build FAISS index
        if FAISS_AVAILABLE:
            if not force_rebuild and faiss_cache.exists() and embeddings_cache.exists():
                print("Loading cached FAISS index...")
                self.faiss_index = faiss.read_index(str(faiss_cache))
                with open(embeddings_cache, 'rb') as f:
                    _ = pickle.load(f)  # embeddings stored but not needed after indexing
            else:
                print("Building FAISS index...")
                embeddings = self._compute_embeddings(self.doc_texts)
                
                # Create FAISS index (IndexFlatIP for cosine similarity)
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
                
                # Normalize embeddings for cosine similarity
                faiss.normalize_L2(embeddings)
                self.faiss_index.add(embeddings)
                
                # Cache
                faiss.write_index(self.faiss_index, str(faiss_cache))
                with open(embeddings_cache, 'wb') as f:
                    pickle.dump(embeddings, f)
                
                print(f"FAISS index built with {len(self.documents)} documents")
        
        # Build BM25 index
        if BM25_AVAILABLE:
            if not force_rebuild and bm25_cache.exists():
                print("Loading cached BM25 index...")
                with open(bm25_cache, 'rb') as f:
                    self.bm25_index = pickle.load(f)
            else:
                print("Building BM25 index...")
                # Tokenize documents (simple split - could use spacy for better results)
                tokenized_docs = [doc.lower().split() for doc in self.doc_texts]
                self.bm25_index = BM25Okapi(tokenized_docs)
                
                # Cache
                with open(bm25_cache, 'wb') as f:
                    pickle.dump(self.bm25_index, f)
                
                print(f"BM25 index built with {len(self.documents)} documents")
    
    def _compute_embeddings(self, texts: List[str]) -> np.ndarray:
        """Compute embeddings for a list of texts"""
        if not self.embedding_model:
            raise RuntimeError("Embedding model not available")
        
        # Batch encode for efficiency
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32,
            convert_to_numpy=True
        )
        return embeddings.astype('float32')
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        company_filter: Optional[str] = None,
        alpha: float = 0.5
    ) -> List[Tuple[Document, float]]:
        """
        Retrieve relevant documents using hybrid search
        
        Args:
            query: Search query
            top_k: Number of documents to retrieve
            company_filter: Optional company filter (devplatform, claude, visa)
            alpha: Weight for vector search (1-alpha for BM25). 0.5 = equal weight
            
        Returns:
            List of (Document, score) tuples, sorted by relevance
        """
        # Get candidates from both retrievers
        vector_results = self._vector_search(query, top_k * 2, company_filter)
        bm25_results = self._bm25_search(query, top_k * 2, company_filter)
        
        # Reciprocal Rank Fusion
        fused_scores = self._reciprocal_rank_fusion(
            vector_results,
            bm25_results,
            alpha=alpha
        )
        
        # Sort by fused score
        sorted_results = sorted(
            fused_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return [(self.documents[idx], score) for idx, score in sorted_results]
    
    def _vector_search(
        self,
        query: str,
        top_k: int,
        company_filter: Optional[str] = None
    ) -> List[Tuple[int, float]]:
        """Vector similarity search using FAISS"""
        if not FAISS_AVAILABLE or self.faiss_index is None:
            return []
        
        # Encode query
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        k = min(top_k * 3, len(self.documents))  # Over-retrieve for filtering
        distances, indices = self.faiss_index.search(query_embedding, k)
        
        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx >= 0:  # Valid index
                if company_filter is None or self.documents[idx].company == company_filter:
                    results.append((int(idx), float(score)))
                    if len(results) >= top_k:
                        break
        
        return results
    
    def _bm25_search(
        self,
        query: str,
        top_k: int,
        company_filter: Optional[str] = None
    ) -> List[Tuple[int, float]]:
        """Keyword search using BM25"""
        if not BM25_AVAILABLE or self.bm25_index is None:
            return []
        
        # Tokenize query
        query_tokens = query.lower().split()
        
        # Get scores for all documents
        scores = self.bm25_index.get_scores(query_tokens)
        
        # Sort by score
        scored_indices = [
            (idx, score) for idx, score in enumerate(scores)
            if company_filter is None or self.documents[idx].company == company_filter
        ]
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        
        return scored_indices[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[int, float]],
        bm25_results: List[Tuple[int, float]],
        alpha: float = 0.5,
        k: int = 60
    ) -> Dict[int, float]:
        """
        Combine results using Reciprocal Rank Fusion
        
        RRF formula: score(d) = sum(1 / (k + rank(d)))
        """
        fused_scores = {}
        
        # Add vector search scores
        for rank, (doc_idx, score) in enumerate(vector_results, start=1):
            rrf_score = alpha * (1.0 / (k + rank))
            fused_scores[doc_idx] = fused_scores.get(doc_idx, 0.0) + rrf_score
        
        # Add BM25 scores
        for rank, (doc_idx, score) in enumerate(bm25_results, start=1):
            rrf_score = (1 - alpha) * (1.0 / (k + rank))
            fused_scores[doc_idx] = fused_scores.get(doc_idx, 0.0) + rrf_score
        
        return fused_scores
    
    def get_document_by_source(self, source: str) -> Optional[Document]:
        """Retrieve a document by its source path"""
        for doc in self.documents:
            if doc.source == source:
                return doc
        return None