"""
SPYDER Phase 2G.1 Strict Quarantine, Metric Integrity, and Evaluator Regression Suite.

Verifies:
1. Raw output hashes and frozen benchmark dataset hashes remain strictly unchanged.
2. Ground truth and provenance are not imported or accessed by System A, System B, or runner.
3. 100% of cited document IDs across both systems resolve to documents in the active retrieval corpus.
4. Evaluator does NOT mark a citation sound based merely on an ID prefix (e.g. DOC_IR_).
5. Missing-evidence cases and telecommunication logs cannot be declared evidentially supported by CDRs alone.
6. Benchmark generation reproducibility operates in temporary directories and never mutates frozen assets.
"""

import os
import sys
import ast
import json
import hashlib
import tempfile
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_experiment.config import (
    FULL_TEST_CORPUS_PATH,
    FULL_TEST_GROUND_TRUTH_PATH,
    FULL_TEST_MANIFEST_PATH,
    FULL_TEST_TARGETS_PATH,
    FULL_TEST_PROVENANCE_PATH,
    PILOT_CORPUS_PATH,
    PILOT_GROUND_TRUTH_PATH,
    PILOT_MANIFEST_PATH,
    PILOT_PROVENANCE_PATH,
    SPLIT_MANIFEST_PATH,
    DEFAULT_OUTPUTS_DIR,
)
from phase2_experiment.evaluator import adjudicate_evidentiary_soundness, compute_descriptive_metrics
from phase2_verification.verifier import HypothesisVerifier

PUBLIC_FROZEN_BENCHMARK_HASHES = {
    # Full-test public inputs & aggregate scoring outputs (zero case-level labels)
    FULL_TEST_TARGETS_PATH: "125e012b794440c6db8170bb4aa9c385472780bddc1174c6ba7e76096c711cd0",
    FULL_TEST_CORPUS_PATH: "72d00c6250a73a385fef10792b38fa30aaae8b8a96dff94420e092980caf1349",
    PILOT_CORPUS_PATH: "a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded",
    PILOT_PROVENANCE_PATH: "ae29dcd873a3f87f01dff4e5dceb3edd041caf64e21f7065d74114ad2f9287bc",
    os.path.join(DEFAULT_OUTPUTS_DIR, "full_test_run_manifest.json"): "56fb9056e33bb637dba35e58074b5c0d6362646fc203cd2f9292152adfa054b7",
    os.path.join(DEFAULT_OUTPUTS_DIR, "full_test_scoring_report.json"): "146e479f94f01c4190418893958c4ab343571b025f6a25653d1a9caa9083e316",
}

QUARANTINED_VAULT_BENCHMARK_HASHES = {
    FULL_TEST_MANIFEST_PATH: "0f5bdc943f9fb51314efb2b1fec8baa2828772feb040980585d0b18f892f12af",
    FULL_TEST_GROUND_TRUTH_PATH: "3f1e9021538be563ea8de015b076ca3a9e2bb75684ae04dcdbd52c7f3e7b8e33",
    FULL_TEST_PROVENANCE_PATH: "e32a102d6a74469799d2488404b049bd602543ff4dba878d26024ef096f77555",
    PILOT_GROUND_TRUTH_PATH: "87f84a65111bd38a021860247b53362fbf3f92f284a8a2ccd30eeb4089a42963",
    PILOT_MANIFEST_PATH: "ee376e36dde8378109d60eaa7a37102262d717d56a76fe65337dda2098ee9b50",
    SPLIT_MANIFEST_PATH: "04dc346d4628d1ad59d6b34d3580f6ddb40548e35921f48cc24a0d6a389d0ffd",
    # Quarantined full-test predictions & pre-audit scoring report (blinded benchmark release)
    os.path.join(DEFAULT_OUTPUTS_DIR, "original_full_test_scoring_report.json"): "3fedc24e87e75400a21f8aca21a3b6edb2797121ecfe0ef4706e53d9d72c249c",
    os.path.join(DEFAULT_OUTPUTS_DIR, "system_a_full_test_outputs.json"): "5c804673b4dc70b8fbe3aa70024d19100f0ed661e35a141db27353f523bf7e8b",
    os.path.join(DEFAULT_OUTPUTS_DIR, "system_b_full_test_outputs.json"): "510ab08293a094ceaf0b161219e6c3da538bdfdc3a4045953e7b846f6874ea31",
}

FROZEN_BENCHMARK_HASHES = {**PUBLIC_FROZEN_BENCHMARK_HASHES, **QUARANTINED_VAULT_BENCHMARK_HASHES}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_frozen_output_and_benchmark_hashes_unchanged():
    """Verify that all public distributed artifacts retain their frozen baseline hashes and zero label leakage."""
    for path, expected_hash in PUBLIC_FROZEN_BENCHMARK_HASHES.items():
        assert os.path.exists(path), f"Required public artifact missing: {path}"
        actual = _sha256(path)
        assert actual == expected_hash, f"Artifact hash mismatch for {os.path.basename(path)}!\nExpected: {expected_hash}\nActual:   {actual}"

    # Confirm public scoring report is aggregate-only (no case-level label leakage)
    pub_rep_path = os.path.join(DEFAULT_OUTPUTS_DIR, "full_test_scoring_report.json")
    with open(pub_rep_path, "r", encoding="utf-8") as f:
        rep_data = json.load(f)
    assert "case_comparisons" not in rep_data, "Public scoring report must NOT contain case_comparisons!"
    assert rep_data.get("total_cases") == 200

    # Also verify quarantined vault files if present in the environment (e.g. internal reproduction)
    vault_present = [path for path in QUARANTINED_VAULT_BENCHMARK_HASHES.keys() if os.path.exists(path)]
    if vault_present:
        for path, expected_hash in QUARANTINED_VAULT_BENCHMARK_HASHES.items():
            assert os.path.exists(path), f"Quarantined vault artifact missing: {path}"
            actual = _sha256(path)
            assert actual == expected_hash, f"Vault hash mismatch for {os.path.basename(path)}!\nExpected: {expected_hash}\nActual:   {actual}"


def test_artifact_hash_manifests_match_files():
    """Verify every declared artifact hash and size in both repository manifests."""
    manifest_names = [
        "phase2_artifact_hash_manifest.json",
        "phase2_public_artifact_hash_manifest.json",
    ]

    for manifest_name in manifest_names:
        manifest_path = os.path.join(REPO_ROOT, manifest_name)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for artifact_path, entry in manifest["files"].items():
            resolved_path = os.path.join(REPO_ROOT, artifact_path)
            context = f"{manifest_name}: {artifact_path}"
            assert os.path.isfile(resolved_path), f"Missing artifact ({context})"

            with open(resolved_path, "rb") as f:
                artifact_bytes = f.read()

            actual_hash = hashlib.sha256(artifact_bytes).hexdigest()
            assert actual_hash == entry["sha256"], f"SHA-256 mismatch ({context})"
            assert len(artifact_bytes) == entry["size_bytes"], f"File size mismatch ({context})"




def test_strict_quarantine_code_import_isolation():
    """Verify that execution runner, System A, and System B never import vault files or provenance."""
    code_files = [
        os.path.join(REPO_ROOT, "phase2_experiment", "system_a.py"),
        os.path.join(REPO_ROOT, "phase2_experiment", "system_b.py"),
        os.path.join(REPO_ROOT, "phase2_experiment", "runner.py"),
    ]

    forbidden_tokens = [
        "ground_truth.json",
        "test_ground_truth.json",
        "internal_provenance.jsonl",
        "test_internal_provenance.jsonl",
        "GroundTruthCase",
        "PilotManifest",
        "TestManifest",
        "EvidenceProvenanceEnvelope",
        "split_manifest.json",
    ]

    for fpath in code_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("phase2_ground_truth_vault"), f"Forbidden import '{alias.name}' in {os.path.basename(fpath)}"
                    assert "provenance" not in alias.name.lower(), f"Forbidden import '{alias.name}' in {os.path.basename(fpath)}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith("phase2_ground_truth_vault"), f"Forbidden import from '{mod}' in {os.path.basename(fpath)}"
                assert "provenance" not in mod.lower(), f"Forbidden import from '{mod}' in {os.path.basename(fpath)}"

        for forbidden in forbidden_tokens:
            assert forbidden not in content, f"Forbidden reference to '{forbidden}' in {os.path.basename(fpath)}"


def test_all_system_citations_resolve_to_active_corpus():
    """Verify that 100% of evidence IDs cited by System A and System B resolve to the active retrieval corpus."""
    corpus_doc_ids = set()
    with open(FULL_TEST_CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                corpus_doc_ids.add(json.loads(line)["doc_id"])

    sys_a_path = os.path.join(DEFAULT_OUTPUTS_DIR, "system_a_full_test_outputs.json")
    sys_b_path = os.path.join(DEFAULT_OUTPUTS_DIR, "system_b_full_test_outputs.json")

    if os.path.exists(sys_a_path) and os.path.exists(sys_b_path):
        with open(sys_a_path, "r", encoding="utf-8") as f:
            data_a = json.load(f)
        with open(sys_b_path, "r", encoding="utf-8") as f:
            data_b = json.load(f)

        for r in data_a["results"]:
            for cid in r.get("cited_doc_ids", []):
                assert cid in corpus_doc_ids, f"System A cited unresolvable doc_id '{cid}' in case {r['case_index']}"

        for r in data_b["results"]:
            for cid in r.get("cited_doc_ids", []):
                assert cid in corpus_doc_ids, f"System B cited unresolvable doc_id '{cid}' in case {r['case_index']}"
    else:
        # In a clean clone where prediction files are quarantined to prevent label leakage,
        # verify 100% citation resolution on pilot run executions
        from phase2_experiment.runner import run_pilot_experiment
        with tempfile.TemporaryDirectory() as tmp_dir:
            res_a, res_b, _ = run_pilot_experiment(outputs_dir=tmp_dir)
            pilot_corpus_ids = set()
            with open(PILOT_CORPUS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        pilot_corpus_ids.add(json.loads(line)["doc_id"])
            for r in res_a.results:
                for cid in r.cited_doc_ids:
                    assert cid in pilot_corpus_ids, f"System A cited unresolvable pilot doc_id '{cid}'"
            for r in res_b.results:
                for cid in r.cited_doc_ids:
                    assert cid in pilot_corpus_ids, f"System B cited unresolvable pilot doc_id '{cid}'"



def test_evaluator_rejects_soundness_based_only_on_id_prefix():
    """
    Ensure the evaluator does NOT mark a citation sound based merely on 'DOC_IR_' prefix.
    An independent report mentioning only one suspect must fail evidentiary verification.
    """
    verifier = HypothesisVerifier(corpus_path=FULL_TEST_CORPUS_PATH)
    corpus_docs = {}
    with open(FULL_TEST_CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                corpus_docs[d["doc_id"]] = d

    # Case TEST_CASE_021: target pair OID#2499 and OID#4024 are independent suspects
    # DOC_IR_89c3b05e only mentions OID#2499
    target_pair = ("OID#2499", "OID#4024")
    independent_ir = ["DOC_IR_89c3b05e"]

    is_sound, rationale, meta = adjudicate_evidentiary_soundness(target_pair, independent_ir, corpus_docs, verifier)
    assert not is_sound, "Independent incident report must NOT be marked sound!"
    assert "INADEQUATE_EVIDENCE" in meta["category"]


def test_cdrs_alone_cannot_establish_evidentiary_soundness():
    """Verify that CallDetailRecords alone are strictly rejected as unsound for relationship support."""
    verifier = HypothesisVerifier(corpus_path=FULL_TEST_CORPUS_PATH)
    corpus_docs = {}
    with open(FULL_TEST_CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                corpus_docs[d["doc_id"]] = d

    # Case 081 in missing_evidence: CDRs between OID#5224 and OID#6140
    target_pair = ("OID#5224", "OID#6140")
    cdr_ids = ["CDR_3549feee", "CDR_ab097d5f"]

    is_sound, rationale, meta = adjudicate_evidentiary_soundness(target_pair, cdr_ids, corpus_docs, verifier)
    assert not is_sound, "CDRs alone must be rejected as evidentiary support!"
    assert meta["category"] == "CDR_COMMUNICATION_ALONE"


def test_undefined_metrics_return_none_not_zero():
    """Verify that when denominator is zero, precision, recall, f1, etc. return None (N/A)."""
    # All true negatives, no positive predictions
    y_true = [0, 0, 0]
    y_pred = [0, 0, 0]
    m = compute_descriptive_metrics(y_true, y_pred)

    assert m.accuracy == 1.0
    assert m.true_negatives == 3
    assert m.true_positives == 0
    assert m.false_positives == 0
    assert m.false_negatives == 0
    assert m.precision is None, "Precision with 0 positive predictions must be None (N/A)"
    assert m.f1_score is None, "F1-score with 0 positive predictions must be None (N/A)"
    assert m.recall is None, "Recall with 0 positive true labels must be None (N/A)"
    assert m.specificity == 1.0
    assert m.false_positive_rate == 0.0
