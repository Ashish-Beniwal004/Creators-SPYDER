"""Offline scoring boundary checks, with synthetic runner-shaped artifacts."""

import csv
import hashlib
import json

import pytest

from phase2_experiment.evaluator import compute_descriptive_metrics, evaluate_pilot_runs
from phase2_experiment.score_run import ARMS, REVIEW_FIELDS, file_hash, score_run


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def write_lines(path, data):
    path.write_text("".join(json.dumps(row) + "\n" for row in data), encoding="utf-8")


def freeze(run):
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["artifact_hashes"] = {p.name: file_hash(p) for p in run.iterdir() if p.name != "manifest.json"}
    write_json(run / "manifest.json", manifest)


@pytest.fixture
def bundle(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    pairs = [["OID#100", "OID#200"], ["OID#300", "OID#400"]]
    pairs_path, labels_path, corpus_path = [tmp_path / n for n in ("pairs.json", "labels.json", "corpus.jsonl")]
    write_json(pairs_path, {"total_pairs": 2, "pairs": pairs})
    write_json(labels_path, {"cases": [{"case_id": f"CASE_{i}", "target_pair": p, "label": 1 - i,
                                      "condition": "clean"} for i, p in enumerate(pairs)]})
    docs = [{"doc_id": f"DOC_IR_{i+1:08x}", "doc_type": "incident_report", "timestamp": "2020-03-01 12:00:00",
             "text_content": "CASE INC-2020-1234\nEntry Method: residential burglary\n"
                             f"Suspects/Persons of Interest: {p[0]}, {p[1]}\nCase cleared by arrest.", "metadata": {}}
            for i, p in enumerate(pairs)]
    write_lines(corpus_path, docs)
    config = {"implementation": "phase3_llm", "schema_version": "1.0", "mode": "experiment", "scientific_results": True,
              "model": {"provider": "offline_test_double"}, "top_k": 5,
              "dataset": {"corpus_sha256": file_hash(corpus_path), "pairs_sha256": file_hash(pairs_path)},
              "target_pairs_sha256": hashlib.sha256(json.dumps(pairs, sort_keys=True, allow_nan=False).encode()).hexdigest()}
    write_json(run / "config.json", config)
    retrieval, results, traces = [], [], []
    for i, p in enumerate(pairs):
        context = {"run_id": "run", "case_index": i, "target_pair": p}
        doc = docs[i]
        evidence = {k: doc[k] for k in ("doc_id", "doc_type", "text_content")}
        evidence["score"] = 0.5
        retrieval.append({**context, "query": " ".join(p), "evidence": [evidence]})
        for arm in ARMS:
            output = {"case_index": i, "arm": arm, "entity_a": p[0], "entity_b": p[1], "target_pair": p,
                      "decision": "Supported" if i == 0 else "Insufficient Evidence", "is_supported": i == 0,
                      "rationale": "Test fixture only", "retrieval_query": " ".join(p),
                      "retrieved_doc_ids": [doc["doc_id"]], "retrieval_scores": {doc["doc_id"]: 0.5},
                      "cited_doc_ids": [doc["doc_id"]], "verification_data": None, "execution_timestamp": "test"}
            results.append({**context, "arm": arm, "execution_status": "completed", "model_calls": 1, "output": output})
            traces.append({**context, "arm": arm, "event": "model_request", "data": {}})
    write_lines(run / "results.jsonl", results)
    write_lines(run / "retrieval.jsonl", retrieval)
    write_lines(run / "traces.jsonl", traces)
    write_lines(run / "errors.jsonl", [])
    write_json(run / "manifest.json", {"run_id": "run", "status": "completed", "parameters": config,
                                      "expected_executions": 4, "completed_executions": 4, "failed_executions": 0,
                                      "unattempted_executions": 0, "attempted_model_calls": 4})
    freeze(run)
    return dict(run_dir=run, labels_path=labels_path, pairs_path=pairs_path, corpus_path=corpus_path,
                output_dir=tmp_path / "scores")


def mutate_record(bundle, change):
    path = bundle["run_dir"] / "results.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    change(rows)
    write_lines(path, rows)
    freeze(bundle["run_dir"])


def test_complete_run_and_manual_review_are_separate(bundle):
    report = score_run(**bundle)
    assert report["paired_completed_count"] == 2
    assert report["arms"][ARMS[0]]["binary_metrics_completed_only"]["accuracy"] == 1
    assert report["manual_review"][ARMS[0]]["manual_unsupported_assertion_rate"] is None
    template = bundle["output_dir"] / "review_template.csv"
    with template.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0].update(support_assessment="unsupported", reference_status="Insufficient Evidence", reviewer="Human test reviewer")
    reviewed = bundle["output_dir"].parent / "reviewed.csv"
    with reviewed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    bundle["output_dir"] = bundle["output_dir"].parent / "reviewed_scores"
    report = score_run(**bundle, manual_review_path=reviewed)
    assert report["manual_review"][ARMS[0]]["manual_unsupported_assertion_rate"] == 1
    assert report["arms"][ARMS[0]]["verifier_consistency_on_positive_citations"]["rate"] == 1
    assert report["manual_review"][ARMS[0]]["three_way_accuracy"] == 0


def test_failed_execution_is_not_a_negative_decision(bundle):
    def fail(rows):
        row = rows[-1]
        row.pop("output")
        row.update(execution_status="failed", error_type="TimeoutError", error="fixture timeout")
    mutate_record(bundle, fail)
    run = bundle["run_dir"]
    rows = [json.loads(line) for line in (run / "results.jsonl").read_text().splitlines()]
    write_lines(run / "errors.jsonl", [rows[-1]])
    manifest = json.loads((run / "manifest.json").read_text())
    manifest.update(status="incomplete", completed_executions=3, failed_executions=1)
    write_json(run / "manifest.json", manifest)
    freeze(run)
    report = score_run(**bundle)
    assert report["paired_completed_count"] == 1
    assert report["arms"][ARMS[1]]["coverage"] == {"expected": 2, "completed": 1, "failed": 1, "missing_result_records": 0}
    assert report["arms"][ARMS[1]]["binary_metrics_completed_only"]["total_cases"] == 1
    assert not report["complete_experiment_run"]


@pytest.mark.parametrize("change", [
    lambda rows: rows.append(rows[0]),
    lambda rows: rows[0]["output"].update(is_supported=False),
    lambda rows: rows[0]["output"].update(cited_doc_ids=["DOC_IR_00000002"]),
    lambda rows: rows[0].update(target_pair=["OID#200", "OID#100"]),
    lambda rows: rows[0]["output"].update(retrieval_scores={}),
])
def test_rejects_inconsistent_results_before_creating_output(bundle, change):
    mutate_record(bundle, change)
    with pytest.raises(ValueError):
        score_run(**bundle)
    assert not bundle["output_dir"].exists()


def test_rejects_tampered_artifacts_and_wrong_cohort(bundle):
    (bundle["run_dir"] / "results.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        score_run(**bundle)


def test_rejects_wrong_labels(bundle):
    write_json(bundle["labels_path"], {"cases": []})
    with pytest.raises(ValueError, match="Labels must cover"):
        score_run(**bundle)


def test_interrupted_run_reports_missing_records_and_smoke_is_not_experiment(bundle):
    mutate_record(bundle, lambda rows: rows.pop())
    run = bundle["run_dir"]
    config = json.loads((run / "config.json").read_text())
    config.update(mode="smoke", scientific_results=False)
    write_json(run / "config.json", config)
    manifest = json.loads((run / "manifest.json").read_text())
    manifest.update(status="interrupted", parameters=config, completed_executions=3, unattempted_executions=1)
    write_json(run / "manifest.json", manifest)
    freeze(run)
    report = score_run(**bundle)
    assert report["arms"][ARMS[1]]["coverage"]["missing_result_records"] == 1
    assert report["paired_completed_count"] == 1
    assert not report["complete_experiment_run"]


def test_trace_usage_and_unaccepted_tool_calls_are_counted(bundle):
    run = bundle["run_dir"]
    path = run / "traces.jsonl"
    traces = [json.loads(line) for line in path.read_text().splitlines()]
    context = {k: traces[1][k] for k in ("run_id", "case_index", "target_pair", "arm")}
    traces.extend([
        {**context, "event": "model_response", "data": {"tool_calls": [{"name": "bad"}, {"name": "bad"}]}},
        {**context, "event": "provider_response", "data": {"raw": {"usage": {"total_input_tokens": 20, "total_output_tokens": 10}}}},
    ])
    write_lines(path, traces)
    freeze(run)
    report = score_run(**bundle)
    assert report["arms"][ARMS[1]]["calls"]["tool_call_validity_rate"] == 0
    assert report["arms"][ARMS[1]]["calls"]["unaccepted_tool_calls"] == 2
    assert report["arms"][ARMS[1]]["provider_reported_usage"]["total_output_tokens"] == 10


def test_scores_are_exclusive_and_frozen_run_is_unchanged(bundle):
    before = {p.name: file_hash(p) for p in bundle["run_dir"].iterdir()}
    score_run(**bundle)
    assert before == {p.name: file_hash(p) for p in bundle["run_dir"].iterdir()}
    with pytest.raises(ValueError, match="new scoring directory"):
        score_run(**bundle)


def test_withheld_evidence_is_not_a_retrieval_miss(bundle):
    path = bundle["run_dir"].parent / "provenance.jsonl"
    write_lines(path, [{"ground_truth_case_id": "CASE_0", "generation_rule": "RULE_CO_OFFENDER_INCIDENT_REPORT_PRIMARY", "document_id": "DOC_IR_00000001"},
                      {"ground_truth_case_id": "CASE_1", "generation_rule": "RULE_CO_OFFENDER_INCIDENT_REPORT_PRIMARY", "document_id": "DOC_IR_ffffffff"}])
    report = score_run(**bundle, provenance_path=path)
    assert report["retrieval"]["support_doc_recall"] == 1
    assert report["retrieval"]["withheld_support_documents"] == 1


def test_f1_zero_is_defined_when_predictions_are_all_wrong():
    assert compute_descriptive_metrics([1, 0], [0, 1]).f1_score == 0
    assert compute_descriptive_metrics([1], [0]).f1_score == 0
    assert compute_descriptive_metrics([0], [0]).f1_score is None


def test_legacy_evaluator_does_not_write_by_default_and_refuses_overwrite(tmp_path):
    report = evaluate_pilot_runs()
    assert report.total_cases == 10
    destination = tmp_path / "report.json"
    destination.write_text("keep")
    with pytest.raises(FileExistsError):
        evaluate_pilot_runs(report_output_file=str(destination))
    assert destination.read_text() == "keep"
