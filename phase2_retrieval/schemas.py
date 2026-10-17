"""
Phase 2C Evidence Retrieval Response Schemas
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_retrieval/schemas.py

Defines validated Pydantic models for:
1. RetrievalResultItem (individual evidence search hit).
2. RetrievalResponse (structured retrieval response wrapper).
"""

from typing import List
from pydantic import BaseModel, Field, ConfigDict


class RetrievalResultItem(BaseModel):
    """
    Public, read-only search hit returned by the evidence retrieval layer.
    Exposes strictly approved evidence presentation fields.
    Guaranteed free of internal metadata, provenance, ground-truth labels, or rationales.
    """
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(..., description="Opaque document identifier matching ^(DOC_IR|CDR)_[0-9a-f]{8}$")
    doc_type: str = Field(..., description="Evidence type: 'incident_report' or 'call_detail_record'")
    text_content: str = Field(..., description="Retrievable textual evidence payload")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized lexical cosine similarity score")


class RetrievalResponse(BaseModel):
    """
    Structured query response envelope.
    """
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Input search query")
    top_k: int = Field(..., ge=1, le=50, description="Requested top_k cutoff")
    total_hits: int = Field(..., ge=0, description="Number of results returned with score > 0")
    results: List[RetrievalResultItem] = Field(default_factory=list, description="Ranked list of evidence items")
