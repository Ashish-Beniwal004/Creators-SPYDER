# Groq pilot runbook — October 30, 2026

Current provider: **Groq**, model **`openai/gpt-oss-120b`**, **free tier only**.
The runner never configures billing, falls back automatically, commits or pushes.
The completed experiment, exact settings and limitations are recorded in
[MID_SUBMISSION_PROGRESS.md](MID_SUBMISSION_PROGRESS.md). This runbook explains
how to reproduce the saved scores or deliberately start a new live run.

The adapter, token accounting and actual-corpus offline bridge are implemented:
**221 passed, 4 skipped, 30 subtests passed**. Skips require the absent upstream
source graph. **Live smoke passed:** `experiment_runs/groq_smoke_02` completed
both arms with three requests and 2,199 provider-reported tokens. The first smoke
was stopped by HTTP 403 (security-filter code 1010); setting an application
User-Agent resolved it. Its failed attempt remains recorded and conservatively
charged 8k in the local ledger. **The full ten-pair pilot completed** in
`experiment_runs/groq_pilot_01`: 20 executions, zero failures, 30 requests and
42,591 tokens. Both arms achieved 90% binary accuracy and 0.8889 F1; no observed
verification gain. Actual report: [MID_SUBMISSION_PROGRESS.md](MID_SUBMISSION_PROGRESS.md).
Selected reproducibility bundle: [research_audit/groq_checkpoint_20261030](research_audit/groq_checkpoint_20261030/README.md).
It was rescored successfully without API calls. Do not rerun existing destinations.
All fake-HTTP/scripted results are software checks, not LLM results.
Earlier Gemini outputs remain separate: one real pair completed before HTTP 503.
See [the archived Gemini runbook](research_audit/GEMINI_PILOT_RUNBOOK_20261030.md)
and [its actual validation record](research_audit/OCT30_LIVE_VALIDATION.json).

## 1. Key and quota

Put only the key into the root `.groq_api_key` file when ready. No quotes or variable
prefix; do not paste the key into chat. The exact filename is ignored by Git. Live
commands select it explicitly. `GROQ_API_KEY` is also supported; the Gemini key is
never used for Groq. Default invocation without live flags remains an offline mock.

Confirm a Free account with model access and current limits matching the expected
30 RPM / 1,000 RPD / 8k TPM / 200k TPD. Limits are organization-wide and other apps
consume them too. Account-specific limits take precedence. References checked
October 30: [limits](https://console.groq.com/docs/rate-limits),
[model](https://console.groq.com/docs/model/openai/gpt-oss-120b),
[tool calling](https://console.groq.com/docs/tool-use/local-tool-calling),
[structured outputs](https://console.groq.com/docs/structured-outputs).

## 2. Offline checks and token planning

```powershell
.venv/Scripts/python.exe -B -m pytest phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests phase2_ground_truth_vault/tests phase3_llm/tests -q -p no:cacheprovider
.venv/Scripts/python.exe -B -m phase3_llm.preflight --output experiment_runs/groq_preflight_REVIEW.json
```

Choose a new planning filename. Preflight uses the actual pilot and deterministic
tool results, reads no key or labels and makes no HTTP requests. Existing report:
`experiment_runs/groq_preflight_20261030_01.json`.

| Offline estimate | Value |
|---|---:|
| Requests for all ten pairs in both arms | 30 |
| Estimated input tokens across all requests | 67,427 |
| Generation allowance if every call reaches 4,096 | 122,880 |
| Combined estimated input + maximum generation | 190,307 |
| Largest single-request estimate including generation | 7,732 |

The estimator is serialized UTF-8 JSON bytes / 2, rounded up, plus 256 per request.
It is **not exact GPT-OSS tokenization**. All planned requests pass the estimated
8k guard, but the conservative full allowance exceeds the default 170k run budget
and leaves little daily room after smoke/retries. Actual model generation may use
much less. **Measure smoke usage and review remaining account tokens before the
full run.** A successful preflight is not a guarantee that thirty calls fit TPD.

## 3. Smoke test — completed October 30

The successful run used the command below with destination `groq_smoke_02`.
Do not rerun either existing smoke folder. Live baseline/tool/final stages used
727 / 602 / 870 tokens. The run is API validation only, not benchmark evidence.

```powershell
.venv/Scripts/python.exe -B -m phase3_llm.runner `
  --provider groq --mode smoke --allow-live --api-key-file .groq_api_key `
  --model openai/gpt-oss-120b --thinking medium --max-output-tokens 4096 `
  --timeout 300 --request-interval 90 --max-model-calls 3 --max-total-tokens 20000 `
  --output-dir experiment_runs/groq_smoke_NEW
```

The output folder must be new. This uses one fictional pair and a fixture verifier.
Expected success: **two executions, zero failures, three HTTP requests**. Check
authentication, baseline JSON, tool arguments/execution, final JSON and actual
`usage.prompt_tokens`, `completion_tokens`, `total_tokens`, reasoning-token details
and `_rate_limits` headers in provider responses. Smoke is not benchmark evidence.

Medium reasoning remains enabled. `include_reasoning=false` hides reasoning text;
it does not disable thinking. The tool stage uses native function calling with one
allowed verifier and parallel calls disabled. Baseline/final stages use strict JSON
schema with no declared tools. The original tool-call ID/result are retained in
history. No built-in search, browser or code-execution tools are exposed.

## 4. Budget safeguards

- Default start spacing is **90 seconds**, with an enforced minimum of 65 seconds.
  The checkpoint pilot explicitly uses **65 seconds**; model/reasoning/evidence
  settings are unchanged. Successful smoke calls each consumed under 1k tokens.
- `experiment_runs/groq_quota_ledger.jsonl` reserves **8k tokens before each HTTP
  request**. Valid provider usage replaces that reservation; unknown/error usage
  keeps the reservation. The ledger is shared across runs.
- The local rolling 24-hour cap is **180k**; default per-run cap is **170k** and the
  smoke cap is **20k**. Reservations count, so these caps can stop a run early.
- Estimated input plus maximum generation must fit 8k. No evidence truncation,
  top-k change, reasoning reduction, retry or provider switch is automatic.
- The ledger cannot see external organization usage or guarantee server quota.
  Check the account dashboard. A timeout can still have consumed server resources.
- Use one local runner at a time. If a process is killed, verify it stopped before
  removing a stale ledger `.lock` file. **Preserve the ledger**; deleting it loses
  quota accounting. Never discard failed attempts to make coverage look complete.

## 5. Full fresh ten-pair experiment — completed October 30

Run **all ten pairs on Groq**. Do not pool the previous Gemini pair into this run.
Freeze model, prompts, evidence and settings. The actual run uses 65-second
spacing: about 33 minutes including the final smoke-to-pilot wait, plus latency.
The source snapshot is `experiment_runs/groq_checkpoint_20261030/frozen_code`.
The conservative ledger charge before the pilot was 10,199 tokens: 2,199 reported
smoke tokens plus the retained 8k unknown-usage reservation for the blocked attempt.
The original all-max-generation estimate remains a caveat; the 170k run/180k
workspace caps can stop incomplete coverage. No cap was raised to force completion.

```powershell
.venv/Scripts/python.exe -B -m phase3_llm.runner `
  --provider groq --mode experiment --dataset corpus --allow-live `
  --api-key-file .groq_api_key --model openai/gpt-oss-120b `
  --thinking medium --max-output-tokens 4096 --timeout 300 `
  --request-interval 65 --max-model-calls 30 --max-total-tokens 170000 --top-k 5 `
  --corpus phase2_corpus/retrieval_documents.jsonl `
  --pairs phase2_experiment/pilot_target_pairs.json `
  --dataset-version pilot-v1.1-frozen-groq-checkpoint `
  --output-dir experiment_runs/groq_pilot_01
```

Actual complete run: **20 executions, zero failures, 30 HTTP requests**. A uses
one request without a verifier; B uses two with one validated verifier call. This
is the verifier-removal ablation with equal initial evidence, not equal compute.
The final model decision is preserved even if it disagrees with the verifier.
Failures remain failures; local quota/provider errors stop further requests. There
is no automatic resume. Score incomplete runs with their actual coverage and record
a recovery plan before further attempts. Additional ablations are optional only
after the main comparison, scoring/report and remaining token budget are secured.

## 6. Score, review and submit

```powershell
.venv/Scripts/python.exe -B -m phase2_experiment.score_run `
  --run-dir experiment_runs/groq_pilot_01 `
  --pairs phase2_experiment/pilot_target_pairs.json `
  --corpus phase2_corpus/retrieval_documents.jsonl `
  --labels phase2_ground_truth_vault/pilot_manifest.json `
  --provenance phase2_corpus/internal_provenance.jsonl `
  --output-dir experiment_runs/groq_pilot_01_scores
```

Only post-execution scoring joins labels/provenance. Reports identify the model,
dataset, coverage, binary/condition/paired metrics, tool calls, HTTP requests sent
and provider-reported usage. Verifier consistency is not independent validation.
Have another teammate review all twenty outputs and evidence if feasible using
the generated CSV. Import **actual** completed ratings with `--manual-review PATH`
into a new score directory. Procedure: [SCORING.md](phase2_experiment/SCORING.md).

`MID_SUBMISSION_PROGRESS.md` now contains actual progress, datasets, baseline and
ablation results, challenges/mitigations and the final timeline. Independent human
review remains pending: import real ratings only, into a new score destination.
Local run folders are ignored. The selected result bundle is under `research_audit/`;
it contains synthetic evidence, outputs and scoring metadata, with no raw hidden
label/provenance files, API keys or quota ledger. Preserve the original run artifacts.
