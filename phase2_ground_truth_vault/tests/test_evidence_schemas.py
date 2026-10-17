"""
Unit tests for Evidence Schemas and Synthetic Record Formatting
"""

import os
import sys
import json
import pytest

VAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VAULT_DIR)

from schemas import (
    PoliceIncidentReport,
    CallDetailRecord,
    EvidenceProvenanceEnvelope,
    SanitizedRetrievalDocument
)


def test_police_incident_report_validation():
    """Test valid creation and formatting of PoliceIncidentReport."""
    rep = PoliceIncidentReport(
        report_id="DOC_IR_TEST_01",
        incident_id="CID#6456",
        incident_date="2020-01-17 02:40:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5688, 0.6008),
        forced_entry_method="Rear sliding window pry marks",
        stolen_property=["Jewelry", "Cash"],
        suspects_mentioned=["OID#4418", "OID#8864"],
        narrative="Two individuals fled the scene. Detained nearby with stolen property.",
        is_distractor=False
    )
    assert rep.incident_id == "CID#6456"
    assert len(rep.suspects_mentioned) == 2

    text = rep.to_retrieval_text()
    assert "INCIDENT REPORT [DOC_IR_TEST_01]" in text
    assert "CID#6456" in text
    assert "OID#4418" in text
    assert "OID#8864" in text


def test_call_detail_record_validation():
    """Test valid creation and formatting of CallDetailRecord."""
    cdr = CallDetailRecord(
        cdr_id="CDR_TEST_01",
        call_timestamp="2020-01-17 01:15:22",
        caller_identifier="OID#4418",
        callee_identifier="OID#8864",
        duration_seconds=145,
        cell_tower_sector="Sector-Central-East",
        call_type="voice_call"
    )
    assert cdr.duration_seconds == 145
    text = cdr.to_retrieval_text()
    assert "COMMUNICATION INTERCEPT LOG [CDR_TEST_01]" in text
    assert "OID#4418 -> Callee: OID#8864" in text


def test_pilot_evidence_sample_file():
    """Verify that pilot_evidence_sample.json is present and passes schema validation."""
    sample_path = os.path.join(VAULT_DIR, "pilot_evidence_sample.json")
    assert os.path.exists(sample_path), f"Missing {sample_path}"
    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for r in data["incident_reports"]:
        PoliceIncidentReport(**r)
    for c in data["call_detail_records"]:
        CallDetailRecord(**c)
    for p in data["internal_provenance_manifest"]:
        EvidenceProvenanceEnvelope(**p)
    for d in data["sanitized_retrieval_corpus_sample"]:
        SanitizedRetrievalDocument(**d)
