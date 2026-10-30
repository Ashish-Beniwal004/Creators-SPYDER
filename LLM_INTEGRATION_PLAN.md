# Member 1: LLM Integration and Experiment Runner

**October 30 provider change:** The user selected **Groq / openai/gpt-oss-120b**
for a fresh ten-pair comparison after Gemini latency/HTTP 503 interrupted its
pilot. The Groq adapter, shared conservative token ledger and native scorer bridge
are implemented: **221 passed, 4 skipped**. Live smoke passed with three requests
and 2,199 tokens. The ten-pair pilot completed with 65-second spacing: **20
executions, zero failures, 30 requests, 42,591 tokens**. Both arms achieved
**90% binary accuracy and 0.8889 F1**, with no measured verification gain.
The copied saved-output bundle reproduces the scores. Final local commits and a
clean committed-source export are verified; independent human ratings are not
measured. Current results: [MID_SUBMISSION_PROGRESS.md](MID_SUBMISSION_PROGRESS.md).
The root `.groq_api_key` remains ignored. Use
[PILOT_RUNBOOK.md](PILOT_RUNBOOK.md). Earlier Gemini plans/results below are
historical and will not be pooled with the new model.

**October 29 status:** Member 3's committed changes (`d7ec222`, including Member 2)
are merged locally into `feat/llm-integration-runner`, with the merge left
uncommitted for review. Combined tests: **206 passed, 4 skipped**. The real pilot
corpus, runner, verifier and scorer pass the offline integration check. Live access
is not yet configured; the user requires **free tier only**. Current setup and
execution instructions are in [PILOT_RUNBOOK.md](PILOT_RUNBOOK.md). The original
October 28 planning snapshot below is retained as historical context.

**Date:** October 28, 2026 (IST)  
**Repository inspected:** `88d353d`, `release/curated-project-handoff`  
**Checkpoint:** October 30 night  
**Current access:** No model access is set up yet. The user prefers free or low-cost APIs, specifically mentioning GPT-OSS 120B and Gemini 3.8 Flash, with task quality prioritized. Candidate availability/pricing was checked against official documentation on October 28. Provider credentials and any paid spending ceiling remain pending. No model API request or package installation has been made.

**Implementation update (October 28):** Work has started on local branch `feat/llm-integration-runner`. The new [phase3_llm package](phase3_llm/README.md) implements the offline two-arm runner, public contracts, prompts, fictional fixtures, Gemini REST adapter, lazy repository-service adapters, traces and compatible output exports. The offline demonstration completes eight executions with twelve scripted model calls. Live Gemini behavior and the real repository-service integration remain unverified until access/dependencies and teammate handoffs are available. Historical data/results are unchanged; nothing has been committed or pushed by the assistant.

## 1. Can We Start Now?

**Yes. Start the provider-independent implementation using fictional evidence and a scripted model response.** We do not need to wait for the full dataset or verifier repairs to build contracts, prompts, output validation, the two control flows, logging and the runner.

Your teammate's four-page timeline assigns exactly this work to Member 1 on October 28: model adapter, common prompts, structured output contract and experiment logging, initially using mock evidence. October 29 is for the audited-corpus and tested-verifier handoffs. That schedule supports parallel work rather than waiting for all other members to finish.

There are three separate milestones:

1. **Offline development:** mocks and fixtures prove that our software executes and records both paths correctly. This can start immediately.
2. **Live model smoke test:** proves that the selected provider accepts our schema/tool definition. This needs model access and an agreed budget, but can use fictional evidence.
3. **Reported experiment:** runs the approved pilot through both arms. This needs Member 2's accepted corpus, Member 3's tested verifier and output/scoring agreement, plus the model setup.

Mock success is software progress, not an LLM result. Development runs and final checkpoint runs must be labeled separately.

## 2. Understand the Existing Project in Five Pieces

| Piece | What it does | Existing file/function | Our action |
| --- | --- | --- | --- |
| Target pairs | Lists two anonymized IDs to investigate | `phase2_experiment/pilot_target_pairs.json` | Load pair IDs only; no labels or difficulty fields |
| Evidence search | Finds text relevant to those IDs | `phase2_retrieval/retriever.py`: `search_evidence` | Reuse rather than replace |
| Verification | Checks whether supplied evidence establishes shared solved burglary | `phase2_verification/verifier.py`: `verify_hypothesis` | Call through a narrow adapter; Member 3 owns rule changes |
| Current systems | Make decisions using Python heuristics/rules | `phase2_experiment/system_a.py`, `system_b.py` | Preserve as historical baselines; add LLM implementations separately |
| Runner/evaluator | Executes cases, then joins predictions to hidden labels for scoring | `phase2_experiment/runner.py`, `evaluator.py` | Add a safe LLM runner; Member 3 owns scoring changes |

The target is narrow: whether the two entities share at least one documented solved burglary in the January-June 2020 evaluation window. Merely calling each other is not evidence of that relationship. Lack of evidence is not proof of `Unsupported`; it normally means `Insufficient Evidence`.

You do not need to understand every generator or verifier regex before implementing our part. First understand the two public functions and the result contract.

## 3. What Can Start and What Must Wait

| Task | Start now? | Real dependency |
| --- | --- | --- |
| Define input/output records and failure records | Yes | Agree the proposed contract with Member 3 before integration |
| Draft common instructions and baseline/verifier prompts | Yes | Final evidence rules agreed before freezing experiments |
| Implement a scripted mock model and verifier | Yes | No network, credentials or third-party packages required for a small offline harness |
| Validate citations, tool names and arguments | Yes | Existing evidence-ID and verifier conventions are already visible |
| Implement run folders, manifests and per-case traces | Yes | No teammate handoff needed |
| Wire existing retrieval and verification adapters | Yes, against current signatures | Runtime dependencies are absent locally; Member 4 handles environment setup |
| Make a live fictional-example API call | Later | Working account/model access, local credentials and approved spending limit |
| Run the reported 10-case pilot | Later | Audited corpus/version from Member 2; tested verifier and scorer contract from Member 3; model setup |
| Produce scored scientific results | Later | Completed live outputs; Member 3 joins hidden labels after inference |

Do not wait for regeneration of the 200-case corpus, a new development corpus, financial records, optional re-retrieval or the final report. None is required for the first offline milestone.

## 4. Recommended Implementation Shape

Add one small package, provisionally `phase3_llm/`, containing our implementation and its tests. Keep the existing deterministic entry points and frozen outputs unchanged. Exact file names are implementation choices; the responsibilities below are the important boundary.

| Proposed file | Responsibility |
| --- | --- |
| `contracts.py` | Public request, final decision, tool call and execution/failure records |
| `model.py` | Small model interface and scripted mock; the Gemini REST adapter is in `gemini.py` |
| `prompts.py` | Common task/evidence rules, baseline instructions, tool definition and final-response instructions |
| `systems.py` | Baseline and verification control flows |
| `runner.py` | CLI/configuration, shared initial retrieval, execution, traces and manifest |
| `tests/` | Offline validation and integration checks using fictional fixtures |
| `README.md` | Setup, dry run, live smoke test and reported-run instructions |

Do not build a general provider framework. One interface, one mock and one live provider are enough. The implemented Gemini adapter uses the documented REST API through Python's standard library, so no SDK dependency is needed. Coordinate the existing repository runtime dependencies with Member 4. Offline imports remain independent of those dependencies.

Existing experiment models constrain arm names and forbid extra fields. Preserve their compatible final-decision shape for Member 3, and keep richer traces/usage/errors in separate records. Do not add provider metadata into a strict legacy model without agreeing the change. A compatibility export should identify the implementation as LLM-based in its run metadata and preserve pair alignment.

## 5. The Two Experimental Arms

### Shared preparation

For each target pair, run the initial retrieval once and give both arms the same saved evidence texts, order, IDs and scores. Default to the existing `top_k = 5`, subject to the team's freeze. Both arms use the same model version, common evidence rules, generation settings and final schema.

### Arm A: LLM RAG-only

`target pair -> shared retrieved evidence -> model -> validated final decision`

The model receives the actual task and evidence-sufficiency rules, not instructions to guess aggressively. It can return `Insufficient Evidence`. It has no verifier access.

### Arm B: LLM with explicit verification

`same pair/evidence -> model hypothesis and verifier call -> validate arguments -> execute verifier -> model final decision -> validate output`

The application executes Python tools; a model-generated function name is not executed as arbitrary code. For the checkpoint, expose only `verify_hypothesis` at this stage. Initial search is controller-driven and identical across arms. Document that bounded design; do not claim autonomous search or broad tool selection.

Allow at most one verification call and no second retrieval for the checkpoint. Do not accept a tool call that changes the target pair or cites a document outside the shared retrieved set. Record attempted invalid calls and the reason for rejection.

Save the model's final response even if it disagrees with the verifier. If a support gate is enforced, declare the policy in advance and save both the raw response and the gate outcome. Do not silently replace the model answer with the verifier result, or tune the policy after seeing evaluation scores.

The verification arm normally requires two model requests while the baseline requires one. This is a bounded verification intervention, not a matched-compute comparison. Report actual model calls, latency and usage. A compute-matched self-review baseline can wait until the final project if justified.

## 6. Contracts to Share With Teammates

### Member 2: dataset handoff

Ask for the audited searchable JSONL path, an unlabelled pair-list path, corpus version/hash, and a short audit note. Condition counts and labels belong in reporting/evaluation assets, not in the request passed to the model.

We accept existing searchable fields: `doc_id`, `doc_type`, `text_content` and retrieval `score`. Keep timestamps and approved operational metadata available to the verifier through the corpus; no hidden provenance is required during inference.

### Member 3: verifier handoff

Current interface:

```python
verify_hypothesis(
    entity_a: str,
    entity_b: str,
    evidence_ids: list[str],
    verifier=None,
    corpus_path=None,
)
```

Expected response fields: `status`, `evidence_class`, `cited_evidence_ids`, `rationale`, and `findings`. Retain the three existing decision labels. Confirm exception behavior for invalid arguments and whether this signature will change. Our mock uses the same contract until their implementation is ready.

### Member 3: scoring handoff

At minimum, supply a run identifier, implementation/arm identifier, pair, decision, rationale, retrieved IDs/scores, cited IDs and verification data where applicable. Keep pair order canonical and derive `is_supported` from `decision` rather than accepting contradictory flags.

Agree a separate execution state such as `completed`/`failed` with error details. API, parsing and tool failures must not be converted into `Insufficient Evidence`. The scorer must report attempted/completed/failed counts and state its denominator.

### Member 4: setup handoff

Ask for a reproducible Python environment with the existing requirements, actual test/skip results and the agreed provider SDK. Share the exact commands we used, model identifier, nonsecret configuration and output schema. Credentials stay local; never put them in manifests or traces.

These are handoff requests the user can share; no teammate messages have been sent by the assistant.

## 7. Model Access: Resolve Alongside Offline Development

No access exists yet, so this is the main dependency for live experiments, not a reason to postpone software development.

**Recommendation:** begin with **Gemini 3.8 Flash** if the account's free quota is usable. Keep **GPT-OSS 120B on Groq** as the alternative if access, quota or the development checks make it more practical. Both are serious candidates; no SPYDER-specific quality comparison has been run, so do not claim either is better from price or parameter count alone. These options replace the earlier GPT-5.4 Mini suggestion in this plan.

| Candidate | Exact API model ID | Access/cost evidence | Fit for this project |
| --- | --- | --- | --- |
| Gemini 3.8 Flash | `gemini-3.8-flash` | Published free tier; standard paid input/output rates of $0.75/$3.75 per million tokens through December 31, 2026 | Stable model; function calling, structured outputs and configurable thinking supported |
| GPT-OSS 120B on Groq | `openai/gpt-oss-120b` | Published free-plan limits; standard paid input/output rates of $0.15/$0.60 per million tokens | Hosted open-weight model; local function calling and structured-output support |

Sources: [Gemini model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Groq model specification](https://console.groq.com/docs/model/openai/gpt-oss-120b), [Groq tool use](https://console.groq.com/docs/tool-use/overview), [Groq structured outputs](https://console.groq.com/docs/structured-outputs). Prices are documentation checks, not a verified account quote or guaranteed access.

Free access is quota-limited. Check the actual account's limits before batch execution, use sequential requests with bounded backoff, and retain rate-limit failures. [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Groq rate limits](https://console.groq.com/docs/rate-limits).

### Preserve quality without expanding the project

1. Validate the chosen model on a fixed small set of fictional/development examples covering direct support, alias resolution, CDR-only insufficiency and independent activity. Do not use the frozen full-test scores for model selection.
2. Check valid final-output structure, legitimate citations, correct verifier arguments and useful final evidence judgments. Fix software/tool integration errors before attributing failures to model quality.
3. Use a documented reasoning configuration consistently across arms. For Gemini, start with `medium` thinking, not an unsupported `minimal` setting. Do not impose a tiny output limit merely to save cost; log truncation and usage. [Gemini thinking guidance](https://ai.google.dev/gemini-api/docs/latest-model).
4. Freeze the model/provider and all settings before the reported run. Never silently switch providers for individual failed cases. A provider switch creates a separate comparison and requires both arms to be rerun.
5. Build one live adapter first. The Gemini REST adapter is now implemented but not live-tested. Add Groq only if needed; two complete provider integrations are not a checkpoint requirement. Keep the mock/provider boundary small enough to permit that change.

### Setup and cost control

Obtain a key through the chosen provider's console and configure it locally, for example `GEMINI_API_KEY` or `GROQ_API_KEY`. Never paste keys into chat or commit them. Use the provider's supported SDK/API for tool calls; disable built-in web search, code execution and other tools so the experiment only uses our supplied evidence and verifier.

Before paid calls, confirm the user's spending ceiling and account access. Estimate requests/tokens after formatting actual evidence, include retries and billable thinking/output, and bound output/retries. For illustration only, **100,000 input tokens plus 20,000 billed output tokens** would cost approximately **$0.15 on Gemini** or **$0.027 on Groq** at the rates above, excluding other charges. This is not an estimate of the entire experiment; actual token usage must be measured.

If free quota is exhausted, pause/back off or arrange an agreed small paid allowance; do not change to a smaller model mid-experiment. GPU provisioning and local 120B inference are not part of this deadline's plan. Mocks remain software tests, never scientific results.

## 8. Runner and Logging Requirements

Create a new folder per run, for example:

```text
experiment_runs/<run_id>/
  manifest.json
  retrieval.jsonl
  traces.jsonl
  results.jsonl
  errors.jsonl
```

The directory is a proposed new destination; do not write to `phase2_experiment/outputs/` during development. Scoring output comes later from Member 3.

- Manifest: provider/model version, generation settings, prompt/schema version or hash, corpus/pair hashes, source commit and dirty-state information, mode (`mock`, `smoke`, `experiment`), timestamps and declared budgets.
- Retrieval: pair, query, evidence IDs/text/scores shared by both arms.
- Trace: visible requests/responses, tool-call arguments and result, validation/rejection events, attempt identifiers, duration and returned usage. Exclude credentials and transport authorization headers.
- Results: completed structured final decisions with pair/arm identifiers and trace references.
- Errors: failed attempts/executions with categories and reasons; no fabricated business decision.

Write records as each case completes so a later failure does not lose earlier work. Refuse accidental overwrite of an existing run. A resume feature is optional; if added, it must verify identical configuration/input hashes before skipping completed work.

## 9. Implementation Order and Acceptance Checks

| Step | Work | Acceptance check | Dependency |
| --- | --- | --- | --- |
| **1. Contract and fixtures** | Define public inputs, tool call, final response and failure record; add fictional evidence | Direct positive, resolved alias, independent activity and CDR-only fixtures have explicit expected behavior | None |
| **2. Offline two-arm harness** | Script model responses and a mock verifier; exercise both control flows | Both arms save valid outputs and traces; mock runs are visibly labeled | Step 1 |
| **3. Robust runner** | Unique run folders, shared retrieval input, validation and failure logging | Bad citations/wrong pair/unknown tools are rejected; failures are retained; old files unchanged | Step 2 |
| **4. Provider smoke test** | Add one chosen provider adapter and run a fictional example | Authentication, final-output schema and real tool round-trip work; usage recorded | Access, budget and SDK |
| **5. Real integration** | Connect approved pilot and Member 3's verifier | Smoke-test direct positive, alias positive, negative and missing evidence with real modules | Teammate handoffs and working environment |
| **6. Freeze and batch** | Freeze settings and run all 10 approved pairs in both arms | 20 primary executions accounted for, including failures; actual calls recorded | Step 5 |
| **7. Handoff** | Supply outputs and reproduction procedure | Member 3 can score; Member 4 can repeat setup/run procedure | Step 6 |

Meaningful offline tests cover: equal initial evidence, baseline never invoking verification, correct tool round-trip, malformed model output, wrong target pair, unretrieved/unknown evidence IDs, unexpected tools, execution error versus evidence insufficiency, and refusal to overwrite a run. Use offline fixtures; tests make no paid calls.

## 10. Schedule for Our Part

- **October 28:** steps 1-3; aim for a runnable offline demonstration, while model access and environment are arranged. Share the proposed contract early; do not wait for all teammate work.
- **October 29, first session:** step 4, then step 5 when handoffs arrive. Fix interface problems before freezing settings.
- **October 29, later session:** step 6 on the audited 10 cases; send raw outputs to Member 3 immediately.
- **October 30:** resolve blockers, verify reproduction with Member 4, explain methods/limitations and integrate the submission commit. Aim to finish implementation before the final night.

The first concrete implementation milestone is **a no-key, no-network two-arm mock run that produces traceable files**. The user should be able to explain what evidence each arm saw, which tool was called, what it returned, and why a case completed or failed. That is how we begin understanding and owning this project without waiting for the rest of the team.
