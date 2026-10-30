"""Offline preparation/scoring of the fixed two-block, free-quota pilot.

Never calls a model. The blocks have four/six pairs (12/18 nominal requests).
"""

import argparse
import csv
import json
from pathlib import Path

from .score_run import (ARMS, REVIEW_FIELDS, file_hash, manual_review, metrics,
                        pair_key, read_json, read_jsonl, require, score_run)

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = {"group_1": [0, 3, 4, 7], "group_2": [1, 2, 5, 6, 8, 9]}


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def prepare(directory):
    """Use only unlabelled pairs; selection is fixed before live results exist."""
    directory = Path(directory)
    require(not directory.exists(), "Choose a new campaign directory")
    pairs_path = ROOT / "phase2_experiment/pilot_target_pairs.json"
    corpus_path = ROOT / "phase2_corpus/retrieval_documents.jsonl"
    pairs = read_json(pairs_path)["pairs"]
    require(len(pairs) == 10 and len({pair_key(p) for p in pairs}) == 10, "Expected the frozen ten-pair pilot")
    directory.mkdir(parents=True, exist_ok=False)
    groups = {}
    for name, indexes in BLOCKS.items():
        path = directory / (name + "_pairs.json")
        write_json(path, {"pairs": [pairs[i] for i in indexes], "total_pairs": len(indexes)})
        groups[name] = {"zero_based_indexes": indexes, "pairs_file": path.name, "pairs_sha256": file_hash(path),
                        "expected_executions": 2 * len(indexes), "nominal_model_calls": 3 * len(indexes)}
    campaign = {"schema_version": "1.0", "selection": "fixed index lists, no model-output-based selection",
                "source_pairs_sha256": file_hash(pairs_path), "corpus_sha256": file_hash(corpus_path),
                "groups": groups, "complete_pilot_requires_both_groups": True}
    write_json(directory / "campaign.json", campaign)
    return campaign


def score_campaign(*, directory, runs, output_dir, review_path=None):
    """Validate each native run separately, then pool disjoint completed outputs."""
    directory, output_dir = Path(directory), Path(output_dir)
    require(not output_dir.exists(), "Choose a new campaign scoring directory")
    campaign = read_json(directory / "campaign.json")
    corpus = ROOT / "phase2_corpus/retrieval_documents.jsonl"
    labels_path = ROOT / "phase2_ground_truth_vault/pilot_manifest.json"
    labels_doc = read_json(labels_path)  # post-execution only
    labels = {pair_key(c["target_pair"]): c for c in labels_doc["cases"]}
    require(set(runs) == set(campaign["groups"]) == set(BLOCKS), "Supply both predeclared groups, including incomplete runs")
    require(file_hash(corpus) == campaign["corpus_sha256"], "Campaign corpus changed")
    require(file_hash(ROOT / "phase2_experiment/pilot_target_pairs.json") == campaign["source_pairs_sha256"], "Campaign source pairs changed")
    signatures, group_inputs, all_pairs = [], {}, set()
    for name, run in runs.items():
        path = directory / campaign["groups"][name]["pairs_file"]
        require(file_hash(path) == campaign["groups"][name]["pairs_sha256"], "Campaign pair file changed")
        keys = {pair_key(p) for p in read_json(path)["pairs"]}
        require(not all_pairs & keys, "Campaign groups overlap")
        all_pairs |= keys
        config = read_json(Path(run) / "config.json")
        # Commits/dirty status may change between windows; actual code must not.
        signatures.append({k: config[k] for k in ("model", "top_k", "prompt_sha256", "policy")}
                          | {"code": config["source"]["implementation_hashes"],
                             "dependencies": config["source"]["repository_dependency_hashes"],
                             "environment": config["source"]["environment"]})
        group_inputs[name] = (path, keys)
    require(all_pairs == set(labels), "Campaign does not cover exactly the full pilot")
    require(all(s == signatures[0] for s in signatures), "Settings/code/environment differ between quota windows")
    output_dir.mkdir(parents=True, exist_ok=False)
    reports, completed, review_rows = {}, {}, []
    for name, run in runs.items():
        path, keys = group_inputs[name]
        subset_labels = output_dir / (name + "_labels_PRIVATE.json")
        write_json(subset_labels, {"cases": [{k: c[k] for k in ("case_id", "target_pair", "label", "condition")}
                                             for c in labels_doc["cases"] if pair_key(c["target_pair"]) in keys]})
        reports[name] = score_run(run_dir=run, labels_path=subset_labels, pairs_path=path, corpus_path=corpus,
                                  provenance_path=ROOT / "phase2_corpus/internal_provenance.jsonl",
                                  output_dir=output_dir / name)
        for row in read_jsonl(Path(run) / "results.jsonl"):
            if row["execution_status"] == "completed":
                key = (row["arm"], pair_key(row["target_pair"]))
                require(key not in completed, "Duplicate campaign execution")
                completed[key] = row["output"]
        with (output_dir / name / "review_template.csv").open(encoding="utf-8", newline="") as handle:
            review_rows.extend(csv.DictReader(handle))
    by_arm = {a: {p: out for (arm, p), out in completed.items() if arm == a} for a in ARMS}
    paired = set(by_arm[ARMS[0]]) & set(by_arm[ARMS[1]])
    summary = {"kind": "two_predeclared_quota_windows", "groups": {n: {"run_id": r["run_id"], "run_status": r["run_status"],
                                                                                  "report_sha256": file_hash(output_dir / n / "report.json")}
                                                                      for n, r in reports.items()},
               "complete_experiment_run": all(r["complete_experiment_run"] for r in reports.values()),
               "expected_pairs": len(labels), "paired_completed_count": len(paired),
               "arms": {a: {"coverage": {k: sum(r["arms"][a]["coverage"][k] for r in reports.values())
                                           for k in ("expected", "completed", "failed", "missing_result_records")},
                              "binary_metrics_completed_only": metrics(by_arm[a], labels),
                              "per_condition": {c: metrics({p: o for p, o in by_arm[a].items() if labels[p]["condition"] == c}, labels)
                                                for c in sorted({x["condition"] for x in labels.values()})}}
                        for a in ARMS},
               "paired_completed_binary_metrics": {a: metrics({p: o for p, o in by_arm[a].items() if p in paired}, labels) for a in ARMS},
               "manual_review": manual_review(review_path, completed),
               "campaign_sha256": file_hash(directory / "campaign.json"), "labels_sha256": file_hash(labels_path),
               "note": "Both groups and quota windows must be disclosed. Mock/smoke runs are not scientific results. No significance or independent-review claim is inferred."}
    if review_path:
        summary["manual_review_sha256"] = file_hash(review_path)
    write_json(output_dir / "campaign_report.json", summary)
    with (output_dir / "review_template.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(review_rows)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--directory", type=Path, required=True)
    p = sub.add_parser("score")
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--group-1-run", type=Path, required=True)
    p.add_argument("--group-2-run", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--manual-review", type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.directory) if args.action == "prepare" else score_campaign(
            directory=args.directory, runs={"group_1": args.group_1_run, "group_2": args.group_2_run},
            output_dir=args.output_dir, review_path=args.manual_review)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(2, f"Checkpoint rejected: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
