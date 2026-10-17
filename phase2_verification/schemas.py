"""
Phase 2D Evidence-Grounded Hypothesis Verification Schemas
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_verification/schemas.py

Defines validated Pydantic models for:
1. VerificationStatus: Literals 'Supported', 'Unsupported', 'Insufficient Evidence'.
2. EvidenceClassification: Fine-grained evidence tiering.
3. VerificationFinding: Grounded per-document finding.
4. VerificationResult: Public verification evaluation response.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


VerificationStatus = Literal["Supported", "Unsupported", "Insufficient Evidence"]

EvidenceClassification = Literal[
    "direct",
    "indirect_resolved",
    "indirect_unresolved",
    "contradictory",
    "insufficient"
]


class VerificationFinding(BaseModel):
    """
    Structured factual finding extracted from a single cited evidence document.
    Every finding is strictly traceable to its cited doc_id.
    """
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(..., description="Validated corpus document ID")
    doc_type: str = Field(..., description="Evidence type: 'incident_report' or 'call_detail_record'")
    finding_type: str = Field(
        ...,
        description="Finding category: 'direct_incident_co_offending', 'direct_communication', "
                    "'alias_co_offending', 'alias_attribution', 'explicit_exclusion', "
                    "'independent_activity', or 'unrelated_evidence'"
    )
    entities_mentioned: List[str] = Field(default_factory=list, description="Canonical entity IDs (OID#xxxx) in document")
    aliases_mentioned: List[str] = Field(default_factory=list, description="Street monikers/aliases in document")
    summary: str = Field(..., description="Fact-level summary grounded in document text")


class VerificationResult(BaseModel):
    """
    Public, structured hypothesis verification evaluation response.
    Guaranteed free of internal metadata, provenance, ground-truth labels, or hidden vaults.
    """
    model_config = ConfigDict(extra="forbid")

    entity_a: str = Field(..., description="First subject in canonical format (e.g. OID#4418)")
    entity_b: str = Field(..., description="Second subject in canonical format (e.g. OID#8864)")
    status: VerificationStatus = Field(
        ...,
        description="Verification outcome: 'Supported', 'Unsupported', or 'Insufficient Evidence'"
    )
    evidence_class: EvidenceClassification = Field(
        ...,
        description="Evidential classification tier"
    )
    cited_evidence_ids: List[str] = Field(
        ...,
        description="List of validated document IDs evaluated in this verification"
    )
    rationale: str = Field(
        ...,
        description="Concise, evidence-grounded justification citing supporting documents"
    )
    findings: List[VerificationFinding] = Field(
        default_factory=list,
        description="Itemized, per-document evidential extractions"
    )
