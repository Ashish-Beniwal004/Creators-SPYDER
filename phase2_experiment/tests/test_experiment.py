"""
Phase 2E Experimental Integration, Quarantine Isolation, and Reproducibility Tests
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_experiment/tests/test_experiment.py

Verifies:
1. Integration smoke tests for System A and System B on target pairs.
2. Output schema strictness (forbids unexpected fields, ensures valid status literals).
3. Conservative handling of empty retrieval and non-existent entities.
4. Semantic grounding: System B never infers shared burglary from CDRs alone or unlinked aliases.
5. Deterministic reproducibility across repeated executions.
6. Execution runner integrity: 10 pilot cases, identical inputs, valid corpus doc_ids, citations grounded.
7. Strict quarantine isolation: execution runner and systems have zero access to ground truth vault/provenance.
8. Decoupled scoring process: evaluation runs strictly post-execution.
9. Frozen 5 artifact SHA-256 hashes remain unchanged.
"""

import os
import sys
import json
import ast
import hashlib
import tempfile
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_experiment.config import (
    DEFAULT_TOP_K,
    FROZEN_HASHES,
    PUBLIC_CORPUS_PATH,
)
from phase2_experiment.schemas import (
    SystemCaseOutput,
    ArmRunResult,
    PilotRunManifest,
    PilotScoringReport,
)
from phase2_experiment.system_a import run_system_a
from phase2_experiment.system_b import run_system_b
from phase2_experiment.runner import run_pilot_experiment, load_corpus_doc_ids, compute_file_sha256
from phase2_experiment.evaluator import evaluate_pilot_runs, compute_descriptive_metrics


# ==============================================================================
# 1. SMOKE AND SCHEMA COMPLIANCE TESTS
# ==============================================================================

def test_system_a_smoke_and_schema():
    """System A must produce a valid SystemCaseOutput without verification data."""
    out = run_system_a("OID#4418", "OID#8864", case_index=0, top_k=DEFAULT_TOP_K)
    assert isinstance(out, SystemCaseOutput)
    assert out.arm == "system_a_rag_only"
    assert out.entity_a == "OID#4418"
    assert out.entity_b == "OID#8864"
    assert out.target_pair == ("OID#4418", "OID#8864")
    assert out.decision in ("Supported", "Unsupported", "Insufficient Evidence")
    assert isinstance(out.is_supported, bool)
    assert out.is_supported == (out.decision == "Supported")
    assert out.verification_data is None
    assert len(out.retrieved_doc_ids) > 0
    assert len(out.retrieval_scores) == len(out.retrieved_doc_ids)


def test_system_b_smoke_and_schema():
    """System B must produce a valid SystemCaseOutput with grounded verification data."""
    out = run_system_b("OID#4418", "OID#8864", case_index=0, top_k=DEFAULT_TOP_K)
    assert isinstance(out, SystemCaseOutput)
    assert out.arm == "system_b_rag_verification"
    assert out.entity_a == "OID#4418"
    assert out.entity_b == "OID#8864"
    assert out.target_pair == ("OID#4418", "OID#8864")
    assert out.decision == "Supported"
    assert out.is_supported is True
    assert out.verification_data is not None
    assert out.verification_data["status"] == "Supported"
    assert "findings" in out.verification_data
    # Cited documents must be a subset of retrieved documents
    for cited_id in out.cited_doc_ids:
        assert cited_id in out.retrieved_doc_ids


# ==============================================================================
# 2. EDGE CASE AND CONSERVATIVE SEMANTICS TESTS
# ==============================================================================

def test_empty_retrieval_returns_conservative_decision():
    """Queries for non-existent entities must return Insufficient Evidence conservatively."""
    # Using entities that do not exist in the corpus
    out_a = run_system_a("OID#999999", "OID#999998", case_index=0)
    out_b = run_system_b("OID#999999", "OID#999998", case_index=0)

    assert out_a.decision == "Insufficient Evidence"
    assert out_a.is_supported is False
    assert len(out_a.retrieved_doc_ids) == 0

    assert out_b.decision == "Insufficient Evidence"
    assert out_b.is_supported is False
    assert len(out_b.retrieved_doc_ids) == 0
    assert len(out_b.cited_doc_ids) == 0


def test_cdr_communication_alone_not_supported_in_system_b():
    """System B must NOT infer burglary co-offending from CDR communications alone (Case 05)."""
    out_b = run_system_b("OID#4866", "OID#6315", case_index=4)
    # Even though wiretap CDRs exist between them, primary arrest narrative is missing
    assert out_b.decision == "Insufficient Evidence"
    assert out_b.is_supported is False
    assert "telecommunication" in out_b.rationale.lower() or "insufficient" in out_b.rationale.lower()


def test_alias_unresolved_distinction_in_system_b():
    """System B must reject unlinked alias attributions (Case 04 and Case 10)."""
    out_b_04 = run_system_b("OID#8595", "OID#8827", case_index=3)
    assert out_b_04.decision == "Insufficient Evidence"
    assert out_b_04.is_supported is False

    out_b_10 = run_system_b("OID#4381", "OID#6449", case_index=9)
    assert out_b_10.decision == "Insufficient Evidence"
    assert out_b_10.is_supported is False


# ==============================================================================
# 3. DETERMINISM AND REPRODUCIBILITY TESTS
# ==============================================================================

def test_deterministic_reproducibility():
    """Repeated runs of both arms must yield identical outputs and rankings."""
    pair = ("OID#6819", "OID#8595")
    run1_a = run_system_a(pair[0], pair[1], case_index=2)
    run2_a = run_system_a(pair[0], pair[1], case_index=2)

    assert run1_a.decision == run2_a.decision
    assert run1_a.retrieved_doc_ids == run2_a.retrieved_doc_ids
    assert run1_a.retrieval_scores == run2_a.retrieval_scores
    assert run1_a.rationale == run2_a.rationale

    run1_b = run_system_b(pair[0], pair[1], case_index=2)
    run2_b = run_system_b(pair[0], pair[1], case_index=2)

    assert run1_b.decision == run2_b.decision
    assert run1_b.retrieved_doc_ids == run2_b.retrieved_doc_ids
    assert run1_b.cited_doc_ids == run2_b.cited_doc_ids
    assert run1_b.rationale == run2_b.rationale


# ==============================================================================
# 4. RUNNER INTEGRITY AND 10-CASE PILOT CONTROLS
# ==============================================================================

def test_runner_ten_case_pilot_execution():
    """Runner must execute exactly 10 cases with shared controls and frozen outputs."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res_a, res_b, manifest = run_pilot_experiment(
            run_id="TEST_RUN_PILOT",
            outputs_dir=tmp_dir,
            top_k=DEFAULT_TOP_K
        )

        assert manifest.total_cases == 10
        assert len(res_a.results) == 10
        assert len(res_b.results) == 10

        corpus_ids = load_corpus_doc_ids()

        for idx, (ca, cb) in enumerate(zip(res_a.results, res_b.results)):
            assert ca.case_index == idx
            assert cb.case_index == idx
            assert ca.target_pair == cb.target_pair
            assert ca.retrieval_query == cb.retrieval_query
            assert ca.retrieved_doc_ids == cb.retrieved_doc_ids

            # Check retrieved document IDs exist in corpus
            for d in ca.retrieved_doc_ids:
                assert d in corpus_ids

            # Check System B cited document IDs exist in retrieved IDs
            for d in cb.cited_doc_ids:
                assert d in cb.retrieved_doc_ids

        # Check output files exist in tmp_dir and hashes match
        file_a = os.path.join(tmp_dir, "system_a_pilot_outputs.json")
        file_b = os.path.join(tmp_dir, "system_b_pilot_outputs.json")
        man_file = os.path.join(tmp_dir, "pilot_run_manifest.json")

        assert os.path.exists(file_a)
        assert os.path.exists(file_b)
        assert os.path.exists(man_file)

        assert compute_file_sha256(file_a) == manifest.system_a_output_sha256
        assert compute_file_sha256(file_b) == manifest.system_b_output_sha256


# ==============================================================================
# 5. STRICT QUARANTINE ISOLATION TESTS
# ==============================================================================

def test_runner_quarantine_isolation_no_vault_or_provenance_access():
    """
    Verifies that system_a.py, system_b.py, and runner.py have ZERO access to
    ground_truth.json or internal_provenance.jsonl.
    """
    modules_to_audit = [
        os.path.join(REPO_ROOT, "phase2_experiment", "system_a.py"),
        os.path.join(REPO_ROOT, "phase2_experiment", "system_b.py"),
        os.path.join(REPO_ROOT, "phase2_experiment", "runner.py"),
    ]

    forbidden_tokens = [
        "ground_truth.json",
        "internal_provenance.jsonl",
        "GroundTruthCase",
        "PilotManifest",
        "EvidenceProvenanceEnvelope",
        "split_manifest.json",
    ]

    for mod_path in modules_to_audit:
        with open(mod_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Parse AST to check imports
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("phase2_ground_truth_vault"), (
                        f"Quarantine violation in {os.path.basename(mod_path)}: Imports {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert not node.module.startswith("phase2_ground_truth_vault"), (
                        f"Quarantine violation in {os.path.basename(mod_path)}: Imports from {node.module}"
                    )

        # Check for forbidden string literals
        for tok in forbidden_tokens:
            assert tok not in code, (
                f"Quarantine violation: Forbidden token '{tok}' found in {os.path.basename(mod_path)}"
            )


def test_system_outputs_contain_no_quarantined_tokens():
    """Outputs generated by System A and System B must contain zero hidden evaluation tokens."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res_a, res_b, _ = run_pilot_experiment(outputs_dir=tmp_dir)

        payload_a = res_a.model_dump_json()
        payload_b = res_b.model_dump_json()

        for forbidden in ["CID#", "ground_truth", "internal_provenance", "condition", "is_distractor"]:
            assert forbidden not in payload_a, f"Leakage in System A output: '{forbidden}'"
            assert forbidden not in payload_b, f"Leakage in System B output: '{forbidden}'"


# ==============================================================================
# 6. EVALUATION SEPARATION TESTS
# ==============================================================================

def test_evaluator_decoupled_scoring():
    """Evaluator must operate strictly on saved outputs and ground-truth manifest."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Run experiment
        run_pilot_experiment(outputs_dir=tmp_dir)

        file_a = os.path.join(tmp_dir, "system_a_pilot_outputs.json")
        file_b = os.path.join(tmp_dir, "system_b_pilot_outputs.json")
        rep_file = os.path.join(tmp_dir, "pilot_scoring_report.json")

        report = evaluate_pilot_runs(
            system_a_file=file_a,
            system_b_file=file_b,
            report_output_file=rep_file
        )

        assert isinstance(report, PilotScoringReport)
        assert report.total_cases == 10
        assert len(report.case_comparisons) == 10
        assert os.path.exists(rep_file)

        # Verify descriptive metrics fields
        assert report.system_a_metrics.total_cases == 10
        assert report.system_b_metrics.total_cases == 10
        assert 0.0 <= report.system_b_metrics.accuracy <= 1.0


def test_metric_calculation_correctness():
    """Unit test for compute_descriptive_metrics."""
    y_true = [1, 1, 0, 0]
    y_pred = [1, 0, 0, 1]
    m = compute_descriptive_metrics(y_true, y_pred)
    assert m.true_positives == 1
    assert m.false_negatives == 1
    assert m.true_negatives == 1
    assert m.false_positives == 1
    assert m.accuracy == 0.5
    assert m.precision == 0.5
    assert m.recall == 0.5
    assert m.specificity == 0.5
    assert m.false_positive_rate == 0.5
    assert m.f1_score == 0.5


# ==============================================================================
# 7. FROZEN ARTIFACT REGRESSION CHECKS
# ==============================================================================

def test_five_frozen_artifact_hashes_integrity():
    """Verifies that all 5 frozen artifacts remain byte-identical."""
    for name, (rel_path, expected_hash) in FROZEN_HASHES.items():
        abs_path = os.path.join(REPO_ROOT, rel_path)
        assert os.path.exists(abs_path), f"Frozen artifact not found: {abs_path}"
        actual_hash = compute_file_sha256(abs_path)
        assert actual_hash == expected_hash, (
            f"Frozen artifact '{name}' hash mismatch!\nExpected: {expected_hash}\nActual:   {actual_hash}"
        )
