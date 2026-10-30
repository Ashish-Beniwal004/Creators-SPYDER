<!-- Historical Gemini workflow snapshot before the Groq switch; current instructions are in PILOT_RUNBOOK.md. -->

# Integrated pilot: free-tier setup and execution

Updated October 30, 2026 (IST). **User constraint: free tier only.** Do not enable billing,
buy credits, or use a paid project for this work.

## October 30 quota and live-access update

The user confirmed Free plan, 5 requests/minute, 20 requests/day and initially
300k input tokens/minute; the later dashboard reading was 250k TPM. Use the lower
250k limit unless the dashboard clarifies it. Daily requests are the constraint.
Google resets RPD at midnight Pacific: **12:30 p.m. IST on October 30**.
Source: [official quota rules](https://ai.google.dev/gemini-api/docs/rate-limits).

The saved key works for model metadata. One actual fictional baseline returned
valid JSON after 157 seconds. Two earlier requests timed out (60/180 seconds),
and the first tool-only check returned HTTP 503. A final tool-only smoke then
completed both model requests and the validated verifier call. Its manifest is
`experiment_runs/live_tool_smoke_20261030_04/manifest.json`. Those earlier attempts remain recorded;
they are not successful experiments or model verdicts. The model's medium
thinking setting and 4096-token output allowance are unchanged. New requests use
a **300-second timeout and 35-second minimum spacing**; retries are disabled.
Six setup requests were attempted in total (one completed baseline, two completed
tool-smoke requests, two timeouts and one HTTP 503).

Use four paired cases before reset (**12 requests**) and six after reset
(**18 requests**). Up to six setup attempts plus twelve experiment requests leaves
two requests of margin before reset, assuming no external project usage. The
user's dashboard confirmed 3/20 after the first two smoke runs, matching local
logs. Recheck current usage before each live block. Stop on another provider error;
do not repeatedly rerun or enable billing. A successful tool smoke must precede
the scientific run. Latest statuses are in the per-run manifests under
`experiment_runs/live_*20261030*`.

`phase2_experiment/checkpoint.py` prepares fixed public pair files and scores both
native runs after execution. No model calls are made by this helper. The prepared
campaign is `experiment_runs/checkpoint_20261030/campaign.json`:

- Group 1: original zero-based indexes `[0, 3, 4, 7]`.
- Group 2: `[1, 2, 5, 6, 8, 9]`.

Together they contain every original pair exactly once. The split was revised
from 5/5 to 4/6 after setup failures, before any real pilot outputs were seen.
Disclose the different quota windows and their different condition composition.
Combined offline validation: **210 passed, 4 skipped, 25 subtests passed**.

**Actual first-block outcome:** one pair completed in both arms; the next baseline
returned HTTP 503. The block stopped with 2 completed, 1 failed and 5 missing
execution records. It consumed 4 inference attempts, for **10 total including
setup**. The partial score is in
`experiment_runs/checkpoint_20261030_group1_scores/report.json`; portable evidence
is `research_audit/OCT30_LIVE_VALIDATION.json`. No additional request was made after
that failure. Group 2 is not started. Reassess service availability and dashboard
usage before continuing. An existing run directory cannot be overwritten; do not
discard the partial run or silently rerun completed pairs. The commands below
describe the intended campaign, not a claim that either full block has finished.

## Current local state

- Branch: `feat/llm-integration-runner`.
- Member 1 commit: `6f35e83`; Member 2 + Member 3 tip: `d7ec222`.
- Member 3 was merged locally with `--no-commit`; the merge and additional
  integration changes await the user's review/commit. Nothing was pushed.
- October 29 combined validation: **206 passed, 4 skipped, 25 subtests passed**. The four
  skips require the absent upstream raw dataset. Frozen-artifact checks passed.
- A new offline pilot check completed 20 executions and 30 scripted requests,
  and the native scorer accepted all 10 paired cases. Artifacts are under
  `experiment_runs/integrated_pilot_offline_20261029T070633476514Z` and its
  adjacent `_scores` folder. These are **software checks, not LLM results**.
- October 29 had no real API calls. See the October 30 update above for actual
  access attempts and limitations. No human evidence review has been fabricated.

The integration adds provider-error stopping, one-pair smoke tests, optional local
key-file input, dependency/environment hashes, an actual repository integration
test, and a scorer fix for canonical entity ordering. A provider failure stops
further requests and leaves the failed and remaining executions visible. A model
output validation failure remains a recorded case failure; it is not a verdict.

## 1. Set up a free Gemini key

1. Open [Google AI Studio API keys](https://aistudio.google.com/api-keys) and sign
   in with your Google account. Review any account terms yourself.
2. Use a project whose **Plan / usage tier is Free**, or create a new project
   without linking a billing account. Create an API key in that project. New
   AI Studio accounts may already have a default project and key. If an existing
   account shows only paid projects, create/select a separate free project.
3. Confirm the project shows **Free**, not Paid/Tier 1. Do not click **Set up
   billing**, add payment details, or treat Cloud trial credits as free API access.
4. In your editor, create a file named exactly `.gemini_api_key` at this repository
   root. Paste **only the key** into the file and save. No quotes, variable name,
   or `GEMINI_API_KEY=` prefix. Avoid an accidental `.txt` extension on Windows.
   This exact filename is ignored by Git; do not force-add it. Do not paste the
   key into chat. An existing `GEMINI_API_KEY` environment variable is also supported.
5. Check the project's [active rate limits](https://aistudio.google.com/usage?timeRange=last-28-days&tab=rate-limit)
   for **gemini-3.8-flash**. Record model access, requests/minute, input tokens/minute
   and requests/day. These numbers are safe to share; the key is not.

Google currently lists Gemini 3.8 Flash text input/output on the free tier. Actual
access and capacity are account-specific. The code cannot determine your billing
tier from a key, so verifying the project's Free plan is necessary before running.
If access is denied, keep the error and resolve free access; do not enable billing
or silently switch models. Sources checked October 29:
[API-key setup](https://ai.google.dev/gemini-api/docs/api-key),
[billing tiers](https://ai.google.dev/gemini-api/docs/billing),
[model pricing](https://ai.google.dev/gemini-api/docs/pricing),
[rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## 2. Check the integrated checkout

Review the merge and new changes, then commit them locally before freezing a real
experiment. The runner records the commit, pending merge parent, dirty state,
prompt and implementation hashes, repository dependency hashes and environment.
It does not commit or push anything.

```powershell
.venv/Scripts/python.exe -B -m pytest phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests phase2_ground_truth_vault/tests phase3_llm/tests -q -p no:cacheprovider
```

## 3. Run the tiny live smoke test

Only after confirming the key's project is Free and the model has quota:

```powershell
.venv/Scripts/python.exe -B -m phase3_llm.runner `
  --provider gemini --mode smoke --allow-live `
  --api-key-file .gemini_api_key `
  --model gemini-3.8-flash --thinking medium --max-output-tokens 4096 `
  --timeout 300 --request-interval 35 --smoke-pairs 1 --max-model-calls 3
```

This uses **one fictional pair and a scripted verifier**, with real model requests.
Expected: two completed arm executions, zero failures, three model requests.
It tests authentication, JSON output and the tool round-trip, not evidence quality.
The runner prints the unique output directory; keep its actual name. For a project
limited to one request/minute, increase spacing above 60 seconds before starting.
Check input-token/minute limits as well; spacing alone does not guarantee quota.

If it fails, inspect `errors.jsonl`, `manifest.json` and the trace in that run.
The adapter preserves HTTP status codes without logging credentials. A provider
failure stops the run; no retries or fallback model are automatic. Typical checks:
400: request format/configuration; 401/403: key/project/access; 404: model/API
availability; 429: rate/quota. These are diagnostic clues, not definitive causes.
Do not rerun repeatedly against an exhausted daily quota. Any development fix gets
a new smoke run before changing the frozen experiment settings.

For this checkout the baseline already succeeded. Use `--smoke-arm
system_b_rag_verification --max-model-calls 2` to test only the remaining tool
round-trip. Single-arm selection is forbidden for experiments. Do not repeat a
successful stage merely to produce a fresh all-in-one smoke folder.

## 4. Freeze and run the minimum experiment

The 30-request pilot cannot fit one 20-request quota window. Use the predeclared
4/6 campaign above, only after the tool smoke succeeds. No partial run should be
presented as a complete pilot. Other project usage also consumes the shared quota.

Freeze model, thinking, output limit, request spacing, prompts, corpus and top-k.
Use the unchanged 10-pair pilot and 31-document corpus. The full corpus still has
known text cues correlated with negative labels, so it is not the primary clean
quality evaluation for this checkpoint.

```powershell
.venv/Scripts/python.exe -B -m phase3_llm.runner `
  --provider gemini --mode experiment --dataset corpus --allow-live `
  --api-key-file .gemini_api_key `
  --model gemini-3.8-flash --thinking medium --max-output-tokens 4096 `
  --timeout 300 --request-interval 35 --top-k 5 --max-model-calls 12 `
  --corpus phase2_corpus/retrieval_documents.jsonl `
  --pairs experiment_runs/checkpoint_20261030/group_1_pairs.json `
  --dataset-version pilot-v1.1-frozen-two-quota-windows `
  --output-dir experiment_runs/checkpoint_20261030/group_1_run
```

Expected group 1: **8 completed executions, zero failures, 12 requests**.
After 12:30 p.m. IST, confirm that the dashboard reset and run group 2 using
identical settings, changing only these three arguments:

```powershell
--pairs experiment_runs/checkpoint_20261030/group_2_pairs.json
--max-model-calls 18
--output-dir experiment_runs/checkpoint_20261030/group_2_run
```

Expected group 2: **12 completed executions, zero failures, 18 requests**.
The two completed groups together provide **20 executions and 30 requests**.
Both arms receive the same initial evidence. A uses one model request, B uses two
with one validated verifier call. This is an equal-initial-evidence comparison;
compute differs. A is the verifier-removal ablation of B. Additional retrieval-k
ablations are optional after this comparison works and free quota permits.

The model's final answer is preserved even when it disagrees with the verifier.
Failures are not converted to Insufficient Evidence. If a run is incomplete, retain
it; the scorer reports failure/paired coverage. There is no automatic resume or
selection of only successful cases. Do not tune on the full test labels and call
the resulting experiment held out.

## 5. Score saved outputs and review evidence

Once both groups have saved results (including failures), score the declared
campaign. The score directory must be new. This is the first live-workflow step
with hidden-label access.

```powershell
.venv/Scripts/python.exe -B -m phase2_experiment.checkpoint score `
  --directory experiment_runs/checkpoint_20261030 `
  --group-1-run experiment_runs/checkpoint_20261030/group_1_run `
  --group-2-run experiment_runs/checkpoint_20261030/group_2_run `
  --output-dir experiment_runs/checkpoint_20261030_scores
```

Have another teammate review all 20 outputs if feasible using the generated
`review_template.csv` and exact evidence text. Keep reviewer fields blank until
someone actually reviews them. Import completed ratings with `--manual-review`
into another new score directory. The helper checks disjoint membership and common
model/prompt/code/environment settings before pooling validated results. It retains
per-group coverage and marks the campaign complete only if both real experiments
completed. Its files ending `_labels_PRIVATE.json` are post-execution scoring inputs,
not files to publish or send to the model. To reproduce preparation, use
`python -m phase2_experiment.checkpoint prepare --directory NEW_DIRECTORY` and
adjust both run commands accordingly.
See [scoring definitions and review procedure](phase2_experiment/SCORING.md).
The verifier consistency diagnostic is not independent human validation. Binary
metrics and three-way evidence judgments answer different questions.

## 6. October 30 submission package

| Requirement | Evidence to include |
|---|---|
| Progress | Implemented two-arm runner, actual verifier/scorer integration and passing checks |
| Datasets | Synthetic pilot: 10 pairs, 5 positive/5 negative, 31 documents; versions/hashes and limitations |
| Baseline | Legacy deterministic results clearly labelled, plus real LLM-only A once actually run |
| Ablations | Fixed A/B verifier-removal comparison; disclose B's extra model request |
| Actual results | Real saved runs, coverage/failures, metrics and completed independent review; never substitute mock output |
| Challenges | API/quota availability, alias grammar, withheld evidence, label/evidence mismatch and synthetic text cues |
| Mitigation | One-pair smoke, stop on provider errors, frozen pilot, explicit failure accounting and independent review |
| Final timeline | Oct 31–Nov 2 feedback/corpus design; Nov 3–7 experiments; Nov 8–11 analysis; Nov 12–14 reproduce/report; Nov 15 submit |
| Updated GitHub | User reviews and pushes code, commands and selected reproducibility artifacts manually; no automatic push |

Local `experiment_runs/` is ignored. Select the reviewed config, manifests,
decisions, scoring summaries and reproducibility evidence for publication explicitly.
Review traces and case-level material before sharing; hidden labels/provenance must
not become model inputs. If access remains blocked, report the implemented work
and actual deterministic results honestly, with the live-experiment gap explicit.
