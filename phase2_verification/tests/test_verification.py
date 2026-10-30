"""
Phase 2D & 2D.1 Automated Test Suite for Evidence-Grounded Hypothesis Verification
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_verification/tests/test_verification.py

Verifies:
1. Communication without a shared burglary returns 'Insufficient Evidence'.
2. Alias resolution without a qualifying joint incident returns 'Insufficient Evidence'.
3. Communication combined with alias resolution (without burglary) returns 'Insufficient Evidence'.
4. Documented qualifying joint burglary records (direct and resolved alias) return 'Supported'.
5. Missing joint incident reports and ambiguous unresolved aliases return 'Insufficient Evidence'.
6. Independent operations with spatial/temporal proximity return 'Insufficient Evidence'.
7. Explicit incident exclusion returns 'Unsupported'.
8. Contradictory alias attribution returns 'Unsupported'.
9. Rejection of unknown, malformed, duplicate, or empty document IDs.
10. Rejection of invalid, malformed, or reflexive entity inputs.
11. Schema strictness (extra fields forbidden, exact types).
12. Citation tracking integrity (every claim traced to cited document IDs).
13. Strict firewall quarantine (no access to ground truth, provenance, or splits).
14. Tool permissions catalog (strictly approved read-only tools).
15. Deterministic repeatability and entity order symmetry.
16. Regression validation of frozen Phase 2A-2C corpus and manifest hashes.
"""

import os
import sys
import json
import ast
import hashlib
import tempfile
import contextlib
import pytest
from pydantic import ValidationError

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_ground_truth_vault.schemas import SanitizedRetrievalDocument
from phase2_verification.schemas import (
    VerificationResult,
    VerificationFinding,
    VerificationStatus,
    EvidenceClassification,
)
from phase2_verification.verifier import (
    verify_hypothesis,
    HypothesisVerifier,
    extract_document_facts,
    get_default_verifier,
)
from phase2_verification import APPROVED_READONLY_TOOLS

CORPUS_PATH = os.path.join(REPO_ROOT, "phase2_corpus", "retrieval_documents.jsonl")


# =====================================================================
# 1. Communication Without a Shared Burglary
# =====================================================================

def test_communication_without_shared_burglary_insufficient_evidence():
    """
    A direct CDR intercept (CDR_055ad8bc) establishes telecommunication between
    OID#4418 and OID#8864, but does NOT establish the benchmark target of a
    shared burglary co-offending relationship. It must return 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#4418", "OID#8864", ["CDR_055ad8bc"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert result.cited_evidence_ids == ["CDR_055ad8bc"]
    assert "CDR_055ad8bc" in result.rationale
    assert "Communication alone does not establish the benchmark target relationship" in result.rationale
    assert len(result.findings) >= 1
    assert result.findings[0].finding_type == "direct_communication"


def test_multiple_cdrs_without_shared_burglary_insufficient_evidence():
    """
    Citing multiple direct communication records (CDR_055ad8bc and CDR_5b17362b)
    confirms communication, but without a shared burglary record, returns 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#4418", "OID#8864", ["CDR_055ad8bc", "CDR_5b17362b"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "CDR_055ad8bc" in result.rationale
    assert "Communication alone does not establish" in result.rationale
    for f in result.findings:
        assert f.finding_type == "direct_communication"


# =====================================================================
# 2. Alias Resolution Without a Qualifying Joint Incident
# =====================================================================

def test_alias_resolution_without_qualifying_incident_insufficient_evidence():
    """
    An intelligence record (DOC_IR_c1c7b4bb) establishes an alias mapping for OID#8595
    ('The Wire'), but citing it without a joint burglary record returns 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#6819", "OID#8595", ["DOC_IR_c1c7b4bb"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "DOC_IR_c1c7b4bb" in result.rationale
    assert "An alias resolution alone does not establish shared burglary participation" in result.rationale
    assert result.findings[0].finding_type == "alias_attribution"


def test_communication_plus_alias_resolution_without_burglary_insufficient_evidence():
    """
    Citing an alias communication record (CDR_063962b6) and an alias resolution record
    (DOC_IR_c1c7b4bb) proves communication between OID#6819 and OID#8595 via 'The Wire',
    but without a joint burglary incident report, must return 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#6819", "OID#8595", ["CDR_063962b6", "DOC_IR_c1c7b4bb"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "no qualifying shared" in result.rationale and "burglary incident is documented" in result.rationale
    types = {f.finding_type for f in result.findings}
    assert "alias_communication" in types
    assert "alias_attribution" in types


# =====================================================================
# 3. Documented Qualifying Joint Burglary (Supported)
# =====================================================================

def test_direct_joint_burglary_supported():
    """
    A qualifying joint burglary report (DOC_IR_68ca5aaf) explicitly listing
    OID#4418 and OID#8864 as co-suspects establishes 'Supported'.
    """
    result = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf"])
    assert result.status == "Supported"
    assert result.evidence_class == "direct"
    assert result.cited_evidence_ids == ["DOC_IR_68ca5aaf"]
    assert "DOC_IR_68ca5aaf" in result.rationale
    assert "OID#4418" in result.rationale and "OID#8864" in result.rationale
    assert len(result.findings) >= 1
    assert result.findings[0].finding_type == "direct_burglary_co_offending"


def test_direct_joint_burglary_with_corroborating_cdr_supported():
    """
    A qualifying joint burglary report (DOC_IR_68ca5aaf) accompanied by a CDR (CDR_055ad8bc)
    establishes 'Supported', noting corroborating telecommunications.
    """
    result = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf", "CDR_055ad8bc"])
    assert result.status == "Supported"
    assert result.evidence_class == "direct"
    assert set(result.cited_evidence_ids) == {"DOC_IR_68ca5aaf", "CDR_055ad8bc"}
    assert "DOC_IR_68ca5aaf" in result.rationale
    assert "CDR_055ad8bc" in result.rationale
    assert "Corroborating telecommunication" in result.rationale


def test_alias_resolved_joint_burglary_case_03_supported():
    """
    Case 03: Burglary report DOC_IR_71acf05c details burglary with OID#6819 and accomplice 'The Wire'.
    Field stop DOC_IR_c1c7b4bb resolves 'The Wire' to OID#8595.
    Jointly, they establish shared-burglary co-offending -> 'Supported'.
    """
    result = verify_hypothesis("OID#6819", "OID#8595", ["DOC_IR_71acf05c", "DOC_IR_c1c7b4bb"])
    assert result.status == "Supported"
    assert result.evidence_class == "indirect_resolved"
    assert set(result.cited_evidence_ids) == {"DOC_IR_71acf05c", "DOC_IR_c1c7b4bb"}
    assert "The Wire" in result.rationale
    assert "DOC_IR_71acf05c" in result.rationale
    assert "DOC_IR_c1c7b4bb" in result.rationale


def test_alias_resolved_joint_burglary_case_09_locksmith_supported():
    """
    Case 09: Primary burglary report DOC_IR_bf7db53a links OID#1964 and 'The Locksmith'.
    Intelligence interview DOC_IR_80e4d5d3 resolves 'The Locksmith' to OID#2568.
    Jointly, they establish shared-burglary co-offending -> 'Supported'.
    """
    result = verify_hypothesis("OID#1964", "OID#2568", ["DOC_IR_bf7db53a", "DOC_IR_80e4d5d3"])
    assert result.status == "Supported"
    assert result.evidence_class == "indirect_resolved"
    assert "The Locksmith" in result.rationale
    assert "DOC_IR_bf7db53a" in result.rationale
    assert "DOC_IR_80e4d5d3" in result.rationale


# =====================================================================
# 4. Missing and Ambiguous Evidence
# =====================================================================

def test_burglary_with_unresolved_alias_insufficient_evidence():
    """
    A burglary report (DOC_IR_71acf05c) naming an entity with an alias ('The Wire')
    without an accompanying resolution document must return 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#6819", "OID#8595", ["DOC_IR_71acf05c"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "indirect_unresolved"
    assert "The Wire" in result.rationale
    assert "An alias mention alone does not establish" in result.rationale


def test_missing_joint_incident_case_05_insufficient_evidence():
    """
    Case 05: Primary break-in report DOC_IR_68652ed0 lists 'Unidentified Suspects'.
    The report alone yields 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#4866", "OID#6315", ["DOC_IR_68652ed0"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "absence of a retrieved record cannot be interpreted as proof" in result.rationale


def test_case_05_cdrs_alone_insufficient_evidence_for_burglary():
    """
    Case 05: Intercept CDRs (CDR_aad75224 and CDR_811729fb) establish telecommunications
    between OID#4866 and OID#6315, but without a joint burglary record, must return 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#4866", "OID#6315", ["CDR_aad75224", "CDR_811729fb"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "Communication alone does not establish the benchmark target relationship" in result.rationale


def test_independent_records_proximity_only_insufficient_evidence():
    """
    Case 02: OID#4418 and OID#5590 operate in the same sector in different months.
    Citing independent reports DOC_IR_68ca5aaf and DOC_IR_b45ea549 yields 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#4418", "OID#5590", ["DOC_IR_68ca5aaf", "DOC_IR_b45ea549"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "independent activity" in result.rationale
    assert "proximity alone does not establish" in result.rationale


def test_distractor_evidence_neither_entity_mentioned():
    """
    Distractor report DOC_IR_1ddf34ef (parks shed break-in by OID#9901) mentions neither target entity.
    Returns 'Insufficient Evidence'.
    """
    result = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_1ddf34ef"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "None of the cited documents establish" in result.rationale


# =====================================================================
# 5. Pair-Level vs Incident-Level Contradictions & Solved Status
# =====================================================================

def test_contradictory_alias_attribution_incident_level_finding_pair_insufficient():
    """
    If hypothesis claims relationship between OID#6819 and OID#9999, but cited evidence
    DOC_IR_c1c7b4bb explicitly proves that accomplice 'The Wire' in DOC_IR_71acf05c
    is OID#8595 (not OID#9999), this is an incident-specific contradiction.
    It refutes co-offending for DOC_IR_71acf05c, but does NOT establish that the pair
    shares no other solved burglary case across the evaluation window.
    Pair-level status -> 'Insufficient Evidence', with finding recorded as 'contradictory_attribution'.
    """
    result = verify_hypothesis("OID#6819", "OID#9999", ["DOC_IR_71acf05c", "DOC_IR_c1c7b4bb"])
    assert result.status == "Insufficient Evidence"
    assert result.evidence_class == "insufficient"
    assert "OID#8595" in result.rationale
    assert "contradicting OID#9999" in result.rationale
    assert "does not establish that the pair shares no other solved burglary case" in result.rationale
    assert any(f.finding_type == "contradictory_attribution" for f in result.findings)


def test_explicit_incident_exclusion_incident_finding_pair_insufficient():
    """
    Synthetic fixture: A document explicitly recording that a suspect was cleared or excluded
    from a specific burglary incident refutes co-offending for that incident, but does not
    prove the global negative claim across the full evaluation window.
    Pair-level status -> 'Insufficient Evidence', with finding recorded as 'explicit_exclusion'.
    """
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        doc1 = {
            "doc_id": "DOC_IR_a1a1a1a1",
            "doc_type": "incident_report",
            "timestamp": "2020-03-01 02:00:00",
            "text_content": (
                "INCIDENT REPORT [DOC_IR_a1a1a1a1] - CASE INC-2020-1111\n"
                "Entry Method: Forced lock on rear entrance\n"
                "Suspects/Persons of Interest: OID#1111, OID#2222\n"
                "NARRATIVE SUMMARY: Commercial burglary investigated. Suspects detained on scene."
            ),
            "metadata": {"incident_id": "INC-2020-1111"}
        }
        doc2 = {
            "doc_id": "DOC_IR_b2b2b2b2",
            "doc_type": "incident_report",
            "timestamp": "2020-03-02 10:00:00",
            "text_content": (
                "INCIDENT REPORT [DOC_IR_b2b2b2b2] - CASE INC-2020-1111\n"
                "Suspects/Persons of Interest: OID#2222\n"
                "NARRATIVE SUMMARY: Followup investigation: Subject OID#2222 was investigated "
                "and cleared of all involvement in the break-in."
            ),
            "metadata": {"incident_id": "INC-2020-1111"}
        }
        f.write(json.dumps(doc1) + "\n")
        f.write(json.dumps(doc2) + "\n")
        temp_path = f.name

    try:
        verifier = HypothesisVerifier(corpus_path=temp_path)
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_a1a1a1a1", "DOC_IR_b2b2b2b2"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "cleared of all involvement" in result.rationale
        assert "does not establish that the pair shares no other solved burglary case" in result.rationale
        assert any(f.finding_type == "explicit_exclusion" for f in result.findings)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_global_contradiction_incarceration_rules_out_target_unsupported():
    """
    Synthetic fixture: Evidence documenting that an entity was continuously incarcerated
    spanning the entire evaluation window logically rules out participation in any shared
    burglary co-offending. Pair-level status -> 'Unsupported'.
    """
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        doc1 = {
            "doc_id": "DOC_IR_a1a1a1a1",
            "doc_type": "incident_report",
            "timestamp": "2020-03-01 02:00:00",
            "text_content": (
                "INCIDENT REPORT [DOC_IR_a1a1a1a1] - CASE INC-2020-1111\n"
                "Entry Method: Forced lock on rear entrance\n"
                "Suspects/Persons of Interest: OID#1111, OID#2222\n"
                "NARRATIVE SUMMARY: Commercial burglary investigated. Suspects detained."
            ),
            "metadata": {"incident_id": "INC-2020-1111"}
        }
        doc2 = {
            "doc_id": "DOC_IR_c3c3c3c3",
            "doc_type": "incident_report",
            "timestamp": "2020-07-01 09:00:00",
            "text_content": (
                "INCIDENT REPORT [DOC_IR_c3c3c3c3] - CASE INC-2020-9999\n"
                "Suspects/Persons of Interest: OID#2222\n"
                "NARRATIVE SUMMARY: Institutional audit confirms OID#2222 was in continuous custodial detention "
                "and continuously incarcerated throughout the entire evaluation window, precluding any community offenses."
            ),
            "metadata": {"incident_id": "INC-2020-9999"}
        }
        f.write(json.dumps(doc1) + "\n")
        f.write(json.dumps(doc2) + "\n")
        temp_path = f.name

    try:
        verifier = HypothesisVerifier(corpus_path=temp_path)
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_a1a1a1a1", "DOC_IR_c3c3c3c3"])
        assert result.status == "Unsupported"
        assert result.evidence_class == "contradictory"
        assert "Global contradictory evidence" in result.rationale
        assert "continuously incarcerated" in result.rationale
        assert any(f.finding_type == "global_exclusion" for f in result.findings)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_joint_burglary_solved_status_supported():
    """
    A joint burglary report documenting apprehension/detention or verified clearance
    establishes a solved case -> 'Supported'.
    """
    result = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf"])
    assert result.status == "Supported"
    assert result.evidence_class == "direct"
    assert any(f.finding_type == "direct_burglary_co_offending" for f in result.findings)
    assert "clearance/apprehension verified" in result.rationale or "DOC_IR_68ca5aaf" in result.rationale


def test_joint_burglary_unsolved_status_insufficient_evidence():
    """
    A joint burglary report where perpetrators departed and case remains unsolved
    does NOT establish a *solved* burglary case -> 'Insufficient Evidence'.
    """
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        doc = {
            "doc_id": "DOC_IR_e1e1e1e1",
            "doc_type": "incident_report",
            "timestamp": "2020-04-10 03:00:00",
            "text_content": (
                "INCIDENT REPORT [DOC_IR_e1e1e1e1] - CASE INC-2020-5555\n"
                "Entry Method: Rear window forced open\n"
                "Suspects/Persons of Interest: OID#1111, OID#2222\n"
                "NARRATIVE SUMMARY: Commercial burglary reported. Perpetrators departed the scene "
                "prior to law enforcement arrival; case remains unsolved."
            ),
            "metadata": {"incident_id": "INC-2020-5555"}
        }
        f.write(json.dumps(doc) + "\n")
        temp_path = f.name

    try:
        verifier = HypothesisVerifier(corpus_path=temp_path)
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_e1e1e1e1"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "unsolved" in result.rationale
        assert "strictly requires evidence of a shared *solved* burglary case" in result.rationale
        assert any(f.finding_type == "unsolved_burglary_incident" for f in result.findings)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_joint_burglary_unknown_status_insufficient_evidence():
    """
    A joint burglary report listing suspects without documentation of arrest, detention,
    identification, or case closure has unknown solved status -> 'Insufficient Evidence'.
    """
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        doc = {
            "doc_id": "DOC_IR_f2f2f2f2",
            "doc_type": "incident_report",
            "timestamp": "2020-04-12 04:00:00",
            "text_content": (
                "INCIDENT REPORT [DOC_IR_f2f2f2f2] - CASE INC-2020-7777\n"
                "Entry Method: Pried warehouse latch\n"
                "Suspects/Persons of Interest: OID#1111, OID#2222\n"
                "NARRATIVE SUMMARY: Alarm triggered at storage facility. OID#1111 and OID#2222 were named "
                "as persons of interest in preliminary intake. Investigation is ongoing."
            ),
            "metadata": {"incident_id": "INC-2020-7777"}
        }
        f.write(json.dumps(doc) + "\n")
        temp_path = f.name

    try:
        verifier = HypothesisVerifier(corpus_path=temp_path)
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_f2f2f2f2"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "unverified" in result.rationale or "unknown" in result.rationale
        assert "strictly requires evidence of a shared *solved* burglary case" in result.rationale
        assert any(f.finding_type == "unverified_status_burglary" for f in result.findings)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_distinction_unsupported_vs_insufficient_evidence():
    """
    Verifies the fundamental semantic distinction across three tiers:
    1. Missing records -> 'Insufficient Evidence' (absence != proof of non-association).
    2. Incident-specific contradiction -> 'Insufficient Evidence' at pair level (finding preserved).
    3. Global contradiction (continuous incarceration across window) -> 'Unsupported'.
    """
    # 1. Missing records
    res_insufficient = verify_hypothesis("OID#4418", "OID#5590", ["DOC_IR_68ca5aaf", "DOC_IR_b45ea549"])
    assert res_insufficient.status == "Insufficient Evidence"
    assert "independent activity" in res_insufficient.rationale

    # 2. Incident-specific contradiction
    res_incident_contra = verify_hypothesis("OID#6819", "OID#9999", ["DOC_IR_71acf05c", "DOC_IR_c1c7b4bb"])
    assert res_incident_contra.status == "Insufficient Evidence"
    assert "incident-level contradiction" in res_incident_contra.rationale
    assert any(f.finding_type == "contradictory_attribution" for f in res_incident_contra.findings)

    # 3. Global contradiction
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        doc = {
            "doc_id": "DOC_IR_d3d3d3d3",
            "doc_type": "incident_report",
            "timestamp": "2020-07-01 09:00:00",
            "text_content": (
                "INCIDENT REPORT [DOC_IR_d3d3d3d3] - CASE INC-2020-9999\n"
                "Suspects/Persons of Interest: OID#9999\n"
                "NARRATIVE SUMMARY: Official audit confirms OID#9999 was continuously incarcerated throughout "
                "the entire evaluation window, precluding any community offenses."
            ),
            "metadata": {"incident_id": "INC-2020-9999"}
        }
        f.write(json.dumps(doc) + "\n")
        temp_path = f.name

    try:
        verifier = HypothesisVerifier(corpus_path=temp_path)
        res_global = verifier.verify("OID#6819", "OID#9999", ["DOC_IR_d3d3d3d3"])
        assert res_global.status == "Unsupported"
        assert res_global.evidence_class == "contradictory"
        assert "Global contradictory evidence" in res_global.rationale
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@contextlib.contextmanager
def synthetic_corpus(docs):
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc) + "\n")
        temp_path = f.name
    try:
        yield HypothesisVerifier(corpus_path=temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# =====================================================================
# 5A. Solved-Status Extraction Edge Cases (Phase 2D.3 Audit 1)
# =====================================================================

def test_solved_status_positive_clearance_supported():
    """
    Case 1: Positive clearance - An explicit arrest or verified clearance statement
    on scene can establish solved status when qualifying joint-burglary evidence is present.
    """
    doc = {
        "doc_id": "DOC_IR_11111111",
        "doc_type": "incident_report",
        "timestamp": "2020-03-15 03:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_11111111] - CASE INC-2020-1111\n"
            "Date: 2020-03-15 03:00:00 | Sector: Sector-North\n"
            "Entry Method: Rear window forced open with crowbar\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Commercial burglary investigated. Responding units detained OID#1111 "
            "and apprehended OID#2222 on scene in possession of stolen electronics. Suspects placed under arrest."
        ),
        "metadata": {"incident_id": "INC-2020-1111"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_11111111"])
        assert result.status == "Supported"
        assert result.evidence_class == "direct"
        assert any(f.finding_type == "direct_burglary_co_offending" for f in result.findings)


def test_solved_status_negated_arrest_insufficient_evidence():
    """
    Case 2: Negated arrest - 'The suspect was not arrested' must NOT establish solved status.
    Without confirmed clearance, the joint burglary returns 'Insufficient Evidence'.
    """
    doc = {
        "doc_id": "DOC_IR_22222222",
        "doc_type": "incident_report",
        "timestamp": "2020-03-20 02:30:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_22222222] - CASE INC-2020-2222\n"
            "Date: 2020-03-20 02:30:00 | Sector: Sector-East\n"
            "Entry Method: Front deadbolt lock pried open\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Commercial break-in investigated. OID#1111 and OID#2222 were named as suspects. "
            "Responding units arrived after subjects fled; the suspects were not arrested and no arrest was made."
        ),
        "metadata": {"incident_id": "INC-2020-2222"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_22222222"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "strictly requires evidence of a shared *solved* burglary case" in result.rationale


def test_solved_status_failed_attempted_arrest_insufficient_evidence():
    """
    Case 3: Failed or attempted arrest - 'Officers attempted to arrest the suspect but failed'
    must NOT establish solved status.
    """
    doc = {
        "doc_id": "DOC_IR_33333333",
        "doc_type": "incident_report",
        "timestamp": "2020-04-05 01:15:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_33333333] - CASE INC-2020-3333\n"
            "Date: 2020-04-05 01:15:00 | Sector: Sector-South\n"
            "Entry Method: Rear sliding glass door forced open\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Residential burglary investigated. Officers attempted to arrest the suspects but failed "
            "as both individuals evaded arrest and fled through the back alley."
        ),
        "metadata": {"incident_id": "INC-2020-3333"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_33333333"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "strictly requires evidence of a shared *solved* burglary case" in result.rationale


def test_solved_status_uncertainty_insufficient_evidence():
    """
    Case 4: Uncertainty - 'The suspect may have been arrested' must NOT establish solved status.
    """
    doc = {
        "doc_id": "DOC_IR_44444444",
        "doc_type": "incident_report",
        "timestamp": "2020-04-18 04:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_44444444] - CASE INC-2020-4444\n"
            "Date: 2020-04-18 04:00:00 | Sector: Sector-West\n"
            "Entry Method: Commercial roll-up door latch compromised\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Warehouse burglary reported. Preliminary field notes state the suspects may have been arrested "
            "in an adjacent district, but unconfirmed arrest reports have not been validated. Investigation remains ongoing."
        ),
        "metadata": {"incident_id": "INC-2020-4444"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_44444444"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "strictly requires evidence of a shared *solved* burglary case" in result.rationale


def test_solved_status_historical_references_insufficient_evidence():
    """
    Case 5: Historical references - A statement that another person was previously arrested
    must NOT establish that the current incident was solved.
    """
    doc = {
        "doc_id": "DOC_IR_55555555",
        "doc_type": "incident_report",
        "timestamp": "2020-05-02 02:45:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_55555555] - CASE INC-2020-5555\n"
            "Date: 2020-05-02 02:45:00 | Sector: Sector-Central\n"
            "Entry Method: Basement window pried open\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Commercial break-in investigated. Record check indicates OID#9999 was previously arrested "
            "in 2018 on unrelated charges. Regarding current break-in, no suspects were apprehended and investigation continues."
        ),
        "metadata": {"incident_id": "INC-2020-5555"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_55555555"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "strictly requires evidence of a shared *solved* burglary case" in result.rationale


def test_solved_status_unsolved_not_overridden_by_unrelated_cctv_or_arrest():
    """
    Case 6: Unsolved evidence - 'The case remains unsolved' must NOT be overridden
    by unrelated mentions of arrest, CCTV, or identification.
    """
    doc1 = {
        "doc_id": "DOC_IR_66666661",
        "doc_type": "incident_report",
        "timestamp": "2020-05-10 03:20:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_66666661] - CASE INC-2020-6661\n"
            "Date: 2020-05-10 03:20:00 | Sector: Sector-North\n"
            "Entry Method: Skylight hatch cut open\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Commercial burglary. CCTV footage recorded two individuals entering. "
            "However, perpetrators departed prior to arrival and the case remains unsolved."
        ),
        "metadata": {"incident_id": "INC-2020-6661"}
    }
    with synthetic_corpus([doc1]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_66666661"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert any(f.finding_type == "unsolved_burglary_incident" for f in result.findings)
        assert "unsolved" in result.rationale

    doc2 = {
        "doc_id": "DOC_IR_66666662",
        "doc_type": "incident_report",
        "timestamp": "2020-05-12 04:10:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_66666662] - CASE INC-2020-6662\n"
            "Date: 2020-05-12 04:10:00 | Sector: Sector-North\n"
            "Entry Method: Rear loading door forced open\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Pharmacy burglary. Patrol units arrested an unrelated trespasser in the area, "
            "but perpetrators of the pharmacy burglary were not identified and the case remains unsolved."
        ),
        "metadata": {"incident_id": "INC-2020-6662"}
    }
    with synthetic_corpus([doc2]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_66666662"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert any(f.finding_type == "unsolved_burglary_incident" for f in result.findings)


def test_solved_status_unknown_status_insufficient_evidence():
    """
    Case 7: Unknown status - A joint-suspect report without reliable clearance evidence
    must return 'Insufficient Evidence'.
    """
    doc = {
        "doc_id": "DOC_IR_77777777",
        "doc_type": "incident_report",
        "timestamp": "2020-05-25 01:50:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_77777777] - CASE INC-2020-7777\n"
            "Date: 2020-05-25 01:50:00 | Sector: Sector-East\n"
            "Entry Method: Rear latch jimmied\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Alarm triggered at storage facility. OID#1111 and OID#2222 were named "
            "as persons of interest in preliminary intake. Case transferred to investigative division."
        ),
        "metadata": {"incident_id": "INC-2020-7777"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_77777777"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert any(f.finding_type == "unverified_status_burglary" for f in result.findings)


def test_solved_status_mere_cctv_and_fingerprints_not_positive_id():
    """
    Case 8: CCTV & forensic evidence - Mere mention of CCTV or fingerprints must NOT count
    as positive identification. Requires an explicit, contextually valid identification statement.
    """
    doc = {
        "doc_id": "DOC_IR_88888888",
        "doc_type": "incident_report",
        "timestamp": "2020-06-01 03:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_88888888] - CASE INC-2020-8888\n"
            "Date: 2020-06-01 03:00:00 | Sector: Sector-West\n"
            "Entry Method: Pried window lock\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Commercial break-in investigated. CCTV footage recorded two masked individuals "
            "entering through the rear. Forensic investigators lifted latent fingerprints from the counter. "
            "No identification has been established from the prints or video."
        ),
        "metadata": {"incident_id": "INC-2020-8888"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_88888888"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert any(f.finding_type == "unverified_status_burglary" for f in result.findings)


def test_solved_status_explicit_forensic_and_cctv_identification_supported():
    """
    Case 8 (counterpart): Explicit contextually valid identification statements via forensics
    and CCTV surveillance properly establish solved status when joint burglary evidence is present.
    """
    # Forensic positive identification
    doc1 = {
        "doc_id": "DOC_IR_88888881",
        "doc_type": "incident_report",
        "timestamp": "2020-06-05 02:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_88888881] - CASE INC-2020-8881\n"
            "Date: 2020-06-05 02:00:00 | Sector: Sector-East\n"
            "Entry Method: Window forced open with pry bar\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Burglary investigation. Forensic latent fingerprints recovered from the exterior frame "
            "positively identified OID#1111 and OID#2222 as perpetrators."
        ),
        "metadata": {"incident_id": "INC-2020-8881"}
    }
    with synthetic_corpus([doc1]) as verifier:
        res1 = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_88888881"])
        assert res1.status == "Supported"
        assert res1.evidence_class == "direct"

    # CCTV positive identification
    doc2 = {
        "doc_id": "DOC_IR_88888882",
        "doc_type": "incident_report",
        "timestamp": "2020-06-10 03:30:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_88888882] - CASE INC-2020-8882\n"
            "Date: 2020-06-10 03:30:00 | Sector: Sector-Central\n"
            "Entry Method: Padlock cut open\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Commercial burglary. CCTV footage recorded and positively identified OID#1111 "
            "and OID#2222 carrying merchandise from the storefront."
        ),
        "metadata": {"incident_id": "INC-2020-8882"}
    }
    with synthetic_corpus([doc2]) as verifier:
        res2 = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_88888882"])
        assert res2.status == "Supported"
        assert res2.evidence_class == "direct"


# =====================================================================
# 5B. Complete 'Supported' Decision Audits (Phase 2D.3 Audit 2)
# =====================================================================

def test_supported_requires_burglary_not_non_burglary_incident():
    """
    A non-burglary report (e.g. simple altercation / traffic offense) does not qualify
    even if both entities participated and were arrested. Returns 'Insufficient Evidence'.
    """
    doc = {
        "doc_id": "DOC_IR_99999991",
        "doc_type": "incident_report",
        "timestamp": "2020-03-12 18:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_99999991] - CASE INC-2020-9991\n"
            "Date: 2020-03-12 18:00:00 | Sector: Sector-West\n"
            "Offense: Disorderly conduct and mutual combat in public park\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Patrol officers intervened in a physical altercation between OID#1111 and OID#2222. "
            "Both subjects were detained and arrested for disorderly conduct."
        ),
        "metadata": {"incident_id": "INC-2020-9991"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_99999991"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"


@pytest.mark.parametrize(
    ("text_content", "expected"),
    [
        pytest.param(
            "Theft from a parked vehicle; property was removed.",
            False,
            id="vehicle-theft",
        ),
        pytest.param(
            "INCIDENT REPORT: Theft from construction site container in Sector-Central-East.\nEntry Method: Cut padlock on construction site container.",
            True,
            id="construction-site-container-burglary",
        ),
        pytest.param(
            "Property inventory mentions a construction site container. Entry Method: Cut padlock on a detached storage shed.",
            False,
            id="unrelated-container-and-padlock",
        ),
        pytest.param(
            "Residential burglary report; rear door forced open and entry confirmed.",
            True,
            id="completed-forced-entry-burglary",
        ),
        pytest.param(
            "A shop owner reported a missing tablet. No signs of damage were observed.",
            False,
            id="non-burglary-without-entry-evidence",
        ),
    ],
)
def test_extract_document_facts_classifies_burglary_scope(text_content, expected):
    doc = SanitizedRetrievalDocument(
        doc_id="DOC_IR_99999994",
        doc_type="incident_report",
        timestamp="2020-03-12 18:00:00",
        text_content=text_content,
        metadata={},
    )

    facts = extract_document_facts(doc)

    assert facts["is_burglary_incident"] is expected


def test_supported_requires_joint_participation_not_mere_presence():
    """
    Mere presence of two people in a document (where one is suspect and the other is a reporting
    witness or victim) must NOT establish joint co-offending.
    """
    doc = {
        "doc_id": "DOC_IR_99999992",
        "doc_type": "incident_report",
        "timestamp": "2020-04-14 02:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_99999992] - CASE INC-2020-9992\n"
            "Date: 2020-04-14 02:00:00 | Sector: Sector-North\n"
            "Entry Method: Rear window forced open\n"
            "Suspects/Persons of Interest: OID#1111\n"
            "NARRATIVE SUMMARY: Residential burglary reported by property tenant OID#2222. "
            "Responding officers detained suspect OID#1111 fleeing the scene. Tenant OID#2222 provided witness statement."
        ),
        "metadata": {"incident_id": "INC-2020-9992"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_99999992"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"


def test_supported_requires_incident_within_evaluation_window():
    """
    A solved joint burglary occurring outside the 6-month evaluation window (2020-01-01 to 2020-06-30),
    such as in 2018 or 2019, must return 'Insufficient Evidence'.
    """
    doc = {
        "doc_id": "DOC_IR_99999993",
        "doc_type": "incident_report",
        "timestamp": "2018-05-10 03:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_99999993] - CASE INC-2018-4444\n"
            "Date: 2018-05-10 03:00:00 | Sector: Sector-South\n"
            "Entry Method: Commercial back door pried open\n"
            "Suspects/Persons of Interest: OID#1111, OID#2222\n"
            "NARRATIVE SUMMARY: Historical commercial burglary archive from 2018. Responding officers detained OID#1111 "
            "and OID#2222 on scene in possession of stolen inventory. Charges filed."
        ),
        "metadata": {"incident_id": "INC-2018-4444"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_99999993"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"
        assert "evaluation window" in result.rationale


# =====================================================================
# 5C. Global vs Incident Exclusion Audits (Phase 2D.3 Audit 3)
# =====================================================================

def test_short_detention_does_not_establish_global_unsupported():
    """
    A short detention (e.g. 48-hour temporary custody) does not establish continuous
    custodial incarceration across the entire 6-month window. Returns 'Insufficient Evidence'.
    """
    doc = {
        "doc_id": "DOC_IR_77777771",
        "doc_type": "incident_report",
        "timestamp": "2020-03-05 10:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_77777771] - CASE INC-2020-1010\n"
            "Suspects/Persons of Interest: OID#2222\n"
            "NARRATIVE SUMMARY: Following a traffic violation, OID#2222 was continuously detained for 48 hours "
            "in holding before posting bond and being released."
        ),
        "metadata": {"incident_id": "INC-2020-1010"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_77777771"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"


def test_incomplete_dates_incarceration_does_not_establish_global_unsupported():
    """
    An incarceration statement with incomplete or partial dates (e.g. incarcerated during March only)
    does not prove impossibility across the full 6-month evaluation window. Returns 'Insufficient Evidence'.
    """
    doc = {
        "doc_id": "DOC_IR_77777772",
        "doc_type": "incident_report",
        "timestamp": "2020-04-01 09:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_77777772] - CASE INC-2020-2020\n"
            "Suspects/Persons of Interest: OID#2222\n"
            "NARRATIVE SUMMARY: Correctional records indicate OID#2222 served a 30-day sentence and was incarcerated "
            "from 2020-03-01 to 2020-03-31 before being paroled."
        ),
        "metadata": {"incident_id": "INC-2020-2020"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_77777772"])
        assert result.status == "Insufficient Evidence"
        assert result.evidence_class == "insufficient"


def test_complete_confinement_period_covering_entire_window_establishes_unsupported():
    """
    A clearly documented, complete period of custodial confinement spanning the entire
    6-month evaluation window logically precludes offenses and supports 'Unsupported'.
    """
    doc = {
        "doc_id": "DOC_IR_77777773",
        "doc_type": "incident_report",
        "timestamp": "2020-07-01 08:00:00",
        "text_content": (
            "INCIDENT REPORT [DOC_IR_77777773] - CASE INC-2020-3030\n"
            "Suspects/Persons of Interest: OID#2222\n"
            "NARRATIVE SUMMARY: Corrections department audit confirms OID#2222 was in continuous custodial detention "
            "and continuously incarcerated throughout the entire evaluation window, precluding any community offenses."
        ),
        "metadata": {"incident_id": "INC-2020-3030"}
    }
    with synthetic_corpus([doc]) as verifier:
        result = verifier.verify("OID#1111", "OID#2222", ["DOC_IR_77777773"])
        assert result.status == "Unsupported"
        assert result.evidence_class == "contradictory"
        assert any(f.finding_type == "global_exclusion" for f in result.findings)


# =====================================================================
# 6. Parameter Validation & Edge Case Rejections
# =====================================================================

def test_unknown_document_id_rejection():
    """Supplying an unknown document ID not in the corpus raises ValueError."""
    with pytest.raises(ValueError, match="Unknown document ID 'DOC_IR_ffffffff'"):
        verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_ffffffff"])


def test_malformed_document_id_rejection():
    """Supplying a malformed document ID string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid document ID format"):
        verify_hypothesis("OID#4418", "OID#8864", ["INVALID_DOC_ID"])


def test_duplicate_document_id_rejection():
    """Duplicate document IDs in evidence_ids must be rejected."""
    with pytest.raises(ValueError, match="Duplicate document ID detected"):
        verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf", "DOC_IR_68ca5aaf"])


def test_empty_evidence_ids_rejection():
    """Empty list of evidence IDs raises ValueError."""
    with pytest.raises(ValueError, match="evidence_ids must be a non-empty list"):
        verify_hypothesis("OID#4418", "OID#8864", [])


def test_identical_entities_reflexive_rejection():
    """Hypothesis comparing an entity to itself (reflexive) raises ValueError."""
    with pytest.raises(ValueError, match="Hypothesis entities must be distinct"):
        verify_hypothesis("OID#4418", "OID#4418", ["DOC_IR_68ca5aaf"])


@pytest.mark.parametrize("bad_entity", ["", "4418", "SUSPECT_1", "OID-4418", "oid#4418", None, 4418])
def test_invalid_entity_format_rejection(bad_entity):
    """Malformed entity IDs raise ValueError."""
    with pytest.raises(ValueError, match="Invalid entity identifier"):
        verify_hypothesis(bad_entity, "OID#8864", ["DOC_IR_68ca5aaf"])


# =====================================================================
# 7. Schema Enforcement & Citation Integrity
# =====================================================================

def test_verification_result_schema_strictness():
    """VerificationResult forbids unexpected extra fields."""
    result = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf"])
    dumped = result.model_dump()
    assert "entity_a" in dumped
    assert "entity_b" in dumped
    assert "status" in dumped
    assert "evidence_class" in dumped
    assert "cited_evidence_ids" in dumped
    assert "rationale" in dumped
    assert "findings" in dumped

    # Extra fields must fail validation
    with pytest.raises(ValidationError):
        VerificationResult(**dumped, unexpected_field="leak")


def test_citation_ids_integrity_and_rationale_tracing():
    """
    Every document ID in findings must be strictly in cited_evidence_ids.
    Every factual rationale statement must trace to cited evidence documents.
    """
    result = verify_hypothesis("OID#6819", "OID#8595", ["DOC_IR_71acf05c", "DOC_IR_c1c7b4bb"])
    for finding in result.findings:
        assert finding.doc_id in result.cited_evidence_ids

    # Both documents must be cited in rationale
    assert "DOC_IR_71acf05c" in result.rationale
    assert "DOC_IR_c1c7b4bb" in result.rationale


# =====================================================================
# 8. Firewall Quarantine & Tool Permissions
# =====================================================================

def test_verifier_quarantine_isolation_no_vault_or_provenance_access():
    """
    Static analysis: verify_hypothesis module contains zero references to
    ground_truth.json, pilot_manifest.json, split_manifest.json, or internal_provenance.jsonl.
    """
    verifier_path = os.path.join(REPO_ROOT, "phase2_verification", "verifier.py")
    with open(verifier_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
            assert "ground_truth.json" not in val
            assert "pilot_manifest.json" not in val
            assert "split_manifest.json" not in val
            assert "internal_provenance.jsonl" not in val


def test_verification_output_contains_no_quarantined_tokens():
    """
    Verification results must contain zero source CIDs (CID#xxxx), condition names,
    split assignments, or ground truth labels.
    """
    result = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf", "CDR_055ad8bc"])
    raw_str = result.model_dump_json()

    prohibited_tokens = ["CID#", "CID", "PILOT_CASE", "clean_evidence", "split", "component"]
    for tok in prohibited_tokens:
        assert tok not in raw_str


def test_approved_tools_catalog_and_read_only():
    """The phase2_verification package explicitly exports only approved read-only tools."""
    assert APPROVED_READONLY_TOOLS == ("search_evidence", "verify_hypothesis")


# =====================================================================
# 9. Deterministic Repeatability & Order Symmetry
# =====================================================================

def test_deterministic_behavior_and_entity_order_symmetry():
    """
    Repeated evaluations produce identical results.
    Entity pair ordering (A, B) vs (B, A) produces symmetric status and evidence class.
    """
    res1 = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf"])
    res2 = verify_hypothesis("OID#4418", "OID#8864", ["DOC_IR_68ca5aaf"])
    assert res1.model_dump_json() == res2.model_dump_json()

    res_symmetric = verify_hypothesis("OID#8864", "OID#4418", ["DOC_IR_68ca5aaf"])
    assert res_symmetric.status == res1.status
    assert res_symmetric.evidence_class == res1.evidence_class
    assert res_symmetric.cited_evidence_ids == res1.cited_evidence_ids


# =====================================================================
# 10. Regression Hashes of Frozen Corpus and Vault Manifests
# =====================================================================

def test_frozen_corpus_and_manifests_regression_hashes():
    """
    Verifies that all frozen Phase 2A and Phase 2B.2 manifests and evidence files
    remain completely unchanged before and after Phase 2D/2D.1.
    """
    def file_sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    expected_hashes = {
        os.path.join(REPO_ROOT, "phase2_corpus", "retrieval_documents.jsonl"):
            "a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded",
        os.path.join(REPO_ROOT, "phase2_corpus", "internal_provenance.jsonl"):
            "ae29dcd873a3f87f01dff4e5dceb3edd041caf64e21f7065d74114ad2f9287bc",
        os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "ground_truth.json"):
            "87f84a65111bd38a021860247b53362fbf3f92f284a8a2ccd30eeb4089a42963",
        os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "pilot_manifest.json"):
            "ee376e36dde8378109d60eaa7a37102262d717d56a76fe65337dda2098ee9b50",
        os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "split_manifest.json"):
            "04dc346d4628d1ad59d6b34d3580f6ddb40548e35921f48cc24a0d6a389d0ffd",
    }

    for path, expected_hash in expected_hashes.items():
        actual_hash = file_sha256(path)
        assert actual_hash == expected_hash, f"Frozen artifact {path} modified! Hash: {actual_hash}"
