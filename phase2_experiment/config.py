"""
Phase 2E Experimental Configuration and Controls
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_experiment/config.py

Defines fixed, deterministic parameters for the comparative experiment:
- System A: RAG-only
- System B: RAG + Verification
"""

import os
import sys

# Repository Root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Frozen Artifact Paths (Quarantined vs Public)
PUBLIC_CORPUS_PATH = os.path.join(REPO_ROOT, "phase2_corpus", "retrieval_documents.jsonl")
PROVENANCE_PATH = os.path.join(REPO_ROOT, "phase2_corpus", "internal_provenance.jsonl")
GROUND_TRUTH_VAULT_PATH = os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "ground_truth.json")
PILOT_MANIFEST_PATH = os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "pilot_manifest.json")
SPLIT_MANIFEST_PATH = os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "split_manifest.json")

# Explicit Dataset Path Configurations
PILOT_CORPUS_PATH = PUBLIC_CORPUS_PATH
PILOT_PROVENANCE_PATH = PROVENANCE_PATH
PILOT_GROUND_TRUTH_PATH = GROUND_TRUTH_VAULT_PATH
PILOT_TARGETS_PATH = os.path.join(REPO_ROOT, "phase2_experiment", "pilot_target_pairs.json")

FULL_TEST_CORPUS_PATH = os.path.join(REPO_ROOT, "phase2_corpus", "test_retrieval_documents.jsonl")
FULL_TEST_PROVENANCE_PATH = os.path.join(REPO_ROOT, "phase2_corpus", "test_internal_provenance.jsonl")
FULL_TEST_GROUND_TRUTH_PATH = os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "test_ground_truth.json")
FULL_TEST_MANIFEST_PATH = os.path.join(REPO_ROOT, "phase2_ground_truth_vault", "test_manifest.json")
FULL_TEST_TARGETS_PATH = os.path.join(REPO_ROOT, "phase2_experiment", "test_target_pairs.json")

# Path aliases for clarity
PILOT_TARGET_PAIRS_PATH = PILOT_TARGETS_PATH
FULL_TEST_TARGET_PAIRS_PATH = FULL_TEST_TARGETS_PATH
PILOT_RETRIEVAL_DOCUMENTS_PATH = PILOT_CORPUS_PATH
FULL_TEST_RETRIEVAL_DOCUMENTS_PATH = FULL_TEST_CORPUS_PATH

DATASET_CONFIGS = {
    "pilot": {
        "dataset_mode": "pilot",
        "corpus_path": PILOT_CORPUS_PATH,
        "targets_path": PILOT_TARGETS_PATH,
        "target_pairs_path": PILOT_TARGETS_PATH,
        "manifest_path": PILOT_MANIFEST_PATH,
        "ground_truth_path": PILOT_GROUND_TRUTH_PATH,
        "provenance_path": PILOT_PROVENANCE_PATH,
        "expected_cases": 10,
    },
    "full_test": {
        "dataset_mode": "full_test",
        "corpus_path": FULL_TEST_CORPUS_PATH,
        "targets_path": FULL_TEST_TARGETS_PATH,
        "target_pairs_path": FULL_TEST_TARGETS_PATH,
        "manifest_path": FULL_TEST_MANIFEST_PATH,
        "ground_truth_path": FULL_TEST_GROUND_TRUTH_PATH,
        "provenance_path": FULL_TEST_PROVENANCE_PATH,
        "expected_cases": 200,
    }
}
DEFAULT_DATASET_MODE = "pilot"


def get_dataset_config(dataset_mode: str = DEFAULT_DATASET_MODE) -> dict:
    """Retrieve verified dataset configuration by mode ('pilot' or 'full_test')."""
    if dataset_mode not in DATASET_CONFIGS:
        raise ValueError(f"Unknown dataset_mode '{dataset_mode}'. Must be one of: {list(DATASET_CONFIGS.keys())}")
    return dict(DATASET_CONFIGS[dataset_mode])

# Output Directory
DEFAULT_OUTPUTS_DIR = os.path.join(REPO_ROOT, "phase2_experiment", "outputs")

# Shared Retrieval Controls
DEFAULT_TOP_K = 5
MAX_TOP_K = 50
QUERY_TEMPLATE = "{entity_a} {entity_b}"

# Re-retrieval Policy:
# Single-pass retrieval is fixed for the 10-case pilot to guarantee strictly equal evidence budgets.
ENABLE_RE_RETRIEVAL = False
RE_RETRIEVAL_TOP_K = 3

# Frozen SHA-256 Hashes for Artifact Integrity Verification
FROZEN_HASHES = {
    "corpus": (
        os.path.join("phase2_corpus", "retrieval_documents.jsonl"),
        "a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded"
    ),
    "provenance": (
        os.path.join("phase2_corpus", "internal_provenance.jsonl"),
        "ae29dcd873a3f87f01dff4e5dceb3edd041caf64e21f7065d74114ad2f9287bc"
    ),
    "ground_truth": (
        os.path.join("phase2_ground_truth_vault", "ground_truth.json"),
        "87f84a65111bd38a021860247b53362fbf3f92f284a8a2ccd30eeb4089a42963"
    ),
    "pilot_manifest": (
        os.path.join("phase2_ground_truth_vault", "pilot_manifest.json"),
        "ee376e36dde8378109d60eaa7a37102262d717d56a76fe65337dda2098ee9b50"
    ),
    "split_manifest": (
        os.path.join("phase2_ground_truth_vault", "split_manifest.json"),
        "04dc346d4628d1ad59d6b34d3580f6ddb40548e35921f48cc24a0d6a389d0ffd"
    ),
}

# Pipeline Reproducibility Metadata
PIPELINE_METADATA = {
    "pipeline_name": "SPYDER_Phase2E_Experimental_Pipeline",
    "version": "1.0.0",
    "evaluation_window": ("2020-01-01", "2020-06-30"),
    "deterministic": True,
    "random_seed": 42,
    "retriever_type": "TfidfVectorizer + CosineSimilarity",
    "top_k": DEFAULT_TOP_K,
    "enable_re_retrieval": ENABLE_RE_RETRIEVAL,
    "python_version": sys.version.split()[0],
}
