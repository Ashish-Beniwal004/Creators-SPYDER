"""
Unit tests for Leakage Safeguards and Sanitization Rules
"""

import os
import sys
import json
import pytest

VAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VAULT_DIR)

from schemas import SanitizedRetrievalDocument


def test_sanitized_retrieval_document_allows_clean_payload():
    """Verify that a clean retrieval document is accepted."""
    doc = SanitizedRetrievalDocument(
        doc_id="DOC_IR_68ca5aaf",
        doc_type="incident_report",
        timestamp="2020-01-17 02:40:00",
        text_content="Officers responded to a residential alarm at Sector-Central-East.",
        metadata={"incident_id": "INC-2020-7182", "sector": "Sector-Central-East"}
    )
    assert doc.doc_id == "DOC_IR_68ca5aaf"


def test_sanitized_retrieval_document_rejects_invalid_doc_id():
    """Verify that retrieval documents with non-conforming or case-revealing IDs are rejected."""
    invalid_ids = [
        "DOC_CLEAN_01",
        "DOC_IR_PILOT_01_A",
        "CDR_PILOT_01_01",
        "DOC_IR_CASE_01",
        "DOC_IR_CID6456",
        "invalid_id",
        "DOC_IR_123"
    ]
    for bad_id in invalid_ids:
        with pytest.raises(ValueError, match="Leakage/Format violation"):
            SanitizedRetrievalDocument(
                doc_id=bad_id,
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Regular police summary without explicit label in text.",
                metadata={"sector": "Sector-North"}
            )


def test_sanitized_retrieval_document_rejects_leakage_keys():
    """Verify that retrieval documents containing ground-truth keys are rejected."""
    forbidden_metadata = [
        {"label": 1},
        {"is_co_offender": True},
        {"ground_truth": "positive"},
        {"condition": "clean_evidence"},
        {"target_pair": ["OID#4418", "OID#8864"]},
        {"rationale": "documented co-offenders"},
        {"shared_cid": "CID#6456"},
        {"component_id": 1}
    ]

    for bad_meta in forbidden_metadata:
        with pytest.raises(ValueError, match="Leakage violation"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_11111111",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Regular police summary without explicit label in text.",
                metadata=bad_meta
            )


def test_sanitized_retrieval_document_rejects_leakage_in_text():
    """Verify that retrieval documents with explicit label text strings are rejected."""
    with pytest.raises(ValueError, match="Leakage violation"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_11111111",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="GROUND TRUTH IS_CO_OFFENDER: True",
            metadata={"sector": "Sector-North"}
        )


def test_ground_truth_vault_security_quarantine():
    """Verify that ground_truth.json has explicit quarantine declarations."""
    gt_path = os.path.join(VAULT_DIR, "ground_truth.json")
    with open(gt_path, "r", encoding="utf-8") as f:
        gt = json.load(f)

    assert "STRICTLY_QUARANTINED" in gt.get("vault_security_classification", "")
    assert "DO NOT INDEX" in gt.get("quarantine_policy", "")
