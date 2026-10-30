# Bounded LLM integration and experiment runner

Current live provider: **Groq / `openai/gpt-oss-120b`**. Use the
[pilot runbook](../PILOT_RUNBOOK.md) for smoke, experiment and scoring commands.
**Live Groq smoke passed:** two executions, three requests, 2,199 tokens.
**The ten-pair pilot is complete:** 20 executions, zero failures, 30 requests,
42,591 tokens. Both arms: binary accuracy 0.90, F1 0.8889; no observed improvement
from verification. See the [actual report](../MID_SUBMISSION_PROGRESS.md) and
[reproducibility bundle](../research_audit/groq_checkpoint_20261030/README.md).
Earlier Gemini results remain separate.
Offline validation: **221 passed, 4 skipped, 30 subtests passed**.
The same suite and saved-output scoring pass from a clean committed-source export
without key files. See [closeout evidence](../research_audit/CHECKPOINT_CLOSEOUT_20261030.json).

## Offline start

```powershell
python -B -m phase3_llm.runner
python -B -m unittest discover -s phase3_llm/tests -p test_pipeline.py -q
.venv/Scripts/python.exe -B -m unittest discover -s phase3_llm/tests -p test_groq.py -q
```

Default invocation uses fictional evidence and scripted responses: eight completed
executions, twelve scripted responses, no key/network. The Groq test file includes
the actual repository-service bridge, so it needs the existing requirements in
`.venv`. Fake-HTTP/scripted checks are not model experiments.

## Components

| File | Role |
|---|---|
| `contracts.py`, `prompts.py` | Public evidence/decision/tool contracts and common instructions |
| `model.py` | Provider protocol, requests/replies and shared ProviderError |
| `groq.py` | Standard-library Groq adapter; native verifier call, then strict final JSON |
| `quota.py` | Shared local token ledger, reservation, pacing and lock |
| `preflight.py` | Offline sizing of the actual pilot requests |
| `services.py` | Existing read-only retrieval/verifier adapters and unlabelled pair loading |
| `systems.py`, `runner.py` | Bounded two-arm execution, failures, traces and manifests |
| `fixtures.py` | Fictional software/API smoke inputs |
| `gemini.py` | Previous provider retained for historical reproducibility; no automatic fallback |

Both arms share one initial top-k retrieval. A uses one model response without
tools. B selects arguments for one allowed verifier call, receives its result and
returns a final model decision. The model's answer is retained even on disagreement.
No additional retrieval or tool call is allowed. This is bounded required tool use,
not autonomous search. Evidence budgets match; model-call counts differ (A=1, B=2).

## Groq configuration

Use `--provider groq --api-key-file .groq_api_key --allow-live` with smoke or experiment
mode. The root key filename is ignored by Git. `GROQ_API_KEY` is also supported.
Defaults: medium reasoning, 4096 maximum completion tokens, 300-second timeout,
90-second spacing and 170k per-run tokens. Reasoning text is hidden without disabling
reasoning. Tool and strict-JSON stages are separate, following Groq's restrictions.
No built-in search/browser/code-execution tools or unsupported `store` field are sent.
An application User-Agent avoids the security-filter rejection observed with
Python's default header. The checkpoint explicitly selects 65-second spacing;
90 seconds remains the reusable adapter default.

The ledger reserves 8k per request and substitutes valid reported usage. Unknown
usage remains reserved. Its rolling 24-hour workspace cap is 180k; minimum spacing
is 65 seconds. Input sizing is an estimate, not exact tokenization. External account
usage is invisible. Budgets may stop the run before completion. Never delete the
ledger to reset accounting or start concurrent runners. No automatic retry, input
truncation, reasoning reduction or provider fallback occurs. See the runbook for
budget assumptions and smoke-based review before the full experiment.

## Artifacts and scoring

Each new run stores `config.json`, shared `retrieval.jsonl`, `traces.jsonl`,
`results.jsonl`, `errors.jsonl` and a hashed `manifest.json`. Metadata records the
provider/model, prompt/data/code hashes, source/merge/dirty state and environment.
Traces retain actual provider usage, selected rate headers and quota events.
Manifests distinguish model attempts from provider HTTP requests sent. Failures
have no business verdict. Empty retrieval is a logged, zero-call controller decision.
Existing run folders and historical output paths are protected; complete runs also
receive compatible per-arm JSON exports. Nothing is committed or pushed automatically.

Use [the native scorer](../phase2_experiment/SCORING.md) after inference. It handles
partial runs with coverage and identifies model/provider explicitly. Never pool
different models into one A/B result. Human-review fields remain blank until real
reviewers assess the evidence; shared-verifier consistency is not independent truth.

Live Groq baseline JSON and all ten real verifier/tool/final round-trips passed.
Saved-output metrics were reproduced from the copied bundle. Independent evidence
review remains pending; verifier consistency is not a substitute for it.
The absent upstream graph, full-corpus text cues and small synthetic pilot limit
generalization. Historical Gemini workflow instructions are archived under
`research_audit/`; current live commands use Groq. Review keys/provider content and
hidden scoring material before selecting any artifacts for publication.
