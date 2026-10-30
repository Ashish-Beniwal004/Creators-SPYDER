"""Post-execution scoring for phase3_llm runs. Never imported by inference.

Binary labels answer documented co-offending, not whether the retrieved evidence
justifies an assertion. Human citation review is recorded separately.
"""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from .evaluator import QUALIFYING_EVIDENCE_RULES, compute_descriptive_metrics
from .schemas import SystemCaseOutput, TargetPairInput
from phase2_verification.verifier import HypothesisVerifier

ARMS = ("system_a_rag_only", "system_b_rag_verification")
DECISIONS = {"Supported", "Unsupported", "Insufficient Evidence"}
REVIEW_FIELDS = ["arm", "entity_a", "entity_b", "model_decision", "cited_doc_ids",
                 "retrieved_doc_ids", "model_rationale", "reference_status",
                 "support_assessment", "reviewer", "notes"]


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def pair_key(pair):
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise ValueError("Expected a two-entity target pair")
    TargetPairInput(entity_a=pair[0], entity_b=pair[1])
    return tuple(sorted(pair))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def metrics(outputs, labels):
    if not outputs:
        return None  # no observations is not zero accuracy
    return compute_descriptive_metrics(
        [labels[p]["label"] for p in outputs],
        [int(o["decision"] == "Supported") for o in outputs.values()],
    ).model_dump()


def manual_review(path, completed):
    """No ratings are inferred from labels or from the deterministic verifier."""
    rows, seen = [], set()
    input_rows = []
    if path is not None:
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            input_rows = list(csv.DictReader(handle))
    for row in input_rows:
        key = (row["arm"], pair_key([row["entity_a"], row["entity_b"]]))
        require(key in completed and key not in seen, "Unknown or duplicate manual review execution")
        seen.add(key)
        output = completed[key]
        require(row.get("model_decision") == output["decision"], "Manual review refers to a different decision")
        require(row.get("cited_doc_ids") == json.dumps(output["cited_doc_ids"]), "Manual review citations changed")
        require(row.get("retrieved_doc_ids") == json.dumps(output["retrieved_doc_ids"]), "Manual review retrieval changed")
        require(row.get("model_rationale") == output["rationale"], "Manual review rationale changed")
        assessment, reference = row.get("support_assessment", "").strip(), row.get("reference_status", "").strip()
        require(assessment in {"", "supported", "unsupported", "indeterminate"}, "Invalid support assessment")
        require(not reference or reference in DECISIONS, "Invalid manual reference status")
        if assessment or reference:
            require(bool(row.get("reviewer", "").strip()), "Rated rows need a reviewer")
            rows.append((key, assessment, reference))
    report = {}
    for arm in ARMS:
        selected = [(p, a, r) for (ar, p), a, r in rows if ar == arm]
        positive = [a for p, a, _ in selected if completed[(arm, p)]["decision"] == "Supported" and a]
        references = [(p, r) for p, _, r in selected if r]
        decisive_positives = [a for a in positive if a != "indeterminate"]
        report[arm] = {
            "rated_executions": len(selected), "reviewed_positive_assertions": len(positive),
            "positive_support_assessments": dict(Counter(positive)),
            "decisively_reviewed_positive_assertions": len(decisive_positives),
            "manual_unsupported_assertion_rate": ratio(positive.count("unsupported"), len(decisive_positives)),
            "three_way_reference_count": len(references),
            "three_way_accuracy": ratio(sum(completed[(arm, p)]["decision"] == r for p, r in references), len(references)),
        }
    return report


def score_run(*, run_dir, labels_path, pairs_path, corpus_path, output_dir,
              provenance_path=None, manual_review_path=None):
    run_dir, output_dir = Path(run_dir).resolve(), Path(output_dir).resolve()
    require(not output_dir.exists(), "Choose a new scoring directory")
    require(run_dir != output_dir and run_dir not in output_dir.parents, "Keep scores outside the frozen run")
    protected = Path(__file__).resolve().parent / "outputs"
    require(output_dir != protected and protected not in output_dir.parents, "Historical outputs are protected")
    manifest = read_json(run_dir / "manifest.json")
    hashes = manifest["artifact_hashes"]
    required = {"config.json", "results.jsonl", "retrieval.jsonl", "traces.jsonl", "errors.jsonl"}
    require(required <= set(hashes), "Run manifest lacks required artifact hashes")
    for name, digest in hashes.items():
        path = run_dir / name
        require(Path(name).name == name and path.resolve().parent == run_dir, "Unsafe artifact path")
        require(file_hash(path) == digest, f"Artifact hash mismatch: {name}")
    config = read_json(run_dir / "config.json")
    require(config == manifest["parameters"], "Config and manifest parameters differ")
    require(config.get("implementation") == "phase3_llm" and config.get("schema_version") == "1.0", "Unsupported run schema")
    require(config.get("mode") in {"mock", "smoke", "experiment"}, "Invalid run mode")
    require(config.get("scientific_results") == (config["mode"] == "experiment"), "Inconsistent experiment flag")
    require(config["mode"] != "experiment" or config["model"]["provider"] != "mock", "Mock is not an experiment")
    require(manifest["status"] in {"completed", "incomplete", "interrupted"}, "Run has not been finalized")

    pairs_doc = read_json(pairs_path)
    require(set(pairs_doc) <= {"pairs", "total_pairs", "description"}, "Unexpected target file fields")
    # TargetPair.ids in the runner canonicalizes entity order within each pair.
    pairs = [list(pair_key(pair)) for pair in pairs_doc["pairs"]]
    ordered_keys = [pair_key(p) for p in pairs]
    require(len(set(ordered_keys)) == len(pairs) > 0, "Duplicate or empty target cohort")
    require("total_pairs" not in pairs_doc or pairs_doc["total_pairs"] == len(pairs), "Target count differs")
    pair_digest = hashlib.sha256(json.dumps(pairs, sort_keys=True, allow_nan=False).encode()).hexdigest()
    require(config["target_pairs_sha256"] == pair_digest, "Target cohort/order differs from run")
    for name, path in (("corpus", corpus_path), ("pairs", pairs_path)):
        digest = config.get("dataset", {}).get(f"{name}_sha256")
        require(digest is not None and digest == file_hash(path), f"Missing or mismatched {name} hash")
    label_doc = read_json(labels_path)
    labels = {}
    for case in label_doc["cases"]:
        key = pair_key(case["target_pair"])
        require(key not in labels and type(case["label"]) is int and case["label"] in (0, 1), "Invalid/duplicate label")
        require(isinstance(case["condition"], str) and bool(case["condition"]), "Missing condition")
        labels[key] = case
    require(set(labels) == set(ordered_keys), "Labels must cover exactly the executed target cohort")
    require(len({c["case_id"] for c in labels.values()}) == len(labels), "Duplicate label case IDs")
    corpus_rows = read_jsonl(corpus_path)
    corpus = {d["doc_id"]: d for d in corpus_rows}
    require(len(corpus) == len(corpus_rows), "Duplicate corpus document IDs")
    verifier = HypothesisVerifier(str(corpus_path))  # also validates sanitized corpus

    def context(record, arm=False):
        index = record["case_index"]
        require(type(index) is int and 0 <= index < len(pairs), "Invalid case index")
        require(record["run_id"] == manifest["run_id"] and record["target_pair"] == pairs[index], "Run/pair context differs")
        if arm:
            require(record["arm"] in ARMS, "Unknown experimental arm")
        return ordered_keys[index]

    retrieval = {}
    for record in read_jsonl(run_dir / "retrieval.jsonl"):
        key = context(record)
        require(key not in retrieval, "Duplicate retrieval record")
        ids = [d["doc_id"] for d in record["evidence"]]
        require(len(set(ids)) == len(ids) <= config["top_k"], "Invalid retrieval document count")
        for doc in record["evidence"]:
            require(doc["doc_id"] in corpus, "Retrieved document not in corpus")
            source = corpus[doc["doc_id"]]
            require(all(doc[k] == source[k] for k in ("text_content", "doc_type")), "Retrieved evidence differs from corpus")
            require(type(doc["score"]) in (int, float) and math.isfinite(doc["score"]), "Invalid retrieval score")
        retrieval[key] = record

    executions, completed, failures = {}, {}, []
    for record in read_jsonl(run_dir / "results.jsonl"):
        pair = context(record, arm=True)
        key = (record["arm"], pair)
        require(key not in executions, "Duplicate execution result")
        executions[key] = record
        require(type(record["model_calls"]) is int and record["model_calls"] >= 0, "Invalid model call count")
        if record["execution_status"] == "failed":
            require("output" not in record, "Failed execution cannot contain a business verdict")
            failures.append(record)
            continue
        require(record["execution_status"] == "completed", "Invalid execution status")
        out = SystemCaseOutput.model_validate(record["output"]).model_dump(mode="json")
        require(out["arm"] == key[0] and out["case_index"] == record["case_index"], "Output context differs")
        require(out["target_pair"] == record["target_pair"] == [out["entity_a"], out["entity_b"]], "Output target differs")
        require(out["is_supported"] == (out["decision"] == "Supported"), "Inconsistent decision flag")
        require(pair in retrieval, "Completed output lacks shared retrieval")
        retrieved = retrieval[pair]
        ids = [d["doc_id"] for d in retrieved["evidence"]]
        require(out["retrieved_doc_ids"] == ids and out["retrieval_query"] == retrieved["query"], "Output retrieval differs")
        require(out["retrieval_scores"] == {d["doc_id"]: d["score"] for d in retrieved["evidence"]}, "Output scores differ")
        citations = out["cited_doc_ids"]
        require(len(set(citations)) == len(citations) and set(citations) <= set(ids), "Invalid or unseen citations")
        require(out["decision"] != "Supported" or bool(citations), "Supported assertion lacks citations")
        completed[key] = out
    require(read_jsonl(run_dir / "errors.jsonl") == failures, "Errors/results logs differ")
    require(manifest["expected_executions"] == 2 * len(pairs), "Expected execution count differs")
    require(manifest["completed_executions"] == len(completed) and manifest["failed_executions"] == len(failures), "Manifest execution counts differ")
    missing = 2 * len(pairs) - len(executions)
    require(manifest["unattempted_executions"] == missing, "Missing-record count differs")
    require(manifest["status"] != "completed" or len(completed) == 2 * len(pairs), "Completed manifest has incomplete results")

    traces = read_jsonl(run_dir / "traces.jsonl")
    trace_counts, usage = {a: Counter() for a in ARMS}, {a: Counter() for a in ARMS}
    for trace in traces:
        context(trace, arm=True)
        arm, event, data = trace["arm"], trace["event"], trace["data"]
        trace_counts[arm][event] += 1
        if event == "model_response":
            trace_counts[arm]["requested_tool_calls"] += len(data.get("tool_calls", []))
        if event == "provider_response":
            for name, value in data.get("raw", {}).get("usage", {}).items():
                if type(value) in (int, float) and math.isfinite(value):
                    usage[arm][name] += value
    require(sum(t["model_request"] for t in trace_counts.values()) == manifest["attempted_model_calls"], "Attempted calls differ from traces")
    if "provider_requests_sent" in manifest:
        require(sum(t["provider_request"] for t in trace_counts.values()) == manifest["provider_requests_sent"], "Sent requests differ from traces")

    by_arm = {a: {p: o for (ar, p), o in completed.items() if ar == a} for a in ARMS}
    paired = set(by_arm[ARMS[0]]) & set(by_arm[ARMS[1]])
    arm_reports = {}
    for arm in ARMS:
        outputs, counts = by_arm[arm], trace_counts[arm]
        consistent = sum(bool(o["cited_doc_ids"]) and verifier.verify(*p, o["cited_doc_ids"]).status == "Supported"
                         for p, o in outputs.items() if o["decision"] == "Supported")
        positives = sum(o["decision"] == "Supported" for o in outputs.values())
        requested, accepted = counts["requested_tool_calls"], counts["tool_accepted"]
        require(accepted <= requested, "Accepted tool count exceeds requested count")
        failed_count = sum(ar == arm and r["execution_status"] == "failed" for (ar, _), r in executions.items())
        arm_reports[arm] = {
            "coverage": {"expected": len(pairs), "completed": len(outputs), "failed": failed_count,
                         "missing_result_records": len(pairs) - len(outputs) - failed_count},
            "binary_metrics_completed_only": metrics(outputs, labels),
            "decisions": dict(Counter(o["decision"] for o in outputs.values())),
            "insufficient_evidence_rate": ratio(sum(o["decision"] == "Insufficient Evidence" for o in outputs.values()), len(outputs)),
            "per_condition": {condition: metrics({p: o for p, o in outputs.items() if labels[p]["condition"] == condition}, labels)
                              for condition in sorted({c["condition"] for c in labels.values()})},
            "verifier_consistency_on_positive_citations": {"consistent": consistent, "positive_assertions": positives,
                                                         "rate": ratio(consistent, positives), "independent_validation": False},
            "calls": {"attempted_model_calls": counts["model_request"], "requested_tool_calls": requested,
                      "provider_requests_sent": counts["provider_request"],
                      "accepted_tool_calls": accepted, "unaccepted_tool_calls": requested - accepted,
                      "completed_tool_calls": counts["tool_result"], "tool_call_validity_rate": ratio(accepted, requested)},
            "provider_reported_usage": dict(usage[arm]),
        }
    retrieval_report = None
    if provenance_path is not None:
        provenance = read_jsonl(provenance_path)
        relevant, withheld = defaultdict(set), defaultdict(set)
        case_ids = {c["case_id"]: p for p, c in labels.items()}
        for row in provenance:
            if row["ground_truth_case_id"] in case_ids and row["generation_rule"] in QUALIFYING_EVIDENCE_RULES:
                p, did = case_ids[row["ground_truth_case_id"]], row["document_id"]
                (relevant if did in corpus else withheld)[p].add(did)
        eligible = [p for p in retrieval if relevant[p]]
        hits = {p: relevant[p] & {d["doc_id"] for d in retrieval[p]["evidence"]} for p in eligible}
        retrieval_report = {"top_k": config["top_k"], "observed_pairs": len(retrieval), "pairs_with_available_support_docs": len(eligible),
                            "support_doc_recall": ratio(sum(map(len, hits.values())), sum(len(relevant[p]) for p in eligible)),
                            "all_support_documents_retrieved_rate": ratio(sum(hits[p] == relevant[p] for p in eligible), len(eligible)),
                            "withheld_support_documents": sum(map(len, withheld.values())),
                            "note": "Generation-rule relevance diagnostic; absent/withheld documents are excluded from recall denominators."}
    inputs = {"manifest": run_dir / "manifest.json", "labels": labels_path, "pairs": pairs_path, "corpus": corpus_path}
    if provenance_path is not None:
        inputs["provenance"] = provenance_path
    if manual_review_path is not None:
        inputs["manual_review"] = manual_review_path
    report = {
        "scored_at": datetime.now(timezone.utc).isoformat(), "run_id": manifest["run_id"],
        "run_status": manifest["status"], "mode": config["mode"],
        "model": config["model"], "dataset": config.get("dataset", {}), "top_k": config["top_k"],
        "complete_experiment_run": config["mode"] == "experiment" and manifest["status"] == "completed",
        "input_sha256": {name: file_hash(path) for name, path in inputs.items()},
        "scorer_sha256": file_hash(__file__), "verifier_sha256": file_hash(Path(__file__).parents[1] / "phase2_verification" / "verifier.py"),
        "definitions": {"binary": "Supported=1; Unsupported and Insufficient Evidence=0. This is not three-way evidence correctness.",
                        "missing": "Failed or missing executions are excluded from decision metrics and counted separately.",
                        "manual_review": "Human ratings only. Reference status uses all retrieved evidence; support assessment judges the positive assertion using its citations. Unsupported assertion rate excludes indeterminate assessments from its denominator; their count is shown separately.",
                        "limitations": "Synthetic corpus; development exposure and repeated entities preclude unqualified generalization or independent-case significance claims. No cost inferred from tokens."},
        "arms": arm_reports, "paired_completed_count": len(paired),
        "paired_completed_binary_metrics": {a: metrics({p: o for p, o in by_arm[a].items() if p in paired}, labels) for a in ARMS},
        "retrieval": retrieval_report, "manual_review": manual_review(manual_review_path, completed),
    }
    # Only after validating everything do we create the new destination.
    output_dir.mkdir(parents=True, exist_ok=False)
    with (output_dir / "report.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    with (output_dir / "review_template.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for (arm, p), out in completed.items():
            writer.writerow({"arm": arm, "entity_a": p[0], "entity_b": p[1], "model_decision": out["decision"],
                             "cited_doc_ids": json.dumps(out["cited_doc_ids"]), "retrieved_doc_ids": json.dumps(out["retrieved_doc_ids"]),
                             "model_rationale": out["rationale"]})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("run-dir", "labels", "pairs", "corpus", "output-dir"):
        parser.add_argument(f"--{flag}", type=Path, required=True)
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--manual-review", type=Path)
    args = parser.parse_args(argv)
    try:
        report = score_run(run_dir=args.run_dir, labels_path=args.labels, pairs_path=args.pairs,
                           corpus_path=args.corpus, output_dir=args.output_dir,
                           provenance_path=args.provenance, manual_review_path=args.manual_review)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Scoring rejected: {exc}\n")
    print(json.dumps({"run_id": report["run_id"], "status": report["run_status"],
                      "paired_completed": report["paired_completed_count"], "output_dir": str(args.output_dir)}, indent=2))


if __name__ == "__main__":
    main()
