"""
SPYDER Phase 2F.1 — Full Benchmark Dataset Readiness and Validation Suite
Validates:
1. Exact case count (200) and 50/50 class balance (100 pos, 100 neg).
2. Balanced distribution across all 5 evaluation conditions (40 cases each: 20 pos, 20 neg).
3. Pydantic schema validation for vault manifests, ground truth, retrieval docs, and provenance envelopes.
4. Strict unlabelled input manifest (test_target_pairs.json contains strictly unlabelled entity pairs matching runner interface).
5. Component-level split isolation (zero entity/component overlap with pilot, dev, or reserve).
6. Pair uniqueness, valid entity ID syntax, and reflexive symmetry rejection.
7. Genuine missing-evidence operationalization (primary incident reports withheld from retrieval, preserved in provenance).
8. Distractor and mixed-difficulty condition operationalization (120 total distractor incident reports).
9. Strict leakage prevention (zero CID#xxxx, condition names, ground-truth labels, or case IDs in retrieval docs or experiment inputs).
10. Only approved evidence types (PoliceIncidentReport -> incident_report, CallDetailRecord -> call_detail_record).
11. Deterministic byte-level reproducibility.
12. Preservation of all 5 frozen pilot artifacts (zero hash drift).
"""

import os
import sys
import json
import re
import ast
import hashlib
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VAULT_DIR = os.path.join(REPO_ROOT, "phase2_ground_truth_vault")
CORPUS_DIR = os.path.join(REPO_ROOT, "phase2_corpus")
EXPERIMENT_DIR = os.path.join(REPO_ROOT, "phase2_experiment")

if VAULT_DIR not in sys.path:
    sys.path.insert(0, VAULT_DIR)
if CORPUS_DIR not in sys.path:
    sys.path.insert(0, CORPUS_DIR)

from schemas import (
    TestManifest,
    SanitizedRetrievalDocument,
    EvidenceProvenanceEnvelope,
    validate_retrieval_corpus
)

# Prevent pytest from treating TestManifest as a pytest test class
TestManifest.__test__ = False

FROZEN_PILOT_HASHES = {
    "retrieval_documents.jsonl": "a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded",
    "internal_provenance.jsonl": "ae29dcd873a3f87f01dff4e5dceb3edd041caf64e21f7065d74114ad2f9287bc",
    "ground_truth.json": "87f84a65111bd38a021860247b53362fbf3f92f284a8a2ccd30eeb4089a42963",
    "pilot_manifest.json": "ee376e36dde8378109d60eaa7a37102262d717d56a76fe65337dda2098ee9b50",
    "split_manifest.json": "04dc346d4628d1ad59d6b34d3580f6ddb40548e35921f48cc24a0d6a389d0ffd",
}


def _sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _sha256_normalized(filepath: str) -> str:
    """Compute SHA-256 after normalizing CRLF line endings to LF."""
    with open(filepath, "rb") as f:
        content = f.read()
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


@pytest.fixture(scope="module")
def test_manifest_data():
    path = os.path.join(VAULT_DIR, "test_manifest.json")
    if not os.path.exists(path):
        pytest.skip("Quarantined test_manifest.json is not present (blind benchmark release). Rebuild via 'python phase2_ground_truth_vault/build_test_benchmark.py'.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def test_ground_truth_data():
    path = os.path.join(VAULT_DIR, "test_ground_truth.json")
    if not os.path.exists(path):
        pytest.skip("Quarantined test_ground_truth.json is not present (blind benchmark release). Rebuild via 'python phase2_ground_truth_vault/build_test_benchmark.py'.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def test_target_pairs_data():
    path = os.path.join(EXPERIMENT_DIR, "test_target_pairs.json")
    assert os.path.exists(path), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def split_manifest_data():
    path = os.path.join(VAULT_DIR, "split_manifest.json")
    assert os.path.exists(path), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def test_corpus_data():
    retrieval_path = os.path.join(CORPUS_DIR, "test_retrieval_documents.jsonl")
    prov_path = os.path.join(CORPUS_DIR, "test_internal_provenance.jsonl")

    assert os.path.exists(retrieval_path), f"Missing {retrieval_path}"
    if not os.path.exists(prov_path):
        pytest.skip("Quarantined test_internal_provenance.jsonl is not present (blind benchmark release). Rebuild via 'python phase2_corpus/generate_test_evidence.py'.")

    with open(retrieval_path, "r", encoding="utf-8") as f:
        retrieval_docs = [json.loads(line) for line in f if line.strip()]

    with open(prov_path, "r", encoding="utf-8") as f:
        provenances = [json.loads(line) for line in f if line.strip()]

    return {"retrieval_docs": retrieval_docs, "provenances": provenances}



# ==============================================================================
# 1. Pilot Artifact Preservation
# ==============================================================================

def test_frozen_pilot_artifacts_preservation():
    """Verify that none of the 5 frozen pilot artifacts have been modified."""
    paths = {
        "retrieval_documents.jsonl": os.path.join(CORPUS_DIR, "retrieval_documents.jsonl"),
        "internal_provenance.jsonl": os.path.join(CORPUS_DIR, "internal_provenance.jsonl"),
        "ground_truth.json": os.path.join(VAULT_DIR, "ground_truth.json"),
        "pilot_manifest.json": os.path.join(VAULT_DIR, "pilot_manifest.json"),
        "split_manifest.json": os.path.join(VAULT_DIR, "split_manifest.json"),
    }
    for filename, expected_hash in FROZEN_PILOT_HASHES.items():
        actual_hash = _sha256_file(paths[filename])
        assert actual_hash == expected_hash, (
            f"FROZEN PILOT DRIFT DETECTED in {filename}!\n"
            f"Expected: {expected_hash}\nActual:   {actual_hash}"
        )


# ==============================================================================
# 2. Case Count, Balance, and Condition Allocation
# ==============================================================================

def test_test_manifest_schema_and_counts(test_manifest_data):
    """Verify test_manifest.json passes TestManifest schema and has 200 cases with 50/50 balance."""
    manifest = TestManifest(**test_manifest_data)
    assert manifest.total_cases == 200
    assert len(manifest.cases) == 200

    pos_cases = [c for c in manifest.cases if c.label == 1]
    neg_cases = [c for c in manifest.cases if c.label == 0]
    assert len(pos_cases) == 100, f"Expected 100 positive cases, got {len(pos_cases)}"
    assert len(neg_cases) == 100, f"Expected 100 negative cases, got {len(neg_cases)}"

    # Check conditions: 40 cases per condition (20 pos, 20 neg)
    conditions = ["clean_evidence", "alias_ambiguity", "missing_evidence", "distractors", "mixed_difficulty"]
    for cond in conditions:
        cond_cases = [c for c in manifest.cases if c.condition == cond]
        assert len(cond_cases) == 40, f"Condition {cond} has {len(cond_cases)} cases; expected 40"
        cond_pos = [c for c in cond_cases if c.label == 1]
        cond_neg = [c for c in cond_cases if c.label == 0]
        assert len(cond_pos) == 20, f"Condition {cond} pos count: {len(cond_pos)}; expected 20"
        assert len(cond_neg) == 20, f"Condition {cond} neg count: {len(cond_neg)}; expected 20"


def test_test_ground_truth_reconciliation(test_manifest_data, test_ground_truth_data):
    """Verify test_ground_truth.json matches test_manifest.json exactly."""
    manifest_cases = test_manifest_data["cases"]
    gt_cases = test_ground_truth_data["cases"]
    assert len(gt_cases) == 200

    for m_case, gt_case in zip(manifest_cases, gt_cases):
        assert m_case["case_id"] == gt_case["case_id"]
        assert m_case["target_pair"] == gt_case["target_pair"]
        assert m_case["label"] == gt_case["label"]
        assert m_case["condition"] == gt_case["condition"]
        assert m_case["shared_crime_ids"] == gt_case["shared_crime_ids"]

        if gt_case["label"] == 1:
            assert len(gt_case["shared_crime_ids"]) > 0, f"Positive case {gt_case['case_id']} missing shared crime IDs!"
        else:
            assert len(gt_case["shared_crime_ids"]) == 0, f"Negative case {gt_case['case_id']} has shared crime IDs!"


def test_unlabelled_target_pairs_manifest(test_manifest_data, test_target_pairs_data):
    """Verify test_target_pairs.json contains strictly unlabelled entity pairs matching runner format."""
    assert test_target_pairs_data["total_pairs"] == 200
    pairs = test_target_pairs_data["pairs"]
    assert len(pairs) == 200

    for i, pair in enumerate(pairs):
        assert len(pair) == 2
        ea, eb = pair
        m_case = test_manifest_data["cases"][i]
        assert [ea, eb] == m_case["target_pair"]


# ==============================================================================
# 3. Target Pair Uniqueness, Formatting, and Non-Reflexivity
# ==============================================================================

def test_target_pair_uniqueness_and_validity(test_target_pairs_data):
    """Verify all 200 pairs are unique, non-reflexive, and adhere to OID format."""
    seen_pairs = set()
    entity_regex = re.compile(r"^OID#\d+$")

    for pair in test_target_pairs_data["pairs"]:
        ea, eb = pair
        assert ea != eb, f"Reflexive pair detected: {ea} == {eb}"
        assert entity_regex.match(ea), f"Invalid entity ID format: {ea}"
        assert entity_regex.match(eb), f"Invalid entity ID format: {eb}"

        canonical = tuple(sorted([ea, eb]))
        assert canonical not in seen_pairs, f"Duplicate pair detected: {canonical}"
        seen_pairs.add(canonical)

    assert len(seen_pairs) == 200


# ==============================================================================
# 4. Split Isolation and Component Partitioning
# ==============================================================================

def test_split_isolation_and_component_separation(split_manifest_data, test_manifest_data):
    """Verify test entities belong strictly to test partition and positive pairs use disjoint components."""
    partitions = split_manifest_data["partitions"]
    pilot_nodes = set(partitions["pilot"]["nodes"])
    dev_nodes = set(partitions["dev"]["nodes"])
    test_nodes = set(partitions["test"]["nodes"])
    reserve_nodes = set(partitions["reserve"]["nodes"])

    # Disjoint partition sets
    assert len(test_nodes & pilot_nodes) == 0
    assert len(test_nodes & dev_nodes) == 0
    assert len(test_nodes & reserve_nodes) == 0

    # Build node-to-component mapping for test partition
    test_comp_map = {}
    for comp_idx, comp in enumerate(partitions["test"]["components"]):
        for node in comp:
            test_comp_map[node] = comp_idx

    used_pos_components = set()

    for case in test_manifest_data["cases"]:
        ea, eb = case["target_pair"]
        assert ea in test_nodes, f"Entity {ea} not in test partition!"
        assert eb in test_nodes, f"Entity {eb} not in test partition!"
        assert ea not in pilot_nodes and eb not in pilot_nodes
        assert ea not in dev_nodes and eb not in dev_nodes

        comp_a = test_comp_map[ea]
        comp_b = test_comp_map[eb]

        if case["label"] == 1:
            assert comp_a == comp_b, (
                f"Positive case {case['case_id']} entities {ea}, {eb} belong to different components!"
            )
            assert comp_a not in used_pos_components, (
                f"Component {comp_a} reused across multiple positive cases!"
            )
            used_pos_components.add(comp_a)
        else:
            assert comp_a != comp_b, (
                f"Negative case {case['case_id']} entities {ea}, {eb} belong to the SAME component {comp_a}!"
            )

    assert len(used_pos_components) == 100, "Expected exactly 100 distinct positive components."


# ==============================================================================
# 5. Schema Validation of Test Corpus and Provenance
# ==============================================================================

def test_test_retrieval_documents_schema_and_types(test_corpus_data):
    """Verify all 680 test retrieval documents validate against SanitizedRetrievalDocument."""
    docs = [SanitizedRetrievalDocument(**doc) for doc in test_corpus_data["retrieval_docs"]]
    assert len(docs) == 680

    # Enforce no duplicate doc_id
    validate_retrieval_corpus(docs)

    # Approved types only: incident_report (PoliceIncidentReport) and call_detail_record (CallDetailRecord)
    for doc in docs:
        assert doc.doc_type in ("incident_report", "call_detail_record"), (
            f"Unapproved doc_type '{doc.doc_type}' in {doc.doc_id}"
        )


def test_test_provenance_schema_and_reconciliation(test_corpus_data):
    """Verify all 700 provenance envelopes validate and reconcile 1:1 with retrieval corpus (minus 20 withheld)."""
    envelopes = [EvidenceProvenanceEnvelope(**env) for env in test_corpus_data["provenances"]]
    assert len(envelopes) == 700

    retrieval_doc_ids = {doc["doc_id"] for doc in test_corpus_data["retrieval_docs"]}
    withheld_envelopes = [e for e in envelopes if e.generation_rule == "RULE_MISSING_PRIMARY_INCIDENT_REPORT"]
    public_envelopes = [e for e in envelopes if e.generation_rule != "RULE_MISSING_PRIMARY_INCIDENT_REPORT"]

    assert len(withheld_envelopes) == 20, f"Expected 20 withheld envelopes, got {len(withheld_envelopes)}"
    assert len(public_envelopes) == 680, f"Expected 680 public envelopes, got {len(public_envelopes)}"

    for env in withheld_envelopes:
        assert env.document_id not in retrieval_doc_ids, f"Withheld doc {env.document_id} leaked into retrieval corpus!"

    for env in public_envelopes:
        assert env.document_id in retrieval_doc_ids, f"Public doc {env.document_id} missing from retrieval corpus!"


# ==============================================================================
# 6. Condition Operationalization & Evidence Degradation
# ==============================================================================

def test_missing_evidence_condition_guarantee(test_manifest_data, test_corpus_data):
    """Verify missing_evidence positive cases genuinely omit primary joint burglary report from retrieval."""
    retrieval_docs = test_corpus_data["retrieval_docs"]
    retrieval_doc_ids = {doc["doc_id"] for doc in retrieval_docs}

    missing_ev_cases = [c for c in test_manifest_data["cases"] if c["condition"] == "missing_evidence" and c["label"] == 1]
    assert len(missing_ev_cases) == 20

    # Ensure no retrieval incident report mentions both target entities together
    for case in missing_ev_cases:
        ea, eb = case["target_pair"]
        for doc in retrieval_docs:
            if doc["doc_type"] == "incident_report":
                text = doc["text_content"]
                assert not (ea in text and eb in text), (
                    f"Leakage: Joint incident report for {ea} & {eb} found in retrieval doc {doc['doc_id']}!"
                )

    # Check withheld primary records in provenance
    withheld_count = sum(1 for env in test_corpus_data["provenances"] if env["generation_rule"] == "RULE_MISSING_PRIMARY_INCIDENT_REPORT")
    assert withheld_count == 20


def test_distractor_evidence_construction(test_manifest_data, test_corpus_data):
    """Verify exactly 120 distractor incident reports are generated under RULE_DISTRACTOR_INCIDENT_REPORT."""
    distractor_cases = [c for c in test_manifest_data["cases"] if c["condition"] == "distractors"]
    assert len(distractor_cases) == 40
    mixed_cases = [c for c in test_manifest_data["cases"] if c["condition"] == "mixed_difficulty"]
    assert len(mixed_cases) == 40

    provenances = test_corpus_data["provenances"]
    distractor_envs = [
        env for env in provenances
        if env["generation_rule"] == "RULE_DISTRACTOR_INCIDENT_REPORT"
    ]
    # 40 distractors cases * 2 distractors = 80 distractor reports
    # 40 mixed_difficulty cases * 1 distractor = 40 distractor reports
    # Total = 120 distractor reports
    assert len(distractor_envs) == 120, f"Expected 120 distractor reports, found {len(distractor_envs)}"


# ==============================================================================
# 7. Strict Zero-Leakage Safeguards
# ==============================================================================

def test_retrieval_corpus_zero_leakage(test_corpus_data):
    """Verify absolute absence of original CIDs, case IDs, labels, and conditions from retrieval corpus."""
    cid_pattern = re.compile(r"CID#?\d+", re.IGNORECASE)
    test_case_pattern = re.compile(r"TEST_\d+", re.IGNORECASE)
    pilot_case_pattern = re.compile(r"PILOT_\d+", re.IGNORECASE)
    forbidden_terms = [
        "ground_truth", "ground truth", "is_co_offender", "label: 1", "label: 0",
        "clean_evidence", "alias_ambiguity", "missing_evidence", "distractors", "mixed_difficulty"
    ]

    for doc in test_corpus_data["retrieval_docs"]:
        combined = doc["text_content"] + " " + json.dumps(doc["metadata"])
        assert not cid_pattern.search(combined), f"Leakage: CID in doc {doc['doc_id']}"
        assert not test_case_pattern.search(combined), f"Leakage: TEST_ in doc {doc['doc_id']}"
        assert not pilot_case_pattern.search(combined), f"Leakage: PILOT_ in doc {doc['doc_id']}"

        lower = combined.lower()
        for term in forbidden_terms:
            assert term not in lower, f"Leakage: Forbidden term '{term}' in doc {doc['doc_id']}"


def test_unlabelled_input_zero_leakage(test_target_pairs_data, test_manifest_data):
    """Verify unlabelled input pairs manifest has strictly unlabelled inputs without labels/conditions."""
    # 1. Structural schema validation
    assert set(test_target_pairs_data.keys()) == {"description", "total_pairs", "pairs"}
    assert test_target_pairs_data["total_pairs"] == 200
    pairs = test_target_pairs_data["pairs"]
    assert len(pairs) == 200

    # 2. Key and value checks on target pairs
    oid_pattern = re.compile(r"^OID#\d+$")
    for i, pair in enumerate(pairs):
        assert isinstance(pair, list)
        assert len(pair) == 2
        ea, eb = pair
        assert oid_pattern.match(ea) and oid_pattern.match(eb)
        assert ea != eb
        # Verify pair matches quarantined manifest target pair in exact order
        m_case = test_manifest_data["cases"][i]
        assert [ea, eb] == m_case["target_pair"]

    # 3. Confirm absence of label/condition/rationale/CID keys or values in pairs payload
    pairs_json = json.dumps(pairs).lower()
    for forbidden in ["label", "condition", "rationale", "citation", "ground_truth", "cid#", "case_id"]:
        assert forbidden not in pairs_json, f"Leakage: '{forbidden}' found in pairs payload!"

    # 4. Verify experiment system modules do not import or read vault / provenance files
    system_files = [
        os.path.join(EXPERIMENT_DIR, "system_a.py"),
        os.path.join(EXPERIMENT_DIR, "system_b.py"),
        os.path.join(EXPERIMENT_DIR, "runner.py"),
    ]
    for sf in system_files:
        with open(sf, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=sf)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "vault" not in alias.name and "provenance" not in alias.name
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert "vault" not in mod and "provenance" not in mod


# ==============================================================================
# 8. Deterministic Generation Reproducibility
# ==============================================================================

def test_deterministic_generation_reproducibility():
    """
    Verify that rebuilding the test manifest and evidence corpus is:
    1. Byte-for-byte deterministic between two independent runs in the current environment.
    2. Semantically identical across runs and against the frozen repository baseline.
    3. Platform-independently identical to the frozen baseline after normalizing line endings (CRLF vs LF).
    4. Free of any unintended mutation to the frozen repository assets.
    """
    import tempfile
    from pathlib import Path
    from build_test_benchmark import save_test_benchmark
    from generate_test_evidence import save_test_evidence_corpus

    # Canonical frozen SHA-256 hashes (raw Windows CRLF serialization)
    expected_frozen_hashes = {
        "test_manifest.json": "0f5bdc943f9fb51314efb2b1fec8baa2828772feb040980585d0b18f892f12af",
        "test_ground_truth.json": "3f1e9021538be563ea8de015b076ca3a9e2bb75684ae04dcdbd52c7f3e7b8e33",
        "test_target_pairs.json": "125e012b794440c6db8170bb4aa9c385472780bddc1174c6ba7e76096c711cd0",
        "test_retrieval_documents.jsonl": "72d00c6250a73a385fef10792b38fa30aaae8b8a96dff94420e092980caf1349",
        "test_internal_provenance.jsonl": "e32a102d6a74469799d2488404b049bd602543ff4dba878d26024ef096f77555",
    }

    # Canonical line-ending-normalized SHA-256 hashes (LF-normalized byte sequence)
    expected_normalized_hashes = {
        "test_manifest.json": "bd8e1277c5aed505838f0fa89b39f923bae7f5376d2ecc7a99e826ed4e9d9148",
        "test_ground_truth.json": "1adfd2592a160c7661970053d4f6d020f01817be021918753c8b3d1aa1902814",
        "test_target_pairs.json": "e2db9bd9e6a7c2f8e64af22290d9bfefb577048d1b2d2daf0d479a374b4f86fb",
        "test_retrieval_documents.jsonl": "6c85c8390affb38201fd99e7112f69e9795fec89bf0bd99c6210b6bf825521b1",
        "test_internal_provenance.jsonl": "c578e0b4e3e88d7d5513144d962f3a9a3397a875276bc4365e6512614764e8d2",
    }

    # Helper to resolve repository path
    def _repo_path(fname: str) -> str:
        if fname in ["test_manifest.json", "test_ground_truth.json"]:
            return os.path.join(VAULT_DIR, fname)
        elif fname == "test_target_pairs.json":
            return os.path.join(EXPERIMENT_DIR, fname)
        else:
            return os.path.join(CORPUS_DIR, fname)

    # 1. Confirm initial frozen repository assets match established baselines byte-for-byte (if present in repo)
    for fname, exp_hash in expected_frozen_hashes.items():
        fpath = _repo_path(fname)
        if os.path.exists(fpath):
            assert _sha256_file(fpath) == exp_hash, f"Frozen asset {fname} has drifted before test!"
            assert _sha256_normalized(fpath) == expected_normalized_hashes[fname], (
                f"Frozen asset {fname} normalized hash mismatch before test!"
            )

    raw_data_path = os.path.join(REPO_ROOT, "phase1_dataset_audit", "data", "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")
    if not os.path.exists(raw_data_path):
        pytest.skip(
            "Raw Israel National Police source dataset missing from repository "
            "(excluded from public git tree due to unverified redistribution permission). "
            "Deterministic benchmark regeneration requires authorized upstream data access."
        )

    with tempfile.TemporaryDirectory() as tmp_dir_1, tempfile.TemporaryDirectory() as tmp_dir_2:
        # Generation 1 in isolated temporary directory
        save_test_benchmark(output_vault_dir=tmp_dir_1, output_exp_dir=tmp_dir_1)
        save_test_evidence_corpus(
            output_corpus_dir=tmp_dir_1,
            manifest_path=os.path.join(tmp_dir_1, "test_manifest.json")
        )

        # Generation 2 in independent isolated temporary directory
        save_test_benchmark(output_vault_dir=tmp_dir_2, output_exp_dir=tmp_dir_2)
        save_test_evidence_corpus(
            output_corpus_dir=tmp_dir_2,
            manifest_path=os.path.join(tmp_dir_2, "test_manifest.json")
        )

        for fname in expected_frozen_hashes.keys():
            path_1 = os.path.join(tmp_dir_1, fname)
            path_2 = os.path.join(tmp_dir_2, fname)
            fpath = _repo_path(fname)

            # ------------------------------------------------------------------
            # Check A: Semantic equality between independent runs (Run 1 vs Run 2)
            # ------------------------------------------------------------------
            if fname.endswith(".json"):
                with open(path_1, "r", encoding="utf-8") as f1, open(path_2, "r", encoding="utf-8") as f2:
                    assert json.load(f1) == json.load(f2), f"Semantic disparity between runs for {fname}!"
            elif fname.endswith(".jsonl"):
                with open(path_1, "r", encoding="utf-8") as f1, open(path_2, "r", encoding="utf-8") as f2:
                    lines1 = [json.loads(line) for line in f1 if line.strip()]
                    lines2 = [json.loads(line) for line in f2 if line.strip()]
                    assert lines1 == lines2, f"Semantic disparity between runs for {fname}!"
                    assert len(lines1) == len(lines2), f"Line count disparity between runs for {fname}!"

            # ------------------------------------------------------------------
            # Check B: Byte-for-byte identity between independent runs (Run 1 vs Run 2)
            # (Generated in same environment -> must be byte-for-byte identical)
            # ------------------------------------------------------------------
            hash_1 = _sha256_file(path_1)
            hash_2 = _sha256_file(path_2)
            assert hash_1 == hash_2, f"Non-deterministic byte generation between runs for {fname}!"
            assert Path(path_1).read_bytes() == Path(path_2).read_bytes()

            # ------------------------------------------------------------------
            # Check C: Semantic equality between generated artifact and frozen baseline (if present)
            # ------------------------------------------------------------------
            if os.path.exists(fpath):
                if fname.endswith(".json"):
                    with open(path_1, "r", encoding="utf-8") as f1, open(fpath, "r", encoding="utf-8") as ff:
                        assert json.load(f1) == json.load(ff), (
                            f"Semantic disparity between generated and frozen baseline for {fname}!"
                        )
                elif fname.endswith(".jsonl"):
                    with open(path_1, "r", encoding="utf-8") as f1, open(fpath, "r", encoding="utf-8") as ff:
                        lines_gen = [json.loads(line) for line in f1 if line.strip()]
                        lines_froz = [json.loads(line) for line in ff if line.strip()]
                        assert lines_gen == lines_froz, (
                            f"Semantic disparity between generated and frozen baseline for {fname}!"
                        )
                        assert len(lines_gen) == len(lines_froz), (
                            f"Line count disparity between generated and frozen baseline for {fname}!"
                        )

            # ------------------------------------------------------------------
            # Check D: Platform-independent normalized comparison against frozen baseline
            # (Normalizes CRLF -> LF so that Windows vs Unix line endings do not cause false failures)
            # ------------------------------------------------------------------
            norm_bytes_gen = Path(path_1).read_bytes().replace(b"\r\n", b"\n")
            norm_hash_gen = hashlib.sha256(norm_bytes_gen).hexdigest()
            assert norm_hash_gen == expected_normalized_hashes[fname], (
                f"Generated normalized hash for {fname} ({norm_hash_gen}) does not match "
                f"expected normalized baseline ({expected_normalized_hashes[fname]})!"
            )

            # ------------------------------------------------------------------
            # Check E: Distinguish exact byte match from line-ending-only variance
            # ------------------------------------------------------------------
            if os.path.exists(fpath):
                raw_hash_gen = hash_1
                exp_raw_hash = expected_frozen_hashes[fname]
                if raw_hash_gen != exp_raw_hash:
                    # If raw byte hashes differ, confirm that the ONLY difference is CRLF vs LF line endings
                    raw_bytes_gen = Path(path_1).read_bytes()
                    raw_bytes_froz = Path(fpath).read_bytes()
                    crlf_diff_only = (
                        raw_bytes_gen.replace(b"\r\n", b"\n") == raw_bytes_froz.replace(b"\r\n", b"\n")
                    )
                    assert crlf_diff_only, (
                        f"Generated {fname} differs substantively from frozen baseline beyond line endings!\n"
                        f"Raw hash: {raw_hash_gen}\n"
                        f"Expected frozen hash: {exp_raw_hash}\n"
                        f"Normalized hash: {norm_hash_gen}"
                    )

    # 2. Separately confirm that frozen repository files were NOT mutated during test
    for fname, exp_hash in expected_frozen_hashes.items():
        fpath = _repo_path(fname)
        if os.path.exists(fpath):
            assert _sha256_file(fpath) == exp_hash, f"Frozen asset {fname} was mutated during test!"
            assert _sha256_normalized(fpath) == expected_normalized_hashes[fname], (
                f"Frozen asset {fname} normalized hash mutated during test!"
            )
