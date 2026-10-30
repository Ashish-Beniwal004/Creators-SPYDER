"""CLI and run artifacts. Default invocation is an offline mock, not an experiment."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib import metadata as package_metadata
import json
import os
from pathlib import Path
import platform
import subprocess
from uuid import uuid4

from .contracts import ARMS
from .fixtures import FixtureServices, demo_cases, demo_model
from .model import ProviderError
from .prompts import COMMON_INSTRUCTIONS, DECISION_SCHEMA, PROMPT_VERSION, STAGE_INSTRUCTIONS, VERIFIER_TOOL
from .services import RepositoryServices, load_target_pairs
from .systems import CallBudget, CallBudgetExceeded, execute_arm, utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_metadata() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                                  check=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
    def installed_version(name):
        try:
            return package_metadata.version(name)
        except package_metadata.PackageNotFoundError:
            return None
    dependencies = ("phase2_retrieval", "phase2_verification", "phase2_ground_truth_vault", "phase2_experiment")
    return {"commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "merge_parent": git("rev-parse", "--verify", "MERGE_HEAD"),
            "working_tree_status": git("status", "--porcelain"),
            "implementation_hashes": {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
            "repository_dependency_hashes": {
                p.relative_to(REPO_ROOT).as_posix(): file_hash(p)
                for folder in dependencies for p in sorted((REPO_ROOT / folder).glob("*.py"))},
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "packages": {name: installed_version(name) for name in ("pydantic", "scikit-learn", "numpy", "scipy")}}}


def _write_json(path: Path, value):
    # Exclusive create prevents accidental replacement, even inside a new run directory.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def run_experiment(*, pairs, services, model, output_dir: Path, mode: str = "mock",
                   top_k: int = 5, max_model_calls: int = 40, dataset_metadata: dict | None = None,
                   arms=ARMS) -> dict:
    if mode not in {"mock", "smoke", "experiment"}:
        raise ValueError("Invalid run mode")
    if (model.metadata["provider"] == "mock") != (mode == "mock"):
        raise ValueError("Mock providers must be labeled mock; real providers must not be labeled mock")
    arms = tuple(arms)
    if arms not in (ARMS, (ARMS[0],), (ARMS[1],)) or (arms != ARMS and mode != "smoke"):
        raise ValueError("Single-arm runs are allowed only for API smoke tests; experiments require both arms")
    if not pairs or len({p.ids for p in pairs}) != len(pairs):
        raise ValueError("A nonempty list of unique target pairs is required")
    if type(top_k) is not int or not 1 <= top_k <= 50:
        raise ValueError("top_k must be between 1 and 50")
    output_dir = Path(output_dir).resolve()
    protected = REPO_ROOT / "phase2_experiment" / "outputs"
    if output_dir == protected or protected in output_dir.parents:
        raise ValueError("Historical experiment outputs are protected; choose a new run destination")
    budget = CallBudget(max_model_calls)
    metadata = {"schema_version": "1.0", "implementation": "phase3_llm", "mode": mode, "arms": list(arms),
                "scientific_results": mode == "experiment", "model": model.metadata,
                "dataset": dataset_metadata or {}, "top_k": top_k, "max_model_calls": max_model_calls,
                "prompt_version": PROMPT_VERSION,
                "prompt_sha256": digest([COMMON_INSTRUCTIONS, STAGE_INSTRUCTIONS, DECISION_SCHEMA, VERIFIER_TOOL]),
                "target_pairs_sha256": digest([list(p.ids) for p in pairs]), "source": source_metadata(),
                "policy": {"retrieval": "shared_initial_only", "verification_calls_per_case": 1,
                           "verification_tool_choice": "required_single_allowed_tool",
                           "support_gate": "observe_only", "automatic_retries": 0,
                           "provider_failure": "stop_run"}}
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_json(output_dir / "config.json", metadata)
    run_id = output_dir.name
    manifest = {"run_id": run_id, "started_at": utc_now(), "status": "running", "parameters": metadata,
                "expected_executions": len(pairs) * len(arms), "completed_executions": 0,
                "failed_executions": 0, "attempted_model_calls": 0, "provider_requests_sent": 0, "exports_available": False}
    records = {arm: [] for arm in arms}
    artifacts = {name: (output_dir / f"{name}.jsonl").open("x", encoding="utf-8")
                 for name in ("retrieval", "traces", "results", "errors")}

    def append(name, value):
        artifacts[name].write(json.dumps(value, allow_nan=False) + "\n")
        artifacts[name].flush()

    try:
        stop = False
        for index, pair in enumerate(pairs):
            context = {"run_id": run_id, "case_index": index, "target_pair": list(pair.ids)}
            retrieval_error = None
            try:
                case = services.retrieve(pair, top_k)
                if case.pair.ids != pair.ids:
                    raise ValueError("Retriever changed the target pair")
                append("retrieval", {**context, "query": case.query, "evidence": [asdict(d) for d in case.evidence]})
            except Exception as exc:
                retrieval_error = exc
            for arm in arms:
                def emit(event, value):
                    if event == "provider_request":
                        manifest["provider_requests_sent"] += 1
                    append("traces", {**context, "arm": arm, "timestamp": utc_now(), "event": event, "data": value})
                before = budget.used
                try:
                    if retrieval_error is not None:
                        raise retrieval_error
                    output, diagnostics = execute_arm(arm, case, index, model, services.verify, emit, budget)
                    records[arm].append(output)
                    manifest["completed_executions"] += 1
                    append("results", {**context, "arm": arm, "execution_status": "completed",
                                       "model_calls": budget.used - before, "diagnostics": diagnostics, "output": output})
                except Exception as exc:
                    failed = {**context, "arm": arm, "execution_status": "failed", "model_calls": budget.used - before,
                              "error_type": type(exc).__name__, "error": str(exc), "timestamp": utc_now()}
                    append("errors", failed)
                    append("results", failed)
                    emit("execution_failed", {"error_type": type(exc).__name__, "error": str(exc)})
                    manifest["failed_executions"] += 1
                    if isinstance(exc, (CallBudgetExceeded, ProviderError)):
                        manifest["stop_reason"] = type(exc).__name__
                        stop = True
                        break
            if stop:
                break
        manifest["status"] = "completed" if manifest["completed_executions"] == len(pairs) * len(arms) else "incomplete"
        if manifest["status"] == "completed":
            for arm, outputs in records.items():
                _write_json(output_dir / f"{arm}_outputs.json", {
                    "run_id": run_id, "arm": arm, "execution_timestamp": utc_now(),
                    "parameters": metadata, "total_cases": len(outputs), "results": outputs,
                })
            manifest["exports_available"] = True
    except BaseException:
        manifest["status"] = "interrupted"
        raise
    finally:
        for handle in artifacts.values():
            handle.close()
        manifest["finished_at"] = utc_now()
        manifest["attempted_model_calls"] = budget.used
        manifest["unattempted_executions"] = len(pairs) * len(arms) - manifest["completed_executions"] - manifest["failed_executions"]
        manifest["artifact_hashes"] = {p.name: file_hash(p) for p in sorted(output_dir.iterdir()) if p.is_file()}
        _write_json(output_dir / "manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="SPYDER LLM runner; default is offline scripted fixtures")
    parser.add_argument("--provider", choices=("mock", "groq", "gemini"), default="mock")
    parser.add_argument("--api-key-file", type=Path, help="Local key file; live defaults to .groq_api_key/.gemini_api_key when its environment variable is unset")
    parser.add_argument("--mode", choices=("mock", "smoke", "experiment"), default="mock")
    parser.add_argument("--dataset", choices=("fixtures", "corpus"), default="fixtures")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--pairs", type=Path)
    parser.add_argument("--dataset-version")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-model-calls", type=int, default=30)
    parser.add_argument("--smoke-pairs", type=int, help="Smoke mode only: first N pairs (default: 1); never truncates experiments")
    parser.add_argument("--smoke-arm", choices=ARMS, help="Smoke mode only: validate one arm without repeating the other")
    parser.add_argument("--allow-live", action="store_true", help="Explicitly permit potentially billable API requests")
    parser.add_argument("--model", help="Defaults to openai/gpt-oss-120b for Groq; gemini-3.8-flash for Gemini")
    parser.add_argument("--thinking", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--request-interval", type=float, help="Defaults: Groq 90s (minimum 65s); Gemini 35s")
    parser.add_argument("--max-total-tokens", type=int, default=170000, help="Groq per-run token budget; shared workspace ledger also caps rolling 24h usage at 180000")
    args = parser.parse_args(argv)
    if args.api_key_file is not None and args.provider == "mock":
        parser.error("--api-key-file applies only to live providers")
    if args.smoke_pairs is not None and (args.mode != "smoke" or args.smoke_pairs < 1):
        parser.error("--smoke-pairs must be positive and is allowed only with --mode smoke")
    if args.smoke_arm is not None and args.mode != "smoke":
        parser.error("--smoke-arm is allowed only with --mode smoke")
    if args.provider == "mock" and (args.mode != "mock" or args.dataset != "fixtures" or args.allow_live):
        parser.error("Mock mode uses fictional fixtures only and cannot be an experiment or allow live requests")
    if args.provider != "mock" and (not args.allow_live or args.mode == "mock"):
        parser.error("Live providers require --allow-live and --mode smoke or experiment")
    if args.mode == "experiment" and args.dataset != "corpus":
        parser.error("Reported experiments require the approved corpus, not scripted fixtures")
    if args.dataset == "corpus" and not all((args.corpus, args.pairs, args.dataset_version)):
        parser.error("Corpus runs require --corpus, --pairs and --dataset-version")
    if args.dataset == "fixtures" and any((args.corpus, args.pairs, args.dataset_version)):
        parser.error("Do not combine corpus paths/version with fictional fixtures")
    output = args.output_dir or REPO_ROOT / "experiment_runs" / (
        f"{args.mode}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}")
    try:
        if args.provider == "mock":
            model = demo_model()
        else:
            env_name = "GROQ_API_KEY" if args.provider == "groq" else "GEMINI_API_KEY"
            api_key = os.environ.get(env_name, "")
            key_path = args.api_key_file
            if key_path is None and not api_key:
                key_path = REPO_ROOT / (".groq_api_key" if args.provider == "groq" else ".gemini_api_key")
            if key_path is not None:
                api_key = key_path.read_text(encoding="utf-8-sig").strip()
            options = {"thinking": args.thinking, "max_output_tokens": args.max_output_tokens, "timeout": args.timeout}
            if args.provider == "groq":
                from .groq import GroqModel
                model = GroqModel(api_key, model=args.model or "openai/gpt-oss-120b",
                                  request_interval=90 if args.request_interval is None else args.request_interval,
                                  max_total_tokens=args.max_total_tokens, **options)
            else:
                from .gemini import GeminiModel
                model = GeminiModel(api_key, model=args.model or "gemini-3.8-flash",
                                    request_interval=35 if args.request_interval is None else args.request_interval, **options)
        if args.dataset == "fixtures":
            services = FixtureServices()
            pairs = [case.pair for case in demo_cases()]
            dataset_meta = {"name": "fictional-scripted-smoke-v1", "verifier": "scripted_fixture_only"}
        else:
            pairs = load_target_pairs(args.pairs)
            dataset_meta = {"version": args.dataset_version, "corpus_path": str(args.corpus.resolve()),
                            "corpus_sha256": file_hash(args.corpus), "pairs_path": str(args.pairs.resolve()),
                            "pairs_sha256": file_hash(args.pairs), "verifier": "repository_HypothesisVerifier"}
            services = RepositoryServices(args.corpus)
        if args.mode == "smoke":
            pairs = pairs[:args.smoke_pairs or 1]
        manifest = run_experiment(pairs=pairs, services=services, model=model, output_dir=output,
                                  mode=args.mode, top_k=args.top_k, max_model_calls=args.max_model_calls,
                                  dataset_metadata=dataset_meta, arms=(args.smoke_arm,) if args.smoke_arm else ARMS)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"Run could not start: {exc}\n")
    print(json.dumps({"output_dir": str(output.resolve()), "mode": args.mode,
                      "status": manifest["status"], "completed": manifest["completed_executions"],
                      "failed": manifest["failed_executions"], "model_calls": manifest["attempted_model_calls"],
                      "provider_requests_sent": manifest["provider_requests_sent"]}, indent=2))
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
