"""Small, dependency-free public contracts shared by mocks and live experiments."""

from dataclasses import asdict, dataclass
import json
import math
import re
from typing import Any

ARMS = ("system_a_rag_only", "system_b_rag_verification")
DECISIONS = ("Supported", "Unsupported", "Insufficient Evidence")
ENTITY_ID = re.compile(r"OID#[0-9]+")
DOCUMENT_ID = re.compile(r"(?:DOC_IR|CDR)_[0-9a-f]{8}")


def exact_keys(value: Any, keys: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name} must contain exactly: {', '.join(sorted(keys))}")
    return value


def document_ids(value: Any, allowed: set[str], *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise ValueError("Evidence IDs must be a list of strings")
    if len(set(value)) != len(value) or any(not DOCUMENT_ID.fullmatch(x) for x in value):
        raise ValueError("Evidence IDs must be unique, valid document identifiers")
    if not set(value) <= allowed:
        raise ValueError("Evidence IDs must belong to the evidence supplied to this call")
    if nonempty and not value:
        raise ValueError("At least one evidence ID is required")
    return value


@dataclass(frozen=True)
class TargetPair:
    entity_a: str
    entity_b: str

    def __post_init__(self):
        if any(not isinstance(x, str) or not ENTITY_ID.fullmatch(x) for x in (self.entity_a, self.entity_b)):
            raise ValueError("Entities must use canonical OID#<digits> identifiers")
        if self.entity_a == self.entity_b:
            raise ValueError("Target entities must be distinct")

    @property
    def ids(self) -> tuple[str, str]:
        return tuple(sorted((self.entity_a, self.entity_b)))


@dataclass(frozen=True)
class Evidence:
    doc_id: str
    doc_type: str
    text_content: str
    score: float

    def __post_init__(self):
        if not isinstance(self.doc_id, str) or not DOCUMENT_ID.fullmatch(self.doc_id):
            raise ValueError("Invalid public document ID")
        if self.doc_type not in ("incident_report", "call_detail_record"):
            raise ValueError("Unapproved evidence type")
        if not isinstance(self.text_content, str) or not self.text_content.strip():
            raise ValueError("Evidence text cannot be empty")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise ValueError("Retrieval score must be numeric")
        if not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("Retrieval score must be finite and between zero and one")

    @classmethod
    def from_dict(cls, value: dict) -> "Evidence":
        return cls(**exact_keys(value, {"doc_id", "doc_type", "text_content", "score"}, "Evidence"))


@dataclass(frozen=True)
class CaseInput:
    pair: TargetPair
    query: str
    evidence: tuple[Evidence, ...]

    def __post_init__(self):
        if not isinstance(self.query, str) or not self.query.strip():
            raise ValueError("Retrieval query cannot be empty")
        if len(self.doc_ids) != len(self.evidence):
            raise ValueError("Retrieved document IDs must be unique")

    @property
    def doc_ids(self) -> set[str]:
        return {item.doc_id for item in self.evidence}

    def public_payload(self) -> dict:
        # An allowlist: no caller-provided metadata, labels or conditions can be forwarded.
        return {"target_pair": list(self.pair.ids), "evidence": [asdict(d) for d in self.evidence]}


@dataclass(frozen=True)
class Decision:
    decision: str
    rationale: str
    cited_doc_ids: list[str]

    @classmethod
    def parse(cls, value: Any, case: CaseInput) -> "Decision":
        if isinstance(value, str):
            value = json.loads(value)
        exact_keys(value, {"decision", "rationale", "cited_doc_ids"}, "Final decision")
        if value["decision"] not in DECISIONS:
            raise ValueError("Invalid relationship decision")
        if not isinstance(value["rationale"], str) or not value["rationale"].strip():
            raise ValueError("A nonempty rationale is required")
        ids = document_ids(value["cited_doc_ids"], case.doc_ids, nonempty=value["decision"] == "Supported")
        return cls(value["decision"], value["rationale"], ids)


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict
    call_id: str

    def validate(self, case: CaseInput) -> None:
        if self.name != "verify_hypothesis":
            raise ValueError("Only verify_hypothesis is approved")
        if not isinstance(self.call_id, str) or not self.call_id.strip():
            raise ValueError("A tool-call ID is required")
        args = exact_keys(self.arguments, {"entity_a", "entity_b", "evidence_ids"}, "Verifier arguments")
        if TargetPair(args["entity_a"], args["entity_b"]).ids != case.pair.ids:
            raise ValueError("The verifier call changed the target pair")
        document_ids(args["evidence_ids"], case.doc_ids, nonempty=True)


def validate_verification(value: Any, call: ToolCall) -> dict:
    """Check public tool results before they can be returned to the model."""
    value = exact_keys(value, {"status", "evidence_class", "cited_evidence_ids", "rationale", "findings"}, "Verification result")
    if value["status"] not in DECISIONS:
        raise ValueError("Verifier returned an invalid status")
    if value["evidence_class"] not in {"direct", "indirect_resolved", "indirect_unresolved", "contradictory", "insufficient"}:
        raise ValueError("Verifier returned an invalid evidence class")
    document_ids(value["cited_evidence_ids"], set(call.arguments["evidence_ids"]), nonempty=value["status"] == "Supported")
    if not isinstance(value["rationale"], str) or not value["rationale"].strip():
        raise ValueError("Verifier rationale cannot be empty")
    if not isinstance(value["findings"], list):
        raise ValueError("Verifier findings must be a list")
    # Findings have an explicit field allowlist as well; no hidden tool metadata is forwarded.
    finding_keys = {"doc_id", "doc_type", "finding_type", "entities_mentioned", "aliases_mentioned", "summary"}
    for finding in value["findings"]:
        exact_keys(finding, finding_keys, "Verifier finding")
        document_ids([finding["doc_id"]], set(call.arguments["evidence_ids"]))
    return value
