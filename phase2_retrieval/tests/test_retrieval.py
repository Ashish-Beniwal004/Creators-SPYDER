"""
Phase 2C Automated Test Suite: Evidence Retrieval Layer
Project: Evidence-Grounded Agentic Criminal Network Investigation
Suite: phase2_retrieval/tests/test_retrieval.py

Covers:
1. Successful corpus loading and index construction.
2. Retrieval of relevant incident reports and CDRs using representative queries.
3. Alias-based and canonical-identifier queries.
4. Ranking order and deterministic tie-breaking.
5. Valid and invalid top_k values.
6. Empty queries and queries with no matching terms.
7. Duplicate document IDs and malformed corpus records.
8. Rejection of unsupported evidence types and unexpected schema fields.
9. Retrieval output containing no provenance, target-pair, label, rationale, pilot-case, or source CIDs.
10. No access to the ground-truth vault or internal provenance by the retrieval service.
11. Stable output across repeated executions.
12. Regression tests confirming Phase 2B.2 corpus and frozen manifests remain unchanged.
"""

import os
import sys
import json
import hashlib
import tempfile
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VAULT_DIR = os.path.join(REPO_ROOT, "phase2_ground_truth_vault")
CORPUS_DIR = os.path.join(REPO_ROOT, "phase2_corpus")
RETRIEVAL_DIR = os.path.join(REPO_ROOT, "phase2_retrieval")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_retrieval.retriever import (
    EvidenceRetriever,
    search_evidence,
    get_default_retriever,
    load_and_validate_corpus,
    DEFAULT_CORPUS_PATH,
    DEFAULT_TOP_K,
    MAX_TOP_K
)
from phase2_retrieval.schemas import RetrievalResultItem, RetrievalResponse


@pytest.fixture(scope="module")
def retriever():
    """Module-level EvidenceRetriever fixture initialized on frozen corpus."""
    return EvidenceRetriever(DEFAULT_CORPUS_PATH)


# ==============================================================================
# 1. CORPUS LOADING AND INDEX CONSTRUCTION
# ==============================================================================

def test_corpus_loading_and_index_construction(retriever):
    """Verify that the corpus is validated and indexed correctly."""
    assert retriever.document_count == 31
    assert retriever.is_indexed is True
    assert len(retriever.vocabulary) > 300

    docs = load_and_validate_corpus(DEFAULT_CORPUS_PATH)
    assert len(docs) == 31
    doc_types = {d.doc_type for d in docs}
    assert doc_types == {"incident_report", "call_detail_record"}


# ==============================================================================
# 2. REPRESENTATIVE INCIDENT REPORTS AND CDR RETRIEVAL
# ==============================================================================

def test_retrieval_representative_incident_reports(retriever):
    """Verify retrieval of relevant incident reports using representative operational queries."""
    query = "commercial premises audible burglar alarm dark duffel bag"
    results = retriever.search(query=query, top_k=3)

    assert len(results) > 0
    top_doc = results[0]
    assert top_doc.doc_type == "incident_report"
    assert top_doc.doc_id == "DOC_IR_68ca5aaf"
    assert "alarm" in top_doc.text_content.lower()
    assert 0.0 < top_doc.score <= 1.0


def test_retrieval_representative_call_detail_records(retriever):
    """Verify retrieval of relevant CDRs using telecommunication queries."""
    query = "COMMUNICATION INTERCEPT LOG VOICE_CALL"
    results = retriever.search(query=query, top_k=5)

    assert len(results) > 0
    cdr_hits = [r for r in results if r.doc_type == "call_detail_record"]
    assert len(cdr_hits) > 0
    for r in cdr_hits:
        assert "intercept" in r.text_content.lower()
        assert 0.0 < r.score <= 1.0


# ==============================================================================
# 3. ALIAS-BASED AND CANONICAL-IDENTIFIER QUERIES
# ==============================================================================

def test_retrieval_canonical_entity_identifiers(retriever):
    """Verify retrieval using exact canonical entity identifiers (OID#xxxx)."""
    # Case 01 co-offender
    results_4418 = retriever.search("OID#4418", top_k=5)
    doc_ids_4418 = {r.doc_id for r in results_4418}
    assert "DOC_IR_68ca5aaf" in doc_ids_4418
    assert "CDR_055ad8bc" in doc_ids_4418
    assert "CDR_5b17362b" in doc_ids_4418

    # Alias target entity
    results_8595 = retriever.search("OID#8595", top_k=3)
    assert len(results_8595) > 0
    assert results_8595[0].doc_id == "DOC_IR_c1c7b4bb"
    assert "OID#8595" in results_8595[0].text_content


def test_retrieval_street_aliases(retriever):
    """Verify multi-document retrieval using street aliases / monikers."""
    # 'The Wire'
    results_wire = retriever.search("The Wire", top_k=3)
    wire_ids = [r.doc_id for r in results_wire]
    assert "DOC_IR_71acf05c" in wire_ids  # Primary alias burglary
    assert "CDR_063962b6" in wire_ids     # Intercepted call
    assert "DOC_IR_c1c7b4bb" in wire_ids  # Field interview resolving alias

    # 'The Spark'
    results_spark = retriever.search("The Spark", top_k=3)
    spark_ids = [r.doc_id for r in results_spark]
    assert "DOC_IR_f86bab88" in spark_ids
    assert "CDR_5167d606" in spark_ids

    # 'The Locksmith'
    results_locksmith = retriever.search("The Locksmith", top_k=3)
    locksmith_ids = [r.doc_id for r in results_locksmith]
    assert "DOC_IR_bf7db53a" in locksmith_ids  # Primary jewelry burglary with 'The Locksmith'
    assert "DOC_IR_80e4d5d3" in locksmith_ids  # Field stop resolving 'The Locksmith' to OID#2568


# ==============================================================================
# 4. RANKING ORDER AND DETERMINISTIC TIE-BREAKING
# ==============================================================================

def test_ranking_order_scores_descending(retriever):
    """Verify that results are strictly ranked in descending score order."""
    test_queries = [
        "residential burglary Sector-Central-East",
        "forced lock bulkhead basement storage",
        "copper wire pipe fittings warehouse",
        "traffic field interview vehicle inspection"
    ]
    for q in test_queries:
        results = retriever.search(q, top_k=10)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                f"Score ordering violation in query '{q}': "
                f"{results[i].score} < {results[i+1].score}"
            )


def test_deterministic_tie_breaking_order():
    """Verify that documents with identical scores break ties strictly by doc_id ascending."""
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        # Two documents with identical text content but distinct hash doc_ids
        doc_b = {
            "doc_id": "DOC_IR_bbbbbbbb",
            "doc_type": "incident_report",
            "timestamp": "2020-01-01 10:00:00",
            "text_content": "Identical burglary narrative with specific keyword testcase.",
            "metadata": {"sector": "Sector-Central"}
        }
        doc_a = {
            "doc_id": "DOC_IR_aaaaaaaa",
            "doc_type": "incident_report",
            "timestamp": "2020-01-01 10:00:00",
            "text_content": "Identical burglary narrative with specific keyword testcase.",
            "metadata": {"sector": "Sector-Central"}
        }
        f.write(json.dumps(doc_b) + "\n")
        f.write(json.dumps(doc_a) + "\n")
        temp_path = f.name

    try:
        temp_retriever = EvidenceRetriever(temp_path)
        hits = temp_retriever.search("specific keyword testcase", top_k=2)
        assert len(hits) == 2
        assert hits[0].score == hits[1].score
        # Tie-breaker rule: doc_id ascending ('DOC_IR_aaaaaaaa' before 'DOC_IR_bbbbbbbb')
        assert hits[0].doc_id == "DOC_IR_aaaaaaaa"
        assert hits[1].doc_id == "DOC_IR_bbbbbbbb"
    finally:
        os.remove(temp_path)


# ==============================================================================
# 5. VALID AND INVALID TOP_K VALUES
# ==============================================================================

def test_top_k_parameter_validation(retriever):
    """Verify validation and boundary constraints for top_k."""
    # Valid top_k values
    assert len(retriever.search("burglary", top_k=1)) == 1
    assert len(retriever.search("burglary", top_k=3)) == 3
    assert len(retriever.search("burglary", top_k=20)) <= 20

    # Invalid non-positive top_k
    with pytest.raises(ValueError, match="top_k must be positive"):
        retriever.search("burglary", top_k=0)

    with pytest.raises(ValueError, match="top_k must be positive"):
        retriever.search("burglary", top_k=-5)

    # Invalid top_k exceeding maximum allowed (50)
    with pytest.raises(ValueError, match="exceeds maximum allowed value"):
        retriever.search("burglary", top_k=51)

    # Invalid types
    with pytest.raises(TypeError, match="top_k must be an integer"):
        retriever.search("burglary", top_k="five")  # type: ignore

    with pytest.raises(TypeError, match="top_k must be an integer"):
        retriever.search("burglary", top_k=True)  # type: ignore


# ==============================================================================
# 6. EMPTY QUERIES AND ZERO MATCHING TERMS
# ==============================================================================

def test_empty_and_zero_matching_queries(retriever):
    """Verify safe behavior for empty, whitespace, and unmatched queries."""
    # Empty and whitespace queries
    assert retriever.search("") == []
    assert retriever.search("   ") == []
    assert retriever.search("\n\t  ") == []
    assert retriever.search(None) == []  # type: ignore

    # Zero matching terms
    assert retriever.search("unmatched_nonexistent_term_zyx999") == []
    assert retriever.search("xyz123456789nonexistent") == []

    # search_evidence function interface
    assert search_evidence("") == []
    assert search_evidence("unmatched_nonexistent_term_zyx999") == []


# ==============================================================================
# 7. DUPLICATE DOCUMENT IDS AND MALFORMED CORPUS RECORDS
# ==============================================================================

def test_rejection_of_duplicate_doc_ids():
    """Verify that corpora containing duplicate doc_ids are rejected."""
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        doc = {
            "doc_id": "DOC_IR_11111111",
            "doc_type": "incident_report",
            "timestamp": "2020-01-01 10:00:00",
            "text_content": "Valid text content of sufficient length for testing.",
            "metadata": {"sector": "Sector-Central"}
        }
        f.write(json.dumps(doc) + "\n")
        f.write(json.dumps(doc) + "\n")
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Duplicate doc_id"):
            load_and_validate_corpus(temp_path)
    finally:
        os.remove(temp_path)


def test_rejection_of_malformed_json_records():
    """Verify that syntax errors and non-dict records fail clearly."""
    # Malformed JSON syntax
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write('{"doc_id": "DOC_IR_11111111", broken json\n')
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Malformed JSON"):
            load_and_validate_corpus(temp_path)
    finally:
        os.remove(temp_path)

    # Non-object record (e.g. JSON list instead of object)
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write('["not_an_object"]\n')
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Expected JSON object"):
            load_and_validate_corpus(temp_path)
    finally:
        os.remove(temp_path)


# ==============================================================================
# 8. UNSUPPORTED EVIDENCE TYPES AND UNEXPECTED FIELDS
# ==============================================================================

def test_rejection_of_unsupported_evidence_types():
    """Verify that non-approved evidence types (e.g. pawn logs) are rejected."""
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        bad_doc = {
            "doc_id": "DOC_IR_22222222",
            "doc_type": "pawn_ticket",
            "timestamp": "2020-01-01 10:00:00",
            "text_content": "Pawn shop transaction ticket logging jewelry receipt.",
            "metadata": {"sector": "Sector-Central"}
        }
        f.write(json.dumps(bad_doc) + "\n")
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Disallowed evidence type|Malformed payload"):
            load_and_validate_corpus(temp_path)
    finally:
        os.remove(temp_path)


def test_rejection_of_unexpected_schema_fields():
    """Verify that unexpected extra payload attributes are rejected."""
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        bad_doc = {
            "doc_id": "DOC_IR_33333333",
            "doc_type": "incident_report",
            "timestamp": "2020-01-01 10:00:00",
            "text_content": "Valid text content of sufficient length for testing.",
            "metadata": {"sector": "Sector-Central"},
            "disallowed_extra_field": "leak_payload"
        }
        f.write(json.dumps(bad_doc) + "\n")
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Schema violation|extra"):
            load_and_validate_corpus(temp_path)
    finally:
        os.remove(temp_path)


# ==============================================================================
# 9. STRICT OUTPUT ISOLATION AND ZERO LEAKAGE
# ==============================================================================

def test_retrieval_output_strict_isolation_no_leakage(retriever):
    """
    Verify that retrieval outputs contain ONLY approved evidence fields:
    - Never return internal metadata dictionary.
    - Never return target_pair, label, rationale, condition, component_id, or case_id.
    - Never expose original source crime CIDs or PILOT_CASE identifiers.
    """
    sample_queries = [
        "OID#4418", "The Wire", "commercial burglary", "Sector-Central-East",
        "forced lock", "copper tools", "voice call intercept"
    ]

    for q in sample_queries:
        results = retriever.search(q, top_k=5)
        for r in results:
            # Type and schema check
            assert isinstance(r, RetrievalResultItem)
            dumped = r.model_dump()

            # Exactly approved presentation keys
            assert set(dumped.keys()) == {"doc_id", "doc_type", "text_content", "score"}

            # Confirm internal metadata is NOT returned
            assert not hasattr(r, "metadata")
            assert "metadata" not in dumped

            # Check for leaked tokens in text or doc_id
            assert "CID#" not in r.text_content
            assert "PILOT_CASE" not in r.text_content
            assert "GROUND TRUTH" not in r.text_content
            assert not any(cond in r.text_content for cond in [
                "clean_evidence", "alias_ambiguity", "missing_evidence", "distractors"
            ])


# ==============================================================================
# 10. FIREWALL: NO ACCESS TO GROUND TRUTH VAULT OR PROVENANCE
# ==============================================================================

def test_retrieval_service_no_access_to_vault_or_provenance():
    """
    Verify that the retrieval module source code does NOT reference or load
    ground-truth vault data files or internal provenance files.
    """
    retriever_file = os.path.join(RETRIEVAL_DIR, "retriever.py")
    with open(retriever_file, "r", encoding="utf-8") as f:
        code = f.read()

    forbidden_sources = [
        "internal_provenance.jsonl",
        "ground_truth.json",
        "pilot_manifest.json",
        "split_manifest.json"
    ]
    for bad_source in forbidden_sources:
        assert bad_source not in code, (
            f"Firewall violation: '{bad_source}' referenced in retrieval service source!"
        )


# ==============================================================================
# 11. DETERMINISTIC REPRODUCIBILITY ACROSS REPEATED EXECUTIONS
# ==============================================================================

def test_stable_output_across_repeated_executions(retriever):
    """Verify that repeated executions produce 100% identical search results."""
    query = "residential burglary Sector-Central-East OID#4418"
    run_1 = [r.model_dump() for r in retriever.search(query, top_k=5)]
    run_2 = [r.model_dump() for r in retriever.search(query, top_k=5)]
    run_3 = [r.model_dump() for r in search_evidence(query, top_k=5)]

    assert run_1 == run_2
    assert run_1 == run_3


# ==============================================================================
# 12. REGRESSION: FROZEN CORPUS AND VAULT MANIFESTS INTEGRITY
# ==============================================================================

def test_phase2b2_corpus_and_manifests_regression():
    """
    CRITICAL REGRESSION CHECK:
    Verify that Phase 2C has not altered the frozen Phase 2B.2 corpus or vault files.
    """
    def hash_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    expected_hashes = {
        os.path.join(CORPUS_DIR, "retrieval_documents.jsonl"): "a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded",
        os.path.join(CORPUS_DIR, "internal_provenance.jsonl"): "ae29dcd873a3f87f01dff4e5dceb3edd041caf64e21f7065d74114ad2f9287bc",
        os.path.join(VAULT_DIR, "ground_truth.json"): "87f84a65111bd38a021860247b53362fbf3f92f284a8a2ccd30eeb4089a42963",
        os.path.join(VAULT_DIR, "pilot_manifest.json"): "ee376e36dde8378109d60eaa7a37102262d717d56a76fe65337dda2098ee9b50",
        os.path.join(VAULT_DIR, "split_manifest.json"): "04dc346d4628d1ad59d6b34d3580f6ddb40548e35921f48cc24a0d6a389d0ffd",
    }

    for path, expected_hash in expected_hashes.items():
        assert os.path.exists(path), f"Missing file: {path}"
        actual_hash = hash_file(path)
        assert actual_hash == expected_hash, (
            f"Integrity violation in {os.path.basename(path)}!\n"
            f"Expected: {expected_hash}\nActual:   {actual_hash}"
        )
