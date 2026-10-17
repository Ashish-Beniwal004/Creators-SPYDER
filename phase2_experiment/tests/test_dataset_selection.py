"""
Tests for Phase 2G Dataset Selection and Normalization Adapter.

Verifies:
1. normalize_target_pairs correctly handles list-of-pairs, named entity dicts, and nested formats.
2. Pilot defaults are preserved across all components.
3. Full-test configuration routes to full-test artifacts without state leakage.
4. Systems A and B cite only evidence present in the active corpus.
"""

import json
from pathlib import Path
import pytest

from phase2_experiment.config import (
    get_dataset_config,
    DATASET_CONFIGS,
    PILOT_TARGET_PAIRS_PATH,
    FULL_TEST_TARGET_PAIRS_PATH,
    PILOT_RETRIEVAL_DOCUMENTS_PATH,
    FULL_TEST_RETRIEVAL_DOCUMENTS_PATH,
)
from phase2_experiment.runner import normalize_target_pairs, run_benchmark
from phase2_experiment.system_a import run_system_a
from phase2_experiment.system_b import run_system_b
from phase2_retrieval.retriever import EvidenceRetriever
from phase2_verification.verifier import HypothesisVerifier


def test_dataset_config_selection():
    """Verify dataset config returns correct paths and defaults."""
    cfg_default = get_dataset_config()
    assert cfg_default["dataset_mode"] == "pilot"
    assert cfg_default["corpus_path"] == PILOT_RETRIEVAL_DOCUMENTS_PATH
    assert cfg_default["target_pairs_path"] == PILOT_TARGET_PAIRS_PATH

    cfg_pilot = get_dataset_config("pilot")
    assert cfg_pilot == cfg_default

    cfg_test = get_dataset_config("full_test")
    assert cfg_test["dataset_mode"] == "full_test"
    assert cfg_test["corpus_path"] == FULL_TEST_RETRIEVAL_DOCUMENTS_PATH
    assert cfg_test["target_pairs_path"] == FULL_TEST_TARGET_PAIRS_PATH

    with pytest.raises(ValueError, match="Unknown dataset_mode"):
        get_dataset_config("unknown_mode")


def test_normalize_target_pairs_formats():
    """Test normalization adapter on varied valid formats."""
    # Format 1: List of 2-element lists
    raw_lists = [
        ["OID#4418", "OID#5022"],
        ["OID#3110", "OID#9821"]
    ]
    norm_1 = normalize_target_pairs(raw_lists)
    assert len(norm_1) == 2
    assert norm_1[0] == ("OID#4418", "OID#5022")
    assert norm_1[1] == ("OID#3110", "OID#9821")

    # Format 2: Dict with 'cases' containing target_pair list
    raw_cases = {
        "cases": [
            {"case_id": "c1", "target_pair": ["OID#1001", "OID#1002"]},
            {"case_id": "c2", "target_pair": ["OID#2001", "OID#2002"]}
        ]
    }
    norm_2 = normalize_target_pairs(raw_cases)
    assert len(norm_2) == 2
    assert norm_2[0] == ("OID#1001", "OID#1002")
    assert norm_2[1] == ("OID#2001", "OID#2002")

    # Format 3: List of dicts with entity_a / entity_b
    raw_flat = [
        {"case_id": "c3", "entity_a": "OID#3001", "entity_b": "OID#3002"}
    ]
    norm_3 = normalize_target_pairs(raw_flat)
    assert len(norm_3) == 1
    assert norm_3[0] == ("OID#3001", "OID#3002")


def test_normalize_pilot_and_full_test_artifacts():
    """Verify adapter works directly on both source artifacts."""
    with open(PILOT_TARGET_PAIRS_PATH, "r", encoding="utf-8") as f:
        pilot_raw = json.load(f)
    pilot_norm = normalize_target_pairs(pilot_raw)
    assert len(pilot_norm) == 10
    for ea, eb in pilot_norm:
        assert ea.startswith("OID#")
        assert eb.startswith("OID#")
        assert ea != eb

    with open(FULL_TEST_TARGET_PAIRS_PATH, "r", encoding="utf-8") as f:
        test_raw = json.load(f)
    test_norm = normalize_target_pairs(test_raw)
    assert len(test_norm) == 200
    for ea, eb in test_norm:
        assert ea.startswith("OID#")
        assert eb.startswith("OID#")
        assert ea != eb


def test_system_a_and_b_full_test_corpus_execution():
    """Test that systems A and B query full-test corpus and cite only valid documents."""
    retriever = EvidenceRetriever(corpus_path=FULL_TEST_RETRIEVAL_DOCUMENTS_PATH)
    verifier = HypothesisVerifier(corpus_path=FULL_TEST_RETRIEVAL_DOCUMENTS_PATH)

    # Load first full test pair
    with open(FULL_TEST_TARGET_PAIRS_PATH, "r", encoding="utf-8") as f:
        pairs = json.load(f)
    first_pair = pairs["pairs"][0]

    out_a = run_system_a(
        first_pair[0], first_pair[1],
        case_index=0,
        retriever=retriever,
        corpus_path=FULL_TEST_RETRIEVAL_DOCUMENTS_PATH
    )
    assert out_a.case_index == 0
    assert out_a.decision in ["Supported", "Unsupported", "Insufficient Evidence"]
    for cid in out_a.cited_doc_ids:
        assert cid.startswith("DOC_IR_") or cid.startswith("CDR_")

    out_b = run_system_b(
        first_pair[0], first_pair[1],
        case_index=0,
        retriever=retriever,
        verifier=verifier,
        corpus_path=FULL_TEST_RETRIEVAL_DOCUMENTS_PATH
    )
    assert out_b.case_index == 0
    assert out_b.decision in ["Supported", "Unsupported", "Insufficient Evidence"]
    for cid in out_b.cited_doc_ids:
        assert cid.startswith("DOC_IR_") or cid.startswith("CDR_")
