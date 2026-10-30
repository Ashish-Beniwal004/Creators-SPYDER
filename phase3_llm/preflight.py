"""Offline Groq request-size planning. No key read and no network requests."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from .contracts import ToolCall
from .groq import GroqModel
from .model import ModelReply, ModelRequest
from .runner import REPO_ROOT, file_hash, source_metadata
from .services import RepositoryServices, load_target_pairs


def inspect_pilot(corpus_path, pairs_path):
    pairs = load_target_pairs(Path(pairs_path))
    services = RepositoryServices(Path(corpus_path))
    # Construction/build_payload do not send requests or create a quota ledger.
    model = GroqModel("OFFLINE-PLANNING-NOT-A-CREDENTIAL")
    rows = []
    for index, pair in enumerate(pairs):
        case = services.retrieve(pair, 5)
        call = ToolCall("verify_hypothesis", {"entity_a": pair.ids[0], "entity_b": pair.ids[1],
                        "evidence_ids": [d.doc_id for d in case.evidence]}, "offline-planning-call")
        initial = model.build_payload(ModelRequest(case, "verify"))
        assistant = {"role": "assistant", "content": None, "tool_calls": [{"id": call.call_id, "type": "function",
                     "function": {"name": call.name, "arguments": json.dumps(call.arguments)}}]}
        previous = ModelReply(tool_calls=(call,), raw={"_request_messages": initial["messages"], "_assistant_message": assistant})
        stages = (ModelRequest(case, "baseline"), ModelRequest(case, "verify"),
                  ModelRequest(case, "final", previous, services.verify(call)))
        for req in stages:
            payload = model.build_payload(req)
            estimate = model.estimate_input_tokens(payload)
            rows.append({"pair_index": index, "stage": req.stage, "retrieved_documents": len(case.evidence),
                         "serialized_bytes": len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()),
                         "estimated_input_tokens": estimate, "max_generation_tokens": model.max_output_tokens,
                         "estimated_input_plus_max_generation": estimate + model.max_output_tokens})
    allowance = sum(r["estimated_input_plus_max_generation"] for r in rows)
    return {"kind": "offline_request_planning_not_provider_usage", "created_at": datetime.now(timezone.utc).isoformat(),
            "provider": "groq", "model": model.model, "source": source_metadata(),
            "corpus_sha256": file_hash(Path(corpus_path)), "pairs_sha256": file_hash(Path(pairs_path)),
            "pairs": len(pairs), "requests_for_both_arms": len(rows), "top_k": 5,
            "estimator": model.metadata["token_budget"]["input_estimator"],
            "estimated_input_tokens_total": sum(r["estimated_input_tokens"] for r in rows),
            "maximum_generation_allowance_total": len(rows) * model.max_output_tokens,
            "estimated_input_plus_max_generation_total": allowance,
            "maximum_single_request_estimate": max(r["estimated_input_plus_max_generation"] for r in rows),
            "all_requests_pass_estimated_8k_guard": all(r["estimated_input_plus_max_generation"] <= 8000 for r in rows),
            "worst_allowance_fits_default_170k_run_budget": allowance <= 170000,
            "important": "Estimates are not exact GPT-OSS tokenization. Tool planning cites all top-5 documents; actual model-selected arguments/content can differ. Reasoning usage must be measured in the smoke test. Local budgets may stop a run before all cases finish; no input truncation or reasoning reduction is automatic.",
            "rows": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=REPO_ROOT / "phase2_corpus/retrieval_documents.jsonl")
    parser.add_argument("--pairs", type=Path, default=REPO_ROOT / "phase2_experiment/pilot_target_pairs.json")
    parser.add_argument("--output", type=Path, required=True, help="New JSON planning report")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Output exists; choose a new report path")
    report = inspect_pilot(args.corpus, args.pairs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("source", "rows")}, indent=2))


if __name__ == "__main__":
    main()
