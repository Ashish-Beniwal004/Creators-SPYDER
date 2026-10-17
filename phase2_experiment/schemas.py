"""
Phase 2E Strict Experimental Schemas
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_experiment/schemas.py

Defines validated Pydantic models for:
1. TargetPairInput: Clean target pair input with zero ground truth leakage.
2. SystemCaseOutput: Per-case output schema for System A and System B.
3. ArmRunResult: Complete run result artifact for an experimental arm.
4. PilotRunManifest: Frozen pilot run manifest linking outputs and checksums.
5. CaseEvaluationComparison: Downstream evaluation record joining system decisions to labels.
6. DescriptiveMetrics & PilotScoringReport: Evaluation report structures.
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# Regex patterns
ENTITY_REGEX = re.compile(r"^OID#\d+$")
DOC_ID_REGEX = re.compile(r"^(DOC_IR|CDR)_[0-9a-f]{8}$")

# Allowed Literals
ExperimentalArm = Literal["system_a_rag_only", "system_b_rag_verification"]
RelationshipDecision = Literal["Supported", "Unsupported", "Insufficient Evidence"]


class TargetPairInput(BaseModel):
    """
    Sanitized input representation for an entity pair under investigation.
    Guaranteed free of labels, case IDs, rationales, conditions, or graph components.
    """
    model_config = ConfigDict(extra="forbid")

    entity_a: str = Field(..., description="Canonical ID for first entity (e.g. OID#4418)")
    entity_b: str = Field(..., description="Canonical ID for second entity (e.g. OID#8864)")

    @field_validator("entity_a", "entity_b")
    @classmethod
    def validate_entity_format(cls, v: str) -> str:
        if not isinstance(v, str) or not ENTITY_REGEX.match(v):
            raise ValueError(f"Invalid canonical entity ID '{v}'. Must match '^OID#\\d+$'.")
        return v

    @model_validator(mode="after")
    def validate_non_reflexive(self) -> "TargetPairInput":
        if self.entity_a == self.entity_b:
            raise ValueError(f"Self-comparison forbidden: entity_a '{self.entity_a}' == entity_b '{self.entity_b}'.")
        return self


class SystemCaseOutput(BaseModel):
    """
    Structured per-case decision output produced by an experimental arm.
    Contains no ground-truth labels, conditions, or internal vault references.
    """
    model_config = ConfigDict(extra="forbid")

    case_index: int = Field(..., ge=0, description="0-indexed position within the evaluation run")
    arm: ExperimentalArm = Field(..., description="Experimental system producing this result")
    entity_a: str = Field(..., description="First subject in pair")
    entity_b: str = Field(..., description="Second subject in pair")
    target_pair: Tuple[str, str] = Field(..., description="Canonical entity tuple")
    decision: RelationshipDecision = Field(..., description="Relationship verdict ('Supported', 'Unsupported', 'Insufficient Evidence')")
    is_supported: bool = Field(..., description="Boolean flag: True if decision == 'Supported', else False")
    rationale: str = Field(..., description="Evidence-grounded justification for the decision")
    retrieval_query: str = Field(..., description="Query string used for evidence retrieval")
    retrieved_doc_ids: List[str] = Field(..., description="List of document IDs retrieved for this case")
    retrieval_scores: Dict[str, float] = Field(..., description="Cosine similarity score per retrieved doc_id")
    cited_doc_ids: List[str] = Field(default_factory=list, description="Document IDs cited in the decision justification")
    verification_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured verification payload (populated for System B only)"
    )
    execution_timestamp: str = Field(..., description="ISO 8601 execution timestamp")

    @field_validator("entity_a", "entity_b")
    @classmethod
    def validate_entities(cls, v: str) -> str:
        if not ENTITY_REGEX.match(v):
            raise ValueError(f"Invalid entity format: '{v}'")
        return v

    @field_validator("retrieved_doc_ids", "cited_doc_ids")
    @classmethod
    def validate_doc_ids(cls, v: List[str]) -> List[str]:
        for doc_id in v:
            if not DOC_ID_REGEX.match(doc_id):
                raise ValueError(f"Invalid document ID format: '{doc_id}'")
        return v

    @model_validator(mode="after")
    def validate_arm_consistency(self) -> "SystemCaseOutput":
        if self.arm == "system_a_rag_only" and self.verification_data is not None:
            raise ValueError("System A (RAG-only) must not contain verification data.")
        return self


class ArmRunResult(BaseModel):
    """
    Immutable collection of results for a full experimental arm run over a test set.
    """
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="Unique run identifier")
    arm: ExperimentalArm = Field(..., description="Experimental system arm")
    execution_timestamp: str = Field(..., description="Run completion timestamp")
    parameters: Dict[str, Any] = Field(..., description="Fixed parameters used during this run")
    total_cases: int = Field(..., ge=0, description="Total number of evaluated cases")
    results: List[SystemCaseOutput] = Field(..., description="Per-case results")


class PilotRunManifest(BaseModel):
    """
    Frozen execution manifest documenting the pilot run metadata, parameters,
    and output file hashes.
    """
    model_config = ConfigDict(extra="forbid")

    manifest_version: str = Field(default="1.0")
    run_id: str = Field(..., description="Unique pilot run ID")
    execution_timestamp: str = Field(..., description="Run completion timestamp")
    corpus_sha256: str = Field(..., description="SHA-256 hash of the evidence corpus")
    parameters: Dict[str, Any] = Field(..., description="Experimental parameters applied")
    total_cases: int = Field(default=10, description="Number of evaluated pilot cases")
    system_a_output_file: str = Field(..., description="Relative path to System A outputs")
    system_b_output_file: str = Field(..., description="Relative path to System B outputs")
    system_a_output_sha256: str = Field(..., description="SHA-256 hash of System A outputs")
    system_b_output_sha256: str = Field(..., description="SHA-256 hash of System B outputs")


class CaseEvaluationComparison(BaseModel):
    """
    Comparative evaluation record joining an experimental output to ground-truth labels.
    Generated ONLY during the decoupled post-execution scoring step.
    """
    model_config = ConfigDict(extra="forbid")

    case_index: int = Field(..., ge=0)
    case_id: str = Field(..., description="Pilot case identifier (e.g. PILOT_CASE_01)")
    target_pair: Tuple[str, str] = Field(..., description="Evaluated entity pair")
    ground_truth_label: int = Field(..., ge=0, le=1, description="Definitive ground-truth label (1 or 0)")
    condition: str = Field(..., description="Experimental condition")
    system_a_decision: RelationshipDecision = Field(...)
    system_a_predicted_label: int = Field(..., ge=0, le=1)
    system_a_correct: bool = Field(...)
    system_b_decision: RelationshipDecision = Field(...)
    system_b_predicted_label: int = Field(..., ge=0, le=1)
    system_b_correct: bool = Field(...)
    agreement: bool = Field(..., description="Whether System A and System B produced the same binary verdict")
    notes: str = Field(default="", description="Descriptive notes explaining differences or error modes")


class DescriptiveMetrics(BaseModel):
    """
    Summary descriptive evaluation metrics over a test split.
    Undefined metrics when denominator is 0 are represented as None (N/A).
    """
    model_config = ConfigDict(extra="forbid")

    total_cases: int = Field(..., ge=0)
    true_positives: int = Field(..., ge=0)
    false_positives: int = Field(..., ge=0)
    true_negatives: int = Field(..., ge=0)
    false_negatives: int = Field(..., ge=0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    f1_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    specificity: Optional[float] = Field(None, ge=0.0, le=1.0)
    false_positive_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    accuracy_ci_95: Optional[Tuple[float, float]] = None
    precision_ci_95: Optional[Tuple[float, float]] = None
    recall_ci_95: Optional[Tuple[float, float]] = None
    specificity_ci_95: Optional[Tuple[float, float]] = None


class PilotScoringReport(BaseModel):
    """
    Comprehensive scoring report comparing System A and System B against pilot labels.
    """
    model_config = ConfigDict(extra="forbid")

    evaluation_timestamp: str = Field(...)
    run_id: str = Field(...)
    total_cases: int = Field(default=10)
    system_a_metrics: DescriptiveMetrics = Field(...)
    system_b_metrics: DescriptiveMetrics = Field(...)
    per_condition_breakdown: Dict[str, Dict[str, Any]] = Field(...)
    case_comparisons: List[CaseEvaluationComparison] = Field(...)
    summary_findings: str = Field(...)


class BenchmarkRunManifest(BaseModel):
    """
    Execution manifest documenting a benchmark evaluation run (pilot or full-test).
    """
    model_config = ConfigDict(extra="forbid")

    manifest_version: str = Field(default="1.0")
    run_id: str = Field(...)
    dataset_mode: str = Field(default="full_test")
    execution_timestamp: str = Field(...)
    corpus_sha256: str = Field(...)
    targets_sha256: Optional[str] = None
    parameters: Dict[str, Any] = Field(...)
    total_cases: int = Field(...)
    system_a_output_file: str = Field(...)
    system_b_output_file: str = Field(...)
    system_a_output_sha256: str = Field(...)
    system_b_output_sha256: str = Field(...)


class BenchmarkScoringReport(BaseModel):
    """
    Comprehensive scoring report for full benchmark evaluations.
    """
    model_config = ConfigDict(extra="forbid")

    evaluation_timestamp: str = Field(...)
    run_id: str = Field(...)
    dataset_mode: str = Field(default="full_test")
    total_cases: int = Field(...)
    system_a_metrics: DescriptiveMetrics = Field(...)
    system_b_metrics: DescriptiveMetrics = Field(...)
    system_a_eval_metrics: Optional[Dict[str, Any]] = None
    system_b_eval_metrics: Optional[Dict[str, Any]] = None
    per_condition_breakdown: Dict[str, Dict[str, Any]] = Field(...)
    paired_comparison: Dict[str, Any] = Field(default_factory=dict)
    evidentiary_soundness_audit: Dict[str, Any] = Field(default_factory=dict)
    case_comparisons: List[CaseEvaluationComparison] = Field(...)
    summary_findings: str = Field(...)
