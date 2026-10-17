"""
Phase 2B.1 Strengthened Evidence Corpus Verification Tests
Tests for:
1. Determinism under fixed seed (byte-for-byte reproducibility).
2. Pydantic schema validation for retrieval documents and internal provenance envelopes.
3. Strict evidence scope (Incident Reports & CDRs only; no pawn logs).
4. ABSOLUTE absence of original source crime IDs (CID#xxxx) from retrieval text, metadata, and doc IDs.
5. Opaque document IDs: strictly hash-based, zero case membership, case numbers, or condition leakage.
6. Zero leakage of ground-truth labels, rationales, conditions, component IDs, or target pairs.
7. Exact 1:1 provenance-to-retrieval reconciliation.
8. Condition operationalization across all 5 conditions.
9. Missing-evidence semantics for Case 05 (primary report absent, CID#2293 unreferenced).
10. Absence of artificial negative assertions.
11. Quarantined vault isolation.
"""

import os
import sys
import re
import json
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VAULT_DIR = os.path.join(REPO_ROOT, "phase2_ground_truth_vault")
CORPUS_DIR = os.path.join(REPO_ROOT, "phase2_corpus")

if VAULT_DIR not in sys.path:
    sys.path.insert(0, VAULT_DIR)
if CORPUS_DIR not in sys.path:
    sys.path.insert(0, CORPUS_DIR)

from schemas import (
    SanitizedRetrievalDocument,
    EvidenceProvenanceEnvelope,
    PoliceIncidentReport,
    CallDetailRecord,
    validate_retrieval_corpus
)
from generate_pilot_evidence import build_pilot_evidence_corpus


@pytest.fixture(scope="module")
def corpus_data():
    retrieval_path = os.path.join(CORPUS_DIR, "retrieval_documents.jsonl")
    prov_path = os.path.join(CORPUS_DIR, "internal_provenance.jsonl")

    assert os.path.exists(retrieval_path), f"Missing {retrieval_path}"
    assert os.path.exists(prov_path), f"Missing {prov_path}"

    with open(retrieval_path, "r", encoding="utf-8") as f:
        retrieval_docs = [json.loads(line) for line in f if line.strip()]

    with open(prov_path, "r", encoding="utf-8") as f:
        provenances = [json.loads(line) for line in f if line.strip()]

    return {"retrieval_docs": retrieval_docs, "provenances": provenances}


@pytest.fixture(scope="module")
def ground_truth_cids():
    """Extract all authentic CIDs from the ground truth vault."""
    manifest_path = os.path.join(VAULT_DIR, "ground_truth.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        gt = json.load(f)
    cids = set()
    for c in gt["cases"]:
        for cid in c.get("shared_crime_ids", []):
            cids.add(cid)
    return cids


def test_generator_determinism():
    """Verify that repeated generator calls produce identical outputs."""
    docs1, provs1 = build_pilot_evidence_corpus()
    docs2, provs2 = build_pilot_evidence_corpus()

    assert json.dumps(docs1, sort_keys=True) == json.dumps(docs2, sort_keys=True)
    assert json.dumps(provs1, sort_keys=True) == json.dumps(provs2, sort_keys=True)


def test_byte_identical_reproducibility():
    """Verify that serializing outputs twice produces byte-for-byte identical content."""
    docs1, provs1 = build_pilot_evidence_corpus()
    docs2, provs2 = build_pilot_evidence_corpus()

    s_ret1 = "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs1).encode("utf-8")
    s_ret2 = "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs2).encode("utf-8")
    assert s_ret1 == s_ret2

    s_prov1 = "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in provs1).encode("utf-8")
    s_prov2 = "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in provs2).encode("utf-8")
    assert s_prov1 == s_prov2


def test_all_retrieval_documents_validate_schemas(corpus_data):
    """Verify that every retrieval document validates against SanitizedRetrievalDocument."""
    docs = corpus_data["retrieval_docs"]
    assert len(docs) == 31

    for d in docs:
        validated = SanitizedRetrievalDocument(**d)
        assert validated.doc_id.startswith(("DOC_IR_", "CDR_"))
        assert validated.doc_type in ["incident_report", "call_detail_record"]
        assert len(validated.text_content) > 20


def test_all_internal_provenance_validate_schemas(corpus_data):
    """Verify that all provenance envelopes validate against EvidenceProvenanceEnvelope."""
    provs = corpus_data["provenances"]
    assert len(provs) == 31

    for p in provs:
        validated = EvidenceProvenanceEnvelope(**p)
        assert validated.is_synthetic is True
        assert validated.generation_seed == 42
        assert validated.generator_version == "pilot_v1.1"
        assert isinstance(validated.underlying_entity_references, list)


def test_evidence_types_strictly_approved(corpus_data):
    """Verify that evidence strictly consists of Incident Reports and CDRs with no disallowed types."""
    docs = corpus_data["retrieval_docs"]
    allowed_types = {"incident_report", "call_detail_record"}
    for d in docs:
        assert d["doc_type"] in allowed_types

    disallowed_keywords = [
        "pawn", "fencing transaction", "bank statement", "wire transfer",
        "financial ledger", "safe deposit"
    ]

    for d in docs:
        text = d["text_content"].lower()
        for bad_kw in disallowed_keywords:
            assert bad_kw not in text, f"Disallowed keyword '{bad_kw}' in doc {d['doc_id']}"


def test_no_original_source_cids_in_retrieval_corpus(corpus_data, ground_truth_cids):
    """
    CRITICAL CHECK: Verify that NO original source crime identifiers (CID#xxxx or CID)
    are exposed anywhere in retrieval text, metadata, or document IDs.
    """
    docs = corpus_data["retrieval_docs"]

    cid_pattern = re.compile(r"\bCID#?\d+\b", re.IGNORECASE)

    for d in docs:
        doc_id = d["doc_id"]
        text = d["text_content"]
        meta = d["metadata"]

        # Check doc_id
        assert not cid_pattern.search(doc_id), f"CID leak in doc_id: {doc_id}"
        assert "CID" not in doc_id.upper(), f"CID substring in doc_id: {doc_id}"

        # Check text_content
        match = cid_pattern.search(text)
        assert not match, f"CID pattern leak '{match.group(0)}' in text of {doc_id}"
        assert "CID#" not in text, f"CID# prefix leak in text of {doc_id}"

        # Check metadata values and keys
        for k, v in meta.items():
            assert not cid_pattern.search(str(k)), f"CID leak in metadata key '{k}' of {doc_id}"
            assert not cid_pattern.search(str(v)), f"CID leak in metadata value '{v}' of {doc_id}"
            assert "CID#" not in str(v), f"CID# in metadata value '{v}' of {doc_id}"

        # Check against ground truth shared crime IDs specifically
        for gt_cid in ground_truth_cids:
            assert gt_cid not in text, f"Ground truth shared CID '{gt_cid}' leaked in text of {doc_id}"
            for v in meta.values():
                assert gt_cid not in str(v), f"Ground truth shared CID '{gt_cid}' leaked in metadata of {doc_id}"


def test_retrieval_document_ids_are_opaque_and_leak_free(corpus_data):
    """
    CRITICAL CHECK: Verify that retrieval document IDs are strictly opaque hashes
    and do not reveal case membership, case numbers, conditions, labels, or original source IDs.
    """
    docs = corpus_data["retrieval_docs"]
    doc_ids = [d["doc_id"] for d in docs]

    # Verify uniqueness
    assert len(doc_ids) == len(set(doc_ids))

    opaque_ir_pattern = re.compile(r"^DOC_IR_[0-9a-f]{8}$")
    opaque_cdr_pattern = re.compile(r"^CDR_[0-9a-f]{8}$")

    for did in doc_ids:
        # Check strict format
        is_valid_format = bool(opaque_ir_pattern.match(did) or opaque_cdr_pattern.match(did))
        assert is_valid_format, f"Doc ID '{did}' does not match opaque hash pattern!"

        # Forbidden semantic substrings
        upper_id = did.upper()
        for forbidden in ["PILOT", "CASE", "PAIR", "COND", "CLEAN", "ALIAS", "MISSING", "DISTRACT", "MIXED", "OID"]:
            assert forbidden not in upper_id, f"Semantic leak '{forbidden}' in doc_id: {did}"


def test_no_leakage_in_retrieval_text_or_metadata(corpus_data):
    """
    Ensure zero leakage of ground-truth labels, rationales, conditions, component IDs,
    or target pairs into retrieval text or metadata.
    """
    docs = corpus_data["retrieval_docs"]

    forbidden_text_phrases = [
        "ground truth", "is_co_offender", "label: 1", "label: 0",
        "clean_evidence", "alias_ambiguity", "missing_evidence", "distractors",
        "mixed_difficulty", "target_pair", "pair_label",
        "component 0", "component 1", "comp 0", "comp 1"
    ]

    forbidden_metadata_keys = {
        "label", "is_co_offender", "ground_truth", "condition", "rationale",
        "target_pair", "pair_label", "shared_cids", "observed_edge",
        "component", "components", "component_id", "comp_id", "is_distractor",
        "case_id", "pilot_case"
    }

    for d in docs:
        text = d["text_content"].lower()
        for phrase in forbidden_text_phrases:
            assert phrase not in text, f"Leakage: Forbidden phrase '{phrase}' in text of {d['doc_id']}"

        for k in d["metadata"].keys():
            assert k.lower() not in forbidden_metadata_keys, (
                f"Leakage: Forbidden metadata key '{k}' found in doc {d['doc_id']}"
            )


def test_provenance_reconciliation_1to1(corpus_data):
    """Verify exact 1:1 reconciliation between retrieval documents and provenance envelopes."""
    docs = corpus_data["retrieval_docs"]
    provs = corpus_data["provenances"]

    assert len(docs) == len(provs)

    doc_ids = [d["doc_id"] for d in docs]
    prov_doc_ids = [p["document_id"] for p in provs]

    assert doc_ids == prov_doc_ids
    assert len(set(doc_ids)) == len(doc_ids)

    # Verify provenance maintains ground truth mapping
    for p in provs:
        assert p["source_incident_cid"].startswith("CID#")
        assert p["ground_truth_case_id"].startswith("PILOT_CASE_")


def test_condition_clean_evidence(corpus_data):
    """Verify clean evidence implementation for Case 01 and Case 02."""
    docs = corpus_data["retrieval_docs"]
    provs = corpus_data["provenances"]

    c1_provs = [p for p in provs if p.get("ground_truth_case_id") == "PILOT_CASE_01"]
    c2_provs = [p for p in provs if p.get("ground_truth_case_id") == "PILOT_CASE_02"]

    assert len(c1_provs) == 3
    assert len(c2_provs) == 2

    c1_doc_ids = {p["document_id"] for p in c1_provs}
    c1_docs = [d for d in docs if d["doc_id"] in c1_doc_ids]
    c1_text = " ".join(d["text_content"] for d in c1_docs)
    assert "OID#4418" in c1_text
    assert "OID#8864" in c1_text


def test_condition_alias_ambiguity_genuine_challenge(corpus_data):
    """
    Verify alias condition for Case 03:
    'The Wire' alias is used in primary report; separate field record links moniker to OID#8595.
    Neither document contains both canonical IDs (OID#6819 and OID#8595) together.
    """
    docs = {d["doc_id"]: d for d in corpus_data["retrieval_docs"]}
    provs = {p["document_id"]: p for p in corpus_data["provenances"]}

    # Identify Case 03 documents via provenance
    c3_doc_ids = [p["document_id"] for p in provs.values() if p.get("ground_truth_case_id") == "PILOT_CASE_03"]
    assert len(c3_doc_ids) == 3

    # Primary incident report
    rep_primary = [docs[did] for did in c3_doc_ids if provs[did]["generation_rule"] == "RULE_ALIAS_INCIDENT_REPORT_PRIMARY"][0]
    assert "OID#6819" in rep_primary["text_content"]
    assert "The Wire" in rep_primary["text_content"]
    assert "OID#8595" not in rep_primary["text_content"]  # Cannot expose canonical target in same doc!

    # Field resolution record
    rep_field = [docs[did] for did in c3_doc_ids if provs[did]["generation_rule"] == "RULE_ALIAS_RESOLUTION_FIELD_RECORD"][0]
    assert "OID#8595" in rep_field["text_content"]
    assert "The Wire" in rep_field["text_content"]
    assert "OID#6819" not in rep_field["text_content"]  # Cannot expose partner in field stop!


def test_condition_missing_evidence_case_05_semantics(corpus_data):
    """
    Verify missing evidence condition for Case 05:
    1. Original crime CID#2293 is nowhere in the retrieval corpus.
    2. Primary joint arrest narrative is withheld; no incident report lists both suspects.
    3. Partial report uses synthetic incident ID with unidentified suspects.
    4. Linkage is synthesized via circumstantial pre/post incident CDRs.
    """
    docs = corpus_data["retrieval_docs"]
    provs = corpus_data["provenances"]

    # Verify CID#2293 does not appear anywhere
    for d in docs:
        assert "CID#2293" not in d["text_content"]
        assert "2293" not in d["doc_id"]
        for v in d["metadata"].values():
            assert "2293" not in str(v)

    # Verify no incident report mentions both OID#4866 and OID#6315
    for d in docs:
        if d["doc_type"] == "incident_report":
            text = d["text_content"]
            assert not ("OID#4866" in text and "OID#6315" in text), (
                f"Leakage violation: Incident report {d['doc_id']} contains both suspects, "
                "violating missing evidence condition!"
            )

    # Verify circumstantial CDRs exist
    c5_provs = [p for p in provs if p.get("ground_truth_case_id") == "PILOT_CASE_05"]
    c5_cdrs = [p for p in c5_provs if p["document_id"].startswith("CDR_")]
    assert len(c5_cdrs) == 3


def test_condition_distractors_present(corpus_data):
    """Verify that distractor incident reports exist and do not leak target labels."""
    provs = corpus_data["provenances"]
    distractor_provs = [p for p in provs if "DISTRACTOR" in p["generation_rule"]]

    assert len(distractor_provs) >= 4

    docs = {d["doc_id"]: d for d in corpus_data["retrieval_docs"]}
    for dp in distractor_provs:
        doc = docs[dp["document_id"]]
        # Ensure retriever metadata does NOT leak 'is_distractor'
        assert "is_distractor" not in doc["metadata"]


def test_condition_mixed_difficulty(corpus_data):
    """Verify mixed difficulty operationalization (alias + circumstantial + distractors)."""
    provs = corpus_data["provenances"]
    c9_provs = [p for p in provs if p.get("ground_truth_case_id") == "PILOT_CASE_09"]

    rules = {p["generation_rule"] for p in c9_provs}
    assert "RULE_MIXED_INCIDENT_REPORT_ALIAS_PRIMARY" in rules
    assert "RULE_MIXED_ALIAS_RESOLUTION" in rules
    assert "RULE_CDR_MIXED_CO_OFFENDER" in rules
    assert "RULE_DISTRACTOR_LOCAL_INCIDENT" in rules


def test_negative_cases_no_artificial_non_association(corpus_data):
    """Ensure negative cases contain no fabricated claims of non-association."""
    docs = corpus_data["retrieval_docs"]
    forbidden_negative_claims = [
        "never communicated", "never spoke", "no relationship",
        "definitely innocent", "proven negative", "unrelated suspects",
        "not accomplices"
    ]

    for d in docs:
        text = d["text_content"].lower()
        for claim in forbidden_negative_claims:
            assert claim not in text, f"Artificial non-association claim '{claim}' in doc {d['doc_id']}"


def test_vault_quarantine_isolation(corpus_data):
    """Verify that ground_truth.json is completely isolated from the retrieval corpus."""
    docs = corpus_data["retrieval_docs"]
    for d in docs:
        assert "ground_truth" not in d["doc_id"]
        assert "quarantined" not in d["text_content"].lower()


# ==============================================================================
# PHASE 2B.2 DELIBERATE INJECTION AND SCHEMA HARDENING TESTS
# ==============================================================================

def test_schema_rejects_injected_original_cids():
    """Verify that deliberately injected original CIDs are rejected across all channels."""
    cids = ["CID#6456", "CID5170", "cid#2293", "CID-3528", "CID: 4965", "CID#1124"]

    # 1. Injected in text_content
    for cid in cids:
        with pytest.raises(ValueError, match="Original crime identifier found in text_content"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content=f"Officers responded to premises relating to incident {cid} at Sector-Central.",
                metadata={"sector": "Sector-Central"}
            )

    # 2. Injected in doc_id
    with pytest.raises(ValueError, match="Suspicious identifier token 'CID'|Leakage/Format violation"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_cid6456",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"sector": "Sector-Central"}
        )

    # 3. Injected in metadata key
    for bad_key in ["cid_6456", "source_cid", "original_cid", "CID"]:
        with pytest.raises(ValueError, match="Forbidden.*key"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={bad_key: "val", "sector": "Sector-Central"}
            )

    # 4. Injected in metadata value
    for cid in cids:
        with pytest.raises(ValueError, match="Original crime identifier found in metadata"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={"incident_ref": cid, "sector": "Sector-Central"}
            )


def test_schema_rejects_injected_pilot_case_ids():
    """Verify that pilot-case identifiers are rejected in text, doc_id, and metadata."""
    pilot_ids = ["PILOT_CASE_01", "PILOT_01", "pilot_case_05", "PILOT-CASE-02"]

    # 1. Injected in text_content
    for pid in pilot_ids:
        with pytest.raises(ValueError, match="Pilot-case identifier found in text_content"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content=f"Report associated with internal study {pid} at Sector-Central.",
                metadata={"sector": "Sector-Central"}
            )

    # 2. Injected in doc_id
    for bad_id in ["DOC_IR_PILOT_01", "CDR_PILOT_01_01"]:
        with pytest.raises(ValueError, match="Suspicious identifier token 'PILOT'|Leakage/Format violation"):
            SanitizedRetrievalDocument(
                doc_id=bad_id,
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={"sector": "Sector-Central"}
            )

    # 3. Injected in metadata key
    for bad_key in ["pilot_case_id", "case_id", "pilotcase"]:
        with pytest.raises(ValueError, match="Forbidden metadata key"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={bad_key: 1, "sector": "Sector-Central"}
            )

    # 4. Injected in metadata value
    for pid in pilot_ids:
        with pytest.raises(ValueError, match="Pilot-case identifier found in metadata"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={"case_ref": pid, "sector": "Sector-Central"}
            )


def test_schema_rejects_injected_condition_names():
    """Verify that experimental condition names are rejected in text and metadata."""
    conditions = [
        "clean_evidence", "alias_ambiguity", "missing_evidence",
        "distractors", "mixed_difficulty"
    ]

    for cond in conditions:
        # In text
        with pytest.raises(ValueError, match="Evaluation condition name"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content=f"Report generated under experimental regime {cond} at Sector-Central.",
                metadata={"sector": "Sector-Central"}
            )

        # In metadata key
        with pytest.raises(ValueError, match="Forbidden metadata key"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={"condition": cond, "sector": "Sector-Central"}
            )

        # In metadata value
        with pytest.raises(ValueError, match="Condition string"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={"eval_regime": cond, "sector": "Sector-Central"}
            )


def test_schema_rejects_injected_ground_truth_labels_and_rationales():
    """Verify that ground-truth labels, co-offender assertions, and rationales are rejected."""
    # In text
    label_texts = [
        "GROUND TRUTH IS_CO_OFFENDER: True",
        "LABEL: 1",
        "LABEL: 0",
        "GROUND TRUTH positive co-offending confirmed",
        "TARGET_PAIR verified"
    ]
    for lt in label_texts:
        with pytest.raises(ValueError, match="Forbidden string|Leakage violation"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content=f"Summary of findings: {lt} during investigation.",
                metadata={"sector": "Sector-Central"}
            )

    # In metadata keys
    forbidden_keys = [
        "label", "ground_truth_label", "is_co_offender", "co_offender",
        "cooffender", "rationale", "observed_edge", "pair_label"
    ]
    for fk in forbidden_keys:
        with pytest.raises(ValueError, match="Forbidden metadata key"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={fk: 1, "sector": "Sector-Central"}
            )


def test_schema_rejects_injected_component_identifiers():
    """Verify that component identifiers are rejected in metadata."""
    comp_keys = ["component", "component_id", "comp_id", "comp", "components"]
    for ck in comp_keys:
        with pytest.raises(ValueError, match="Forbidden metadata key"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={ck: 1, "sector": "Sector-Central"}
            )


def test_schema_rejects_injected_target_pair_fields():
    """Verify that target-pair metadata keys and variations are rejected."""
    pair_keys = ["target_pair", "targetpair", "Target-Pair", "Target_Pair", "pair"]
    for pk in pair_keys:
        with pytest.raises(ValueError, match="Forbidden metadata key"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={pk: ["OID#4418", "OID#8864"], "sector": "Sector-Central"}
            )


def test_schema_rejects_suspicious_key_variations():
    """Verify that case and separator variations of forbidden keys are rejected."""
    variations = [
        "Target_Pair", "target-pair", "TargetPair", "Case-Id", "CASE_ID",
        "ground_truth_label", "GroundTruth", "co_offender", "Co-Offender",
        "observed_edge", "shared_cid", "is_distractor", "distractor"
    ]
    for vk in variations:
        with pytest.raises(ValueError, match="Forbidden metadata key"):
            SanitizedRetrievalDocument(
                doc_id="DOC_IR_12345678",
                doc_type="incident_report",
                timestamp="2020-01-17 02:40:00",
                text_content="Clean narrative text without any leaks at Sector-Central.",
                metadata={vk: "leak_val", "sector": "Sector-Central"}
            )


def test_schema_rejects_nested_metadata_leakage():
    """Verify that leakage buried in nested dictionaries or lists is rejected."""
    # Nested dict with CID
    with pytest.raises(ValueError, match="Original crime identifier found in metadata"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"nested_audit": {"source": "CID#6456"}, "sector": "Sector-Central"}
        )

    # Nested list with CID
    with pytest.raises(ValueError, match="Original crime identifier found in metadata"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"prior_incidents": ["INC-2020-1111", "CID#5170"], "sector": "Sector-Central"}
        )

    # Nested dict in list with pilot case
    with pytest.raises(ValueError, match="Pilot-case identifier found in metadata"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"records": [{"case_ref": "PILOT_CASE_07"}], "sector": "Sector-Central"}
        )

    # Nested list with condition name
    with pytest.raises(ValueError, match="Condition string"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"eval_chain": ["baseline", "clean_evidence"], "sector": "Sector-Central"}
        )


def test_schema_rejects_malformed_retrieval_payloads():
    """Verify that malformed or unexpected payloads are rejected immediately."""
    # Extra unexpected attribute (forbid extra fields)
    with pytest.raises(Exception):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"sector": "Sector-Central"},
            unexpected_field="disallowed_extra"
        )

    # Invalid doc_type
    with pytest.raises(ValueError, match="Malformed payload: Invalid doc_type"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="pawn_ticket",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"sector": "Sector-Central"}
        )

    # Malformed / short timestamp
    with pytest.raises(ValueError, match="Malformed payload: Invalid or missing timestamp"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="incident_report",
            timestamp="2020-01",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"sector": "Sector-Central"}
        )

    # Short text content (< 20 chars)
    with pytest.raises(ValueError, match="Malformed payload: text_content must be non-empty string and at least 20"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_12345678",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Short note.",
            metadata={"sector": "Sector-Central"}
        )

    # Non-conforming doc_id
    with pytest.raises(ValueError, match="Leakage/Format violation"):
        SanitizedRetrievalDocument(
            doc_id="DOC_IR_INVALID_ID",
            doc_type="incident_report",
            timestamp="2020-01-17 02:40:00",
            text_content="Clean narrative text without any leaks at Sector-Central.",
            metadata={"sector": "Sector-Central"}
        )


def test_schema_allows_legitimate_evidence_attributes():
    """
    Verify that legitimate evidence is NOT rejected when mentioning:
    - Entity IDs (OID#xxx)
    - Aliases ("The Wire", "Spider")
    - Incident dates ("2020-01-17")
    - Synthetic incident references ("INC-2020-7182")
    - Legitimate operational metadata (sector, date, caller_id, callee_id)
    """
    # 1. Incident report with entity IDs, alias, synthetic ref, date
    doc_ir = SanitizedRetrievalDocument(
        doc_id="DOC_IR_68ca5aaf",
        doc_type="incident_report",
        timestamp="2020-01-17 02:40:00",
        text_content=(
            "INCIDENT REPORT [DOC_IR_68ca5aaf] - CASE INC-2020-7182\n"
            "Date: 2020-01-17 02:40:00 | Sector: Sector-Central-East\n"
            "Suspects/Persons of Interest: OID#4418 (known on street as 'The Wire'), OID#8864\n"
            "Patrol officers detained OID#4418 and OID#8864 following an alarm trigger."
        ),
        metadata={
            "incident_id": "INC-2020-7182",
            "sector": "Sector-Central-East",
            "date": "2020-01-17"
        }
    )
    assert doc_ir.doc_id == "DOC_IR_68ca5aaf"

    # 2. CDR with caller, callee, sector, date
    doc_cdr = SanitizedRetrievalDocument(
        doc_id="CDR_055ad8bc",
        doc_type="call_detail_record",
        timestamp="2020-01-17 01:15:22",
        text_content=(
            "COMMUNICATION INTERCEPT LOG [CDR_055ad8bc]\n"
            "Timestamp: 2020-01-17 01:15:22 | Type: VOICE_CALL\n"
            "Caller: OID#4418 -> Callee: OID#8864\n"
            "Duration: 145s | Originating Sector: Sector-Central-East"
        ),
        metadata={
            "sector": "Sector-Central-East",
            "date": "2020-01-17",
            "caller_id": "OID#4418",
            "callee_id": "OID#8864",
            "call_type": "voice_call"
        }
    )
    assert doc_cdr.doc_id == "CDR_055ad8bc"


def test_corpus_level_duplicate_and_empty_rejection(corpus_data):
    """Verify that corpus validation rejects duplicates, empty corpus, and accepts the true corpus."""
    docs = [SanitizedRetrievalDocument(**d) for d in corpus_data["retrieval_docs"]]
    assert len(docs) == 31

    # Real corpus must pass cleanly
    validate_retrieval_corpus(docs)

    # Empty corpus must fail
    with pytest.raises(ValueError, match="Corpus validation error: Document list is empty"):
        validate_retrieval_corpus([])

    # Duplicate doc_id must fail
    duped_docs = list(docs) + [docs[0]]
    with pytest.raises(ValueError, match="Corpus validation error: Duplicate doc_id"):
        validate_retrieval_corpus(duped_docs)
