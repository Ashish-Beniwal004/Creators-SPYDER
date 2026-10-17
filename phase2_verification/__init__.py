"""
Phase 2D Evidence-Grounded Hypothesis Verification Package
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_verification/__init__.py

Exposes:
- search_evidence: Read-only lexical evidence retriever.
- verify_hypothesis: Read-only evidence-grounded hypothesis verifier.
- HypothesisVerifier: Engine class for hypothesis verification.
- VerificationResult, VerificationFinding, VerificationStatus, EvidenceClassification: Schemas.
- APPROVED_READONLY_TOOLS: Approved tool catalog for downstream agentic investigations.
"""

from phase2_retrieval import search_evidence, EvidenceRetriever
from phase2_verification.verifier import (
    verify_hypothesis,
    HypothesisVerifier,
    extract_document_facts,
)
from phase2_verification.schemas import (
    VerificationResult,
    VerificationFinding,
    VerificationStatus,
    EvidenceClassification,
)

APPROVED_READONLY_TOOLS = ("search_evidence", "verify_hypothesis")

__all__ = [
    "search_evidence",
    "verify_hypothesis",
    "EvidenceRetriever",
    "HypothesisVerifier",
    "VerificationResult",
    "VerificationFinding",
    "VerificationStatus",
    "EvidenceClassification",
    "APPROVED_READONLY_TOOLS",
    "extract_document_facts",
]
