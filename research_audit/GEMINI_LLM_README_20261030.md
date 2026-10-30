<!-- Historical Gemini workflow snapshot before the Groq switch; current instructions are in PILOT_RUNBOOK.md. -->

# LLM integration and bounded experiment runner

Workstream: Member 1. The existing deterministic systems, verifier rules, datasets
and historical result files are preserved. This package adds the two LLM control
flows and writes its own run artifacts.

**October 29 integration update:** Member 2 and Member 3 are merged locally into
this branch, pending review/commit. Combined suite: **206 passed, 4 skipped**;
the real pilot corpus -> runner -> scorer boundary passes offline. Free-tier-only
API access is being configured; live behavior remains unverified. Follow the
[current pilot runbook](../PILOT_RUNBOOK.md) for setup, smoke, experiment and scoring.

## Start here: offline demonstration

From the repository root, using Python 3.10 or newer:

```powershell
python -B -m unittest discover -s phase3_llm/tests -p test_pipeline.py -v
python -B -m phase3_llm.runner
```

The default run needs only Python's standard library. It makes **no network
requests**, reads no benchmark labels, and uses four fictional pairs with scripted
model/verifier responses. Expected summary: **8 completed case-arm executions,
0 failures, 12 scripted model calls**. This demonstrates software behavior;
it is **not an LLM experiment, a quality benchmark, or evidence of verification gains**.

The command prints the unique output folder under `experiment_runs/`. To choose a
review location, pass `--output-dir experiment_runs/my_mock_review`; it must not
already exist. All generated run folders are ignored by Git so they can be reviewed
before selecting artifacts for publication. No commit or push is needed to run it.

## What each file does

| File | Responsibility |
| --- | --- |
| `contracts.py` | Strict public pair, evidence, decision, and tool-call validation |
| `prompts.py` | Common evidence rules, stage instructions and JSON schemas |
| `model.py` | Model request/reply protocol and scripted offline model |
| `fixtures.py` | Four fictional examples and a scripted fixture verifier |
| `gemini.py` | Standard-library Gemini Interactions REST adapter |
| `services.py` | Lazy adapters to the existing retriever and verifier; unlabelled pair loading |
| `systems.py` | Baseline and single-verification control flows, call budget |
| `runner.py` | CLI, shared retrieval, logging, manifests and compatible exports |
| `tests/test_pipeline.py` | Offline behavior, failures, isolation and Gemini payload checks |
| `tests/test_repository_integration.py` | Actual pilot corpus, runner and scorer boundary; existing requirements needed |

## Comparison and declared policies

1. The controller retrieves **once per pair** and passes the same ordered evidence
   to both arms. It uses the existing lexical retriever for corpus runs.
2. Arm A asks the model for a structured final decision, with no tools.
3. Arm B requires the model to supply arguments for the single allowed verifier,
   validates them, executes it, then asks the model for a final decision. There is
   no second retrieval or second tool call. This is bounded, required tool use,
   not a measurement of autonomous search or tool selection.
4. Both arms share the same task/evidence instructions. A phone call alone does
   not establish joint burglary; lack of evidence normally means Insufficient Evidence.
5. The final model answer is **not overwritten by the verifier**. Agreement is
   observed/logged, not enforced. `support_gate: observe_only` is recorded in the
   manifest; unsupported model assertions must be assessed by the scorer/reviewer.
6. Missing retrieval produces an explicit controller Insufficient Evidence record
   in both arms, with `decision_origin: controller_empty_retrieval`, zero model calls,
   and a trace event. Report these separately from actual model responses.
7. Parse/API/tool errors are failed executions, never fabricated evidence decisions.
   Failed attempts count toward the model-call limit. Automatic retries are disabled.
   Provider failures stop further requests; output validation failures remain case failures.
8. The baseline normally makes one model request and the verification arm two.
   This is an equal-initial-evidence comparison, not an equal-compute comparison.

## Run artifacts and scoring handoff

Each folder contains:

- `config.json`: mode, model settings, dataset metadata, source commit/dirty state,
  pending merge parent, implementation/dependency hashes, environment versions,
  prompt/schema hash, call budget and declared policies.
- `retrieval.jsonl`: the exact initial evidence shared by both arms, once per pair.
- `traces.jsonl`: normalized model requests/responses, raw provider bodies/responses,
  usage when supplied, tool acceptance/rejection/results and comparisons.
- `results.jsonl`: one envelope per attempted execution; completed records contain
  `output`, failed records contain an error and **no relationship decision**.
- `errors.jsonl`: failed executions, including their pair, arm, type and message.
- `manifest.json`: completion/failure/unattempted counts, attempted calls, artifact
  hashes and whether scoring exports are available. Also written on Ctrl+C.

Only when **every execution completes**, the runner writes
`system_a_rag_only_outputs.json` and `system_b_rag_verification_outputs.json`.
They preserve the existing `ArmRunResult` / `SystemCaseOutput` field layout for
Member 3's evaluator. Run metadata explicitly identifies `phase3_llm`, provider
and mode. These arm names do not imply that the historical heuristics were used.
Incomplete runs have no compatible exports, preventing accidental scoring of a
silently reduced sample. No scores are computed by this package.

Review secrets and provider content before explicitly adding selected run artifacts
to Git. Authentication headers and API keys are not logged. Do not submit mock
or fictional-fixture smoke outputs as scientific results.

## Gemini: optional live smoke test

The adapter uses the REST Interactions API directly, so it needs no SDK install.
It is implemented against official documentation and checked with fake HTTP
responses, but **has not been validated against a live account**.

Configure `GEMINI_API_KEY` in your local environment without pasting it into chat,
source code or a shell command submitted through the assistant. Confirm account
quota/budget before running the following explicitly live command:

```powershell
python -B -m phase3_llm.runner --provider gemini --mode smoke --allow-live --max-model-calls 12
```

This uses fictional evidence and the scripted fixture verifier. It exercises actual
model output/tool calls once access exists; it is an API smoke test, not a real
verifier evaluation. Smoke mode now defaults to one pair (three requests); use
`--smoke-pairs N` to expand it. That flag is forbidden for experiments. For a local
key file use `--api-key-file .gemini_api_key`; this exact root filename is ignored.
Default model is `gemini-3.8-flash`, thinking `medium`, output
limit 4096 tokens per request (including thinking), timeout 300 seconds, minimum
request spacing 35 seconds. These were increased after observed live latency on
October 30; model reasoning quality was not reduced. These can be overridden via `--help`. Account-specific
quotas can require slower spacing. Rate-limit failures are logged with no retries.
Raise the output allowance before the frozen experiment if development smoke tests
show truncation; never silently reduce reasoning or switch model on failed cases.

Only the custom verifier tool is exposed. No search/code-execution built-ins are
enabled. The stateless flow preserves the provider's original steps/signatures and
call ID across the tool response; `store` is false. Provider usage remains in the
raw response trace. No hard dollar-budget guarantee is provided; the runner limits
requests and per-request output instead.

Official references checked October 28, 2026:

- [Function calling and stateless history](https://ai.google.dev/gemini-api/docs/function-calling)
- [Structured final output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Interactions REST reference](https://ai.google.dev/api/interactions-api)

## Connect teammates' audited corpus and verifier

Corpus integration needs the existing `requirements.txt` environment. It imports
the current `EvidenceRetriever` and `HypothesisVerifier` lazily. It does not load
ground-truth JSON files or internal provenance. Member 3 can repair the verifier
without changing this adapter if its documented signature remains stable.

Once the dataset/verifier handoffs and model smoke test are ready:

```powershell
python -B -m phase3_llm.runner --provider gemini --mode experiment --dataset corpus --corpus PATH_TO_AUDITED_JSONL --pairs PATH_TO_UNLABELLED_PAIRS_JSON --dataset-version PILOT_VERSION --allow-live --max-model-calls 40
```

Replace the uppercase placeholders with the approved paths/version. Pair input
uses the existing `{"pairs": [["OID#1", "OID#2"]], "total_pairs": 1}` format;
case manifests, labels, extra fields, duplicate pairs and mismatching counts are
rejected. Paths/version are explicit: the CLI does not assume current benchmark
data has been audited. The run does not itself certify dataset validity.

Member 3's native scorer consumes the JSONL run **after inference**, joining labels
by pair and writing reports into a separate destination; incomplete runs retain
explicit failure/coverage counts. See [scoring instructions](../phase2_experiment/SCORING.md).
Record the independent
evidence audit, failed-run coverage and verifier/model disagreements. Existing
evaluator defaults point at historical outputs; never invoke those defaults to
score a new run. There is no automatic resume or provider fallback in this version.

## Validation limits

- Offline tests and scripted demonstration can run now, with no external packages.
- The combined suite and repository-service bridge pass in `.venv`; raw source-data
  regeneration remains skipped because the upstream dataset is absent.
- Live authentication, a fictional baseline JSON response and a full tool round-trip
  succeeded on October 30 after two timeouts and an HTTP 503. The first real pilot
  block is being run separately; consult its manifest and the runbook for current
  status. Smoke checks are not scientific pilot results.
- Groq GPT-OSS 120B remains the planned alternative; no Groq adapter is implemented.
