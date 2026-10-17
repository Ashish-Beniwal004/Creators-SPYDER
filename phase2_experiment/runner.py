"""
Phase 2E & 2G Deterministic Experimental Runner
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_experiment/runner.py

Orchestrates deterministic experimental evaluation comparing:
- System A: RAG-only
- System B: RAG + Verification

Supported Dataset Regimes:
- 'pilot': 10-case pilot dataset (default, preserves frozen pilot behavior).
- 'full_test': 200-case full benchmark test set.

Strict Quarantine:
- Runner does NOT import or read quarantined vault files or provenance.
- Does NOT expose labels, case IDs, or condition names to either system.
- Does NOT construct queries with hidden fields.
- Saves immutable raw outputs and an execution manifest.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any, Union

# Ensure repository root in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_experiment.config import (
    PUBLIC_CORPUS_PATH,
    DEFAULT_OUTPUTS_DIR,
    DEFAULT_TOP_K,
    PIPELINE_METADATA,
    DATASET_CONFIGS,
    DEFAULT_DATASET_MODE,
)
from phase2_experiment.schemas import (
    ArmRunResult,
    PilotRunManifest,
    BenchmarkRunManifest,
    SystemCaseOutput,
    TargetPairInput,
)
from phase2_retrieval.retriever import EvidenceRetriever
from phase2_verification.verifier import HypothesisVerifier
from phase2_experiment.system_a import run_system_a
from phase2_experiment.system_b import run_system_b

DEFAULT_TARGETS_FILE = os.path.join(REPO_ROOT, "phase2_experiment", "pilot_target_pairs.json")


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_corpus_doc_ids(corpus_path: str = PUBLIC_CORPUS_PATH) -> set:
    """Loads all valid doc_ids from the sanitized retrieval corpus for integrity checking."""
    doc_ids = set()
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                data = json.loads(line_str)
                doc_ids.add(data["doc_id"])
    return doc_ids


def normalize_target_pairs(raw_data: Any) -> List[Tuple[str, str]]:
    """
    Normalizes diverse unlabelled target-pair inputs into validated canonical tuples:
    - dict with 'pairs': [[ea, eb], ...]
    - dict with 'cases': [{'entity_a': ea, 'entity_b': eb}, ...] or [{'target_pair': [ea, eb]}, ...]
    - list of [ea, eb] or (ea, eb)
    - list of dicts: [{'entity_a': ea, 'entity_b': eb}, ...]
    Enforces TargetPairInput validation on every pair (non-reflexive, OID#<digits> syntax).
    """
    pairs_list: List[Tuple[str, str]] = []

    if isinstance(raw_data, dict):
        if "pairs" in raw_data and isinstance(raw_data["pairs"], list):
            raw_items = raw_data["pairs"]
        elif "cases" in raw_data and isinstance(raw_data["cases"], list):
            raw_items = raw_data["cases"]
        else:
            raise ValueError("Input dictionary must contain 'pairs' or 'cases' key.")
    elif isinstance(raw_data, list):
        raw_items = raw_data
    else:
        raise ValueError(f"Unsupported target pair input type: {type(raw_data).__name__}")

    for idx, item in enumerate(raw_items):
        if isinstance(item, (list, tuple)) and len(item) == 2:
            ea, eb = str(item[0]).strip(), str(item[1]).strip()
        elif isinstance(item, dict):
            if "entity_a" in item and "entity_b" in item:
                ea, eb = str(item["entity_a"]).strip(), str(item["entity_b"]).strip()
            elif "target_pair" in item and isinstance(item["target_pair"], (list, tuple)) and len(item["target_pair"]) == 2:
                ea, eb = str(item["target_pair"][0]).strip(), str(item["target_pair"][1]).strip()
            else:
                raise ValueError(f"Case at index {idx} missing recognized pair keys: {list(item.keys())}")
        else:
            raise ValueError(f"Item at index {idx} is not a valid 2-element sequence or dict: {item}")

        # Validate through strict TargetPairInput model
        validated = TargetPairInput(entity_a=ea, entity_b=eb)
        pairs_list.append((validated.entity_a, validated.entity_b))

    if not pairs_list:
        raise ValueError("Target pairs list cannot be empty.")

    return pairs_list


def load_target_pairs(targets_path: str = DEFAULT_TARGETS_FILE) -> List[Tuple[str, str]]:
    """Loads unlabelled target entity pairs from sanitized input JSON using normalize_target_pairs."""
    if not os.path.exists(targets_path):
        raise FileNotFoundError(f"Target pairs file not found: {targets_path}")
    with open(targets_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return normalize_target_pairs(data)


def run_arm(
    arm_name: str,
    target_pairs: List[Tuple[str, str]],
    run_id: str,
    top_k: int = DEFAULT_TOP_K,
    retriever: Optional[EvidenceRetriever] = None,
    verifier: Optional[HypothesisVerifier] = None,
    corpus_path: Optional[str] = None
) -> ArmRunResult:
    """Executes a single experimental arm over the target pairs."""
    results: List[SystemCaseOutput] = []

    for idx, (ent_a, ent_b) in enumerate(target_pairs):
        if arm_name == "system_a_rag_only":
            case_out = run_system_a(
                entity_a=ent_a,
                entity_b=ent_b,
                case_index=idx,
                top_k=top_k,
                retriever=retriever,
                corpus_path=corpus_path
            )
        elif arm_name == "system_b_rag_verification":
            case_out = run_system_b(
                entity_a=ent_a,
                entity_b=ent_b,
                case_index=idx,
                top_k=top_k,
                retriever=retriever,
                verifier=verifier,
                corpus_path=corpus_path
            )
        else:
            raise ValueError(f"Unknown arm name: {arm_name}")
        results.append(case_out)

    return ArmRunResult(
        run_id=run_id,
        arm=arm_name,
        execution_timestamp=datetime.now(timezone.utc).isoformat(),
        parameters={
            "top_k": top_k,
            "pipeline_metadata": PIPELINE_METADATA,
        },
        total_cases=len(results),
        results=results
    )


def run_benchmark(
    dataset_mode: str = "pilot",
    target_pairs: Optional[Any] = None,
    targets_path: Optional[str] = None,
    corpus_path: Optional[str] = None,
    run_id: Optional[str] = None,
    outputs_dir: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K
) -> Tuple[ArmRunResult, ArmRunResult, BenchmarkRunManifest]:
    """
    Executes both System A and System B on target pairs for a specified dataset ('pilot' or 'full_test'),
    validates integrity, and writes immutable raw output files and an execution manifest.
    """
    cfg = DATASET_CONFIGS.get(dataset_mode, DATASET_CONFIGS["pilot"])
    active_corpus_path = corpus_path or cfg["corpus_path"]
    active_targets_path = targets_path or cfg["targets_path"]

    out_dir = outputs_dir or DEFAULT_OUTPUTS_DIR
    os.makedirs(out_dir, exist_ok=True)

    if target_pairs is not None:
        pairs = normalize_target_pairs(target_pairs)
    else:
        pairs = load_target_pairs(active_targets_path)

    active_run_id = run_id or f"{dataset_mode.upper()}_RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Load corpus doc_ids for integrity check
    corpus_doc_ids = load_corpus_doc_ids(active_corpus_path)

    # Initialize retriever and verifier instances once for this run
    retriever = EvidenceRetriever(corpus_path=active_corpus_path)
    verifier = HypothesisVerifier(corpus_path=active_corpus_path)

    # Step 1: Run System A
    result_a = run_arm(
        "system_a_rag_only",
        pairs,
        active_run_id,
        top_k=top_k,
        retriever=retriever,
        corpus_path=active_corpus_path
    )

    # Step 2: Run System B
    result_b = run_arm(
        "system_b_rag_verification",
        pairs,
        active_run_id,
        top_k=top_k,
        retriever=retriever,
        verifier=verifier,
        corpus_path=active_corpus_path
    )

    # Step 3: Integrity assertions
    assert len(result_a.results) == len(pairs), "System A did not process all cases"
    assert len(result_b.results) == len(pairs), "System B did not process all cases"

    for ca, cb in zip(result_a.results, result_b.results):
        # Both received same targets
        assert ca.target_pair == cb.target_pair, f"Target mismatch: {ca.target_pair} vs {cb.target_pair}"
        assert ca.retrieval_query == cb.retrieval_query, f"Query mismatch: {ca.retrieval_query} vs {cb.retrieval_query}"
        assert ca.retrieved_doc_ids == cb.retrieved_doc_ids, "Retrieved docs mismatch between arms"

        # Check all retrieved IDs exist in corpus
        for doc_id in ca.retrieved_doc_ids:
            assert doc_id in corpus_doc_ids, f"Retrieved doc_id '{doc_id}' not in corpus!"

        # For System B, verify cited docs are subset of retrieved docs
        for cited_id in cb.cited_doc_ids:
            assert cited_id in cb.retrieved_doc_ids, f"System B cited unretrieved doc: {cited_id}"

    # Step 4: Write immutable output files
    prefix_a = f"system_a_{dataset_mode}_outputs.json" if dataset_mode != "pilot" else "system_a_pilot_outputs.json"
    prefix_b = f"system_b_{dataset_mode}_outputs.json" if dataset_mode != "pilot" else "system_b_pilot_outputs.json"
    manifest_name = f"{dataset_mode}_run_manifest.json" if dataset_mode != "pilot" else "pilot_run_manifest.json"

    file_a = os.path.join(out_dir, prefix_a)
    file_b = os.path.join(out_dir, prefix_b)

    with open(file_a, "w", encoding="utf-8") as f:
        f.write(result_a.model_dump_json(indent=2))

    with open(file_b, "w", encoding="utf-8") as f:
        f.write(result_b.model_dump_json(indent=2))

    # Step 5: Compute hashes and manifest
    hash_a = compute_file_sha256(file_a)
    hash_b = compute_file_sha256(file_b)
    corpus_hash = compute_file_sha256(active_corpus_path)
    targets_hash = compute_file_sha256(active_targets_path) if os.path.exists(active_targets_path) else None

    try:
        rel_file_a = os.path.relpath(file_a, REPO_ROOT)
    except ValueError:
        rel_file_a = file_a

    try:
        rel_file_b = os.path.relpath(file_b, REPO_ROOT)
    except ValueError:
        rel_file_b = file_b

    manifest = BenchmarkRunManifest(
        manifest_version="1.0",
        run_id=active_run_id,
        dataset_mode=dataset_mode,
        execution_timestamp=datetime.now(timezone.utc).isoformat(),
        corpus_sha256=corpus_hash,
        targets_sha256=targets_hash,
        parameters={
            "top_k": top_k,
            "pipeline_metadata": PIPELINE_METADATA,
            "dataset_config": {
                "dataset_mode": dataset_mode,
                "corpus_path": active_corpus_path,
                "targets_path": active_targets_path
            }
        },
        total_cases=len(pairs),
        system_a_output_file=rel_file_a,
        system_b_output_file=rel_file_b,
        system_a_output_sha256=hash_a,
        system_b_output_sha256=hash_b
    )

    manifest_file = os.path.join(out_dir, manifest_name)
    with open(manifest_file, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    return result_a, result_b, manifest


def run_pilot_experiment(
    target_pairs: Optional[List[Tuple[str, str]]] = None,
    run_id: Optional[str] = None,
    outputs_dir: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K
) -> Tuple[ArmRunResult, ArmRunResult, PilotRunManifest]:
    """
    Executes both System A and System B on pilot target pairs (defaulting to 10 pilot cases),
    validates integrity, and writes immutable raw output files and a pilot run manifest.
    Maintains 100% backward compatibility for all existing pilot callers.
    """
    res_a, res_b, b_man = run_benchmark(
        dataset_mode="pilot",
        target_pairs=target_pairs,
        run_id=run_id,
        outputs_dir=outputs_dir,
        top_k=top_k
    )

    pilot_man = PilotRunManifest(
        manifest_version="1.0",
        run_id=b_man.run_id,
        execution_timestamp=b_man.execution_timestamp,
        corpus_sha256=b_man.corpus_sha256,
        parameters=b_man.parameters,
        total_cases=b_man.total_cases,
        system_a_output_file=b_man.system_a_output_file,
        system_b_output_file=b_man.system_b_output_file,
        system_a_output_sha256=b_man.system_a_output_sha256,
        system_b_output_sha256=b_man.system_b_output_sha256
    )

    # Save pilot_run_manifest.json
    out_dir = outputs_dir or DEFAULT_OUTPUTS_DIR
    p_file = os.path.join(out_dir, "pilot_run_manifest.json")
    with open(p_file, "w", encoding="utf-8") as f:
        f.write(pilot_man.model_dump_json(indent=2))

    return res_a, res_b, pilot_man


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SPYDER Experimental Benchmark Runner")
    parser.add_argument(
        "--dataset",
        choices=["pilot", "full_test"],
        default="pilot",
        help="Select dataset to evaluate ('pilot' or 'full_test', default: 'pilot')"
    )
    args = parser.parse_args()

    print("=" * 70)
    print(f"SPYDER: Executing Experimental Runner over {args.dataset.upper()} Cases")
    print("=" * 70)
    if args.dataset == "full_test":
        res_a, res_b, man = run_benchmark(dataset_mode="full_test")
    else:
        res_a, res_b, man = run_pilot_experiment()
    print(f"Run ID: {man.run_id}")
    print(f"Dataset Mode: {getattr(man, 'dataset_mode', 'pilot')}")
    print(f"Total Cases Evaluated: {man.total_cases}")
    print(f"System A Output: {man.system_a_output_file} (SHA256: {man.system_a_output_sha256[:16]}...)")
    print(f"System B Output: {man.system_b_output_file} (SHA256: {man.system_b_output_sha256[:16]}...)")
    print("Execution complete. Raw outputs frozen successfully.")
