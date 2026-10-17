"""
Phase 2C Evidence Retrieval Package
Project: Evidence-Grounded Agentic Criminal Network Investigation
Package: phase2_retrieval
"""

from phase2_retrieval.schemas import RetrievalResultItem, RetrievalResponse
from phase2_retrieval.retriever import (
    EvidenceRetriever,
    search_evidence,
    get_default_retriever,
    load_and_validate_corpus,
    evidence_tokenizer,
    DEFAULT_TOP_K,
    MAX_TOP_K,
    APPROVED_EVIDENCE_TYPES
)

__all__ = [
    "EvidenceRetriever",
    "search_evidence",
    "get_default_retriever",
    "load_and_validate_corpus",
    "evidence_tokenizer",
    "RetrievalResultItem",
    "RetrievalResponse",
    "DEFAULT_TOP_K",
    "MAX_TOP_K",
    "APPROVED_EVIDENCE_TYPES"
]
