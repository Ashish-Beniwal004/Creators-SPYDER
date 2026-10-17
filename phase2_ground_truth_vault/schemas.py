"""
Phase 2A Data and Evidence Schemas
Project: Evidence-Grounded Agentic Criminal Network Investigation
Vault: phase2_ground_truth_vault/

Defines validated Pydantic models for:
1. Ground Truth and Manifest structures (internal vault).
2. Police Incident Reports and Call Detail Records (synthetic evidence).
3. Provenance tracking vs. Retrieval-facing sanitization models.
"""

import re
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ==============================================================================
# 1. GROUND TRUTH & MANIFEST SCHEMAS (INTERNAL VAULT ONLY)
# ==============================================================================

class GroundTruthCase(BaseModel):
    """
    Definitive evaluation ground-truth record for a single case pair.
    QUARANTINED: Must NEVER be indexed in retrieval search space or passed to evaluated agents.
    """
    case_id: str = Field(..., description="Unique case identifier (e.g. PILOT_CASE_01)")
    target_pair: Tuple[str, str] = Field(..., description="Canonical sorted entity tuple (OID#xxx, OID#yyy)")
    label: int = Field(..., ge=0, le=1, description="1 if documented co-offenders, 0 if no shared crime in window")
    condition: str = Field(..., description="Evaluation condition (clean_evidence, alias_ambiguity, missing_evidence, distractors, mixed_difficulty)")
    shared_crime_ids: List[str] = Field(default_factory=list, description="Authentic CIDs where suspects co-offended")
    components: Tuple[int, int] = Field(..., description="Component IDs of target entities in the partition")
    spatial_distance: float = Field(..., ge=0.0, description="Euclidean distance between mean incident coordinates")
    temporal_overlap: List[str] = Field(default_factory=list, description="Shared active calendar months (YYYY-MM)")
    factual_rationale: str = Field(..., description="Detailed factual explanation from police records")
    epistemic_limitation: str = Field(..., description="Formal closed-world assumption disclaimer")

    @field_validator("target_pair")
    @classmethod
    def validate_sorted_pair(cls, v: Tuple[str, str]) -> Tuple[str, str]:
        if v[0] == v[1]:
            raise ValueError(f"Self-loops forbidden: {v}")
        if v[0] > v[1]:
            raise ValueError(f"Target pair must be canonically sorted: {v}")
        return v

    @model_validator(mode="after")
    def validate_label_consistency(self) -> "GroundTruthCase":
        if self.label == 1 and not self.shared_crime_ids:
            raise ValueError(f"Positive case {self.case_id} must have at least one shared crime ID.")
        if self.label == 0 and self.shared_crime_ids:
            raise ValueError(f"Negative case {self.case_id} cannot have shared crime IDs.")
        return self


class PilotManifest(BaseModel):
    """Complete frozen manifest of the 10 pilot evaluation cases."""
    pilot_version: str = Field(default="1.0")
    random_seed: int = Field(default=42)
    source_dataset: str = Field(default="israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")
    total_cases: int = Field(default=10)
    positive_cases_count: int = Field(default=5)
    negative_cases_count: int = Field(default=5)
    cases: List[GroundTruthCase]


class TestManifest(BaseModel):
    """Complete frozen manifest of the 200 test evaluation cases."""
    manifest_version: str = Field(default="1.0")
    random_seed: int = Field(default=42)
    source_dataset: str = Field(default="israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")
    total_cases: int = Field(default=200)
    positive_cases_count: int = Field(default=100)
    negative_cases_count: int = Field(default=100)
    cases: List[GroundTruthCase]



# ==============================================================================
# 2. EVIDENCE SCHEMAS (SYNTHETIC RECORD LAYER)
# ==============================================================================

class PoliceIncidentReport(BaseModel):
    """
    Structured Police Incident Report.
    Represents an official burglary incident summary generated from authentic metadata.
    """
    report_id: str = Field(..., description="Opaque unique document ID (e.g. DOC_IR_...)")
    incident_id: str = Field(..., description="Associated crime incident ID (e.g. CID#xxx)")
    incident_date: str = Field(..., description="Incident date string (YYYY-MM-DD HH:MM:SS)")
    location_sector: str = Field(..., description="Synthetic metropolitan sector name matching coordinates")
    normalized_coordinates: Tuple[float, float] = Field(..., description="(X, Y) normalized spatial coordinates")
    forced_entry_method: str = Field(..., description="Point of forced entry (e.g. pry marks on rear patio door)")
    stolen_property: List[str] = Field(default_factory=list, description="Categories of items stolen")
    suspects_mentioned: List[str] = Field(default_factory=list, description="Suspect IDs or monikers observed")
    narrative: str = Field(..., description="Objective narrative text detailing police observations")
    is_distractor: bool = Field(default=False, description="Flag indicating whether this is a distractor document")

    def to_retrieval_text(self) -> str:
        """Converts report to clean textual chunk for vector/BM25 indexing."""
        items_str = ", ".join(self.stolen_property) if self.stolen_property else "Unspecified property"
        suspects_str = ", ".join(self.suspects_mentioned) if self.suspects_mentioned else "Unidentified actors"
        return (
            f"INCIDENT REPORT [{self.report_id}] - CASE {self.incident_id}\n"
            f"Date: {self.incident_date} | Sector: {self.location_sector}\n"
            f"Entry Method: {self.forced_entry_method}\n"
            f"Stolen Items: {items_str}\n"
            f"Suspects/Persons of Interest: {suspects_str}\n\n"
            f"NARRATIVE SUMMARY:\n{self.narrative}"
        )


class CallDetailRecord(BaseModel):
    """
    Structured Call Detail Record (CDR) entry.
    Calibrated against empirical Israel LEA wiretap frequency distributions.
    """
    cdr_id: str = Field(..., description="Opaque CDR transaction ID")
    call_timestamp: str = Field(..., description="Date and time of call (YYYY-MM-DD HH:MM:SS)")
    caller_identifier: str = Field(..., description="Caller entity ID or alias/phone handle")
    callee_identifier: str = Field(..., description="Callee entity ID or alias/phone handle")
    duration_seconds: int = Field(..., ge=0, description="Duration of call in seconds")
    cell_tower_sector: str = Field(..., description="Originating cell tower sector")
    call_type: str = Field(default="voice_call", description="Call type: voice_call or sms")

    def to_retrieval_text(self) -> str:
        """Converts CDR to clean textual chunk for retrieval indexing."""
        return (
            f"COMMUNICATION INTERCEPT LOG [{self.cdr_id}]\n"
            f"Timestamp: {self.call_timestamp} | Type: {self.call_type.upper()}\n"
            f"Caller: {self.caller_identifier} -> Callee: {self.callee_identifier}\n"
            f"Duration: {self.duration_seconds}s | Originating Sector: {self.cell_tower_sector}"
        )


# ==============================================================================
# 3. PROVENANCE ENVELOPE (INTERNAL AUDIT ONLY)
# ==============================================================================

class EvidenceProvenanceEnvelope(BaseModel):
    """
    Internal provenance envelope tracking the synthetic generation history.
    MUST BE STRIPPED before presenting evidence chunks to the retrieval engine.
    """
    document_id: str
    is_synthetic: bool = True
    generator_version: str = "pilot_v1.0"
    generation_seed: int = 42
    ground_truth_case_id: Optional[str] = None
    target_pair: Optional[Tuple[str, str]] = None
    source_incident_cid: Optional[str] = None
    condition: str
    generation_rule: str
    underlying_entity_references: List[str]
    creation_timestamp: str


# ==============================================================================
# 4. SANITIZED RETRIEVAL DOCUMENT SCHEMA (EVALUATION-FACING)
# ==============================================================================

PERMITTED_DOC_ID_REGEX = re.compile(r"^(DOC_IR|CDR)_[0-9a-f]{8}$")
ORIGINAL_CID_REGEX = re.compile(r"\bCID\s*[-#:]?\s*\d+\b", re.IGNORECASE)
PILOT_CASE_REGEX = re.compile(r"\bPILOT[-_ ]*(CASE)?[-_ ]*\d+\b", re.IGNORECASE)


class SanitizedRetrievalDocument(BaseModel):
    """
    Strictly sanitized document payload exposed to the retriever / evaluated agent.
    Guaranteed free of labels, hidden conditions, original crime IDs, or ground-truth leakage fields.
    """
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(..., description="Opaque document identifier matching ^(DOC_IR|CDR)_[0-9a-f]{8}$")
    doc_type: str = Field(..., description="incident_report or call_detail_record")
    timestamp: str = Field(..., description="Timestamp for chronological sorting")
    text_content: str = Field(..., description="Retrievable natural language / tabular text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Retriever-safe operational metadata")

    @model_validator(mode="after")
    def verify_no_leakage_fields(self) -> "SanitizedRetrievalDocument":
        # 1. Enforce exact permitted document-ID formats
        if not isinstance(self.doc_id, str) or not PERMITTED_DOC_ID_REGEX.match(self.doc_id):
            raise ValueError(
                f"Leakage/Format violation: Invalid doc_id '{self.doc_id}'. "
                "Must strictly match format '^(DOC_IR|CDR)_[0-9a-f]{8}$'."
            )
        upper_id = self.doc_id.upper()
        for forbidden_id_sub in ["PILOT", "CASE", "PAIR", "COND", "LABEL", "GROUND_TRUTH", "CID"]:
            if forbidden_id_sub in upper_id:
                raise ValueError(
                    f"Leakage violation: Suspicious identifier token '{forbidden_id_sub}' in doc_id '{self.doc_id}'"
                )

        # 2. Reject malformed or unexpected retrieval payloads
        if self.doc_type not in ["incident_report", "call_detail_record"]:
            raise ValueError(
                f"Malformed payload: Invalid doc_type '{self.doc_type}'. Expected 'incident_report' or 'call_detail_record'."
            )
        if not self.timestamp or not isinstance(self.timestamp, str) or len(self.timestamp.strip()) < 10:
            raise ValueError(f"Malformed payload: Invalid or missing timestamp '{self.timestamp}'")
        if not self.text_content or not isinstance(self.text_content, str) or len(self.text_content.strip()) < 20:
            raise ValueError("Malformed payload: text_content must be non-empty string and at least 20 characters.")
        if not isinstance(self.metadata, dict):
            raise ValueError("Malformed payload: metadata must be a dictionary.")

        # 3. Normalized metadata key checks & pattern-based safeguards
        forbidden_normalized_exact = {
            "label", "iscooffender", "cooffender", "groundtruth", "truth", "condition", "rationale",
            "targetpair", "pairlabel", "sharedcids", "sharedcid", "observededge", "component", "components",
            "componentid", "compid", "comp", "isdistractor", "distractor", "caseid", "pilotcase",
            "split", "partition", "target", "pair", "sourcecid"
        }
        forbidden_normalized_substrings = [
            "label", "groundtruth", "targetpair", "caseid", "component", "condition",
            "rationale", "observededge", "sharedcid", "pilotcase", "cooffend", "distractor"
        ]

        for k in self.metadata.keys():
            k_str = str(k)
            norm_key = re.sub(r"[^a-z0-9]", "", k_str.lower())
            if norm_key in forbidden_normalized_exact or any(pat in norm_key for pat in forbidden_normalized_substrings):
                raise ValueError(f"Leakage violation: Forbidden metadata key '{k}' found in retrieval metadata!")
            if re.search(r"(^|_|-|original|source)cid(_|-|\d|$)", k_str, re.IGNORECASE) or norm_key in ["cid", "sourcecid", "origcid"]:
                raise ValueError(f"Leakage violation: Forbidden crime identifier key '{k}' in retrieval metadata!")

        # 4. Recursive metadata value scan (including nested dicts, lists, sets, primitives)
        def _extract_all_strings(val) -> List[str]:
            strs = []
            if isinstance(val, str):
                strs.append(val)
            elif isinstance(val, dict):
                for sub_k, sub_v in val.items():
                    strs.append(str(sub_k))
                    strs.extend(_extract_all_strings(sub_v))
            elif isinstance(val, (list, tuple, set)):
                for item in val:
                    strs.extend(_extract_all_strings(item))
            elif val is not None and not isinstance(val, bool):
                strs.append(str(val))
            return strs

        all_meta_strings = _extract_all_strings(self.metadata)
        for s in all_meta_strings:
            if ORIGINAL_CID_REGEX.search(s) or "CID#" in s.upper():
                raise ValueError(f"Leakage violation: Original crime identifier found in metadata: '{s}'")
            if PILOT_CASE_REGEX.search(s) or "PILOT_CASE" in s.upper() or "PILOT CASE" in s.upper():
                raise ValueError(f"Leakage violation: Pilot-case identifier found in metadata: '{s}'")
            upper_s = s.upper()
            for forbidden_sub in [
                "GROUND TRUTH", "GROUND_TRUTH", "IS_CO_OFFENDER", "CO_OFFENDER",
                "LABEL: 1", "LABEL: 0", "LABEL:1", "LABEL:0", "TARGET_PAIR", "TARGET PAIR"
            ]:
                if forbidden_sub in upper_s:
                    raise ValueError(f"Leakage violation: Forbidden evaluation string '{forbidden_sub}' found in metadata value: '{s}'")
            lower_s = s.lower()
            for cond in ["clean_evidence", "alias_ambiguity", "missing_evidence", "distractors", "mixed_difficulty"]:
                if cond in lower_s:
                    raise ValueError(f"Leakage violation: Condition string '{cond}' found in metadata value: '{s}'")

        # 5. Check text_content for original CIDs, pilot-case IDs, and explicit evaluation leakage
        if ORIGINAL_CID_REGEX.search(self.text_content) or "CID#" in self.text_content.upper():
            raise ValueError("Leakage violation: Original crime identifier found in text_content!")

        if PILOT_CASE_REGEX.search(self.text_content) or "PILOT_CASE" in self.text_content.upper() or "PILOT CASE" in self.text_content.upper():
            raise ValueError("Leakage violation: Pilot-case identifier found in text_content!")

        upper_text = self.text_content.upper()
        for forbidden in [
            "GROUND TRUTH", "GROUND_TRUTH", "IS_CO_OFFENDER", "LABEL: 1", "LABEL: 0",
            "LABEL:1", "LABEL:0", "TARGET_PAIR", "TARGET PAIR"
        ]:
            if forbidden in upper_text:
                raise ValueError(f"Leakage violation: Forbidden string '{forbidden}' found in document text!")

        lower_text = self.text_content.lower()
        for cond in ["clean_evidence", "alias_ambiguity", "missing_evidence", "distractors", "mixed_difficulty"]:
            if cond in lower_text:
                raise ValueError(f"Leakage violation: Evaluation condition name '{cond}' found in document text!")

        for artificial_neg in [
            "never communicated", "never spoke", "no relationship",
            "definitely innocent", "proven negative", "not accomplices", "unrelated suspects"
        ]:
            if artificial_neg in lower_text:
                raise ValueError(f"Evidential violation: Artificial negative assertion '{artificial_neg}' in document text!")

        return self


def validate_retrieval_corpus(documents: List[SanitizedRetrievalDocument]) -> None:
    """
    Validates an entire corpus of SanitizedRetrievalDocument objects:
    - Enforces zero duplicate doc_ids.
    - Verifies non-empty corpus.
    """
    if not documents:
        raise ValueError("Corpus validation error: Document list is empty.")
    seen_ids = set()
    for doc in documents:
        if doc.doc_id in seen_ids:
            raise ValueError(f"Corpus validation error: Duplicate doc_id '{doc.doc_id}' detected!")
        seen_ids.add(doc.doc_id)
