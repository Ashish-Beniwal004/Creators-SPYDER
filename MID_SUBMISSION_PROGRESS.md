# SPYDER mid-submission - October 30, 2026

Status: **The real Groq pilot is complete and scored: ten pairs, twenty executions,
thirty requests, zero failures. Both arms achieved 90% binary accuracy and 0.8889 F1.**
No verification improvement was observed in this pilot. The selected saved-output
bundle was rescored successfully with identical serialized metrics. This report
separates completed work from pending human review and submission actions.
The submission implementation and selected result bundle are maintained on
`feat/llm-integration-runner`. The default release branch describes earlier work.

## 1. Progress completed

- Integrated Member 1's LLM runner with Member 2's audited pilot and Member 3's
  verifier/scorer on `feat/llm-integration-runner`.
- Implemented Groq `openai/gpt-oss-120b` access, strict final JSON decisions, native
  verifier tool calls, citation/argument validation, bounded execution and tracing.
- Both systems use the same initial top-5 evidence. A answers without tools;
  B generates one verifier call, receives its result, then answers. The controller
  fixes this sequence. This is bounded tool use rather than autonomous search.
- Preserved the model's final decision, including disagreement with the verifier.
  Provider failures are logged as failures, never converted into negative verdicts.
- Added shared request pacing, local rolling token accounting, conservative unknown-
  usage reservations, per-run call/token caps and exclusive output destinations.
- Fixed documented alias-attribution patterns and ambiguous identity handling in
  the deterministic verifier. Frozen datasets and historical outputs are preserved.
- Implemented post-execution scoring, coverage/paired metrics, condition analysis,
  retrieval diagnostics and an unfilled human evidence-review CSV.
- Offline validation: **221 passed, 4 skipped, 30 subtests passed**. The four skips
  need the missing upstream graph. Scripted/fake-HTTP tests are software validation,
  not model performance evidence.
- A clean committed-source export without any API-key files passes the same
  suite and reproduces the saved metrics, 24 bundle hashes and 30 source hashes.
  It uses the same installed dependencies, so it is not a second-machine claim.
  The first export exposed two tests relying on a local key file; their mocked
  credential fixtures were fixed. Runtime and experimental outputs are unchanged.
- Actual Groq smoke: **2 completed executions, 0 failures, 3 requests, 2,199 tokens**.
  The baseline, native tool call and final structured response all succeeded.
  This uses fictional evidence and is excluded from benchmark metrics.

Implementation: `phase3_llm/`, `phase2_verification/verifier.py`,
`phase2_experiment/score_run.py`. Commands: [PILOT_RUNBOOK.md](PILOT_RUNBOOK.md).

## 2. Datasets being used

| Dataset | Contents | Use |
|---|---|---|
| Frozen pilot v1.1 | 10 pairs, 5 positive/5 negative; 31 documents: 20 incident reports + 11 call-detail records | Primary live checkpoint comparison |
| Existing full corpus | 200 pairs, 100 positive/100 negative; 680 documents | Deterministic development diagnostics only |
| Fictional software fixtures | Four cases; one used for live smoke | API/software checks; excluded from experiment metrics |

Primary inference inputs:

- `phase2_experiment/pilot_target_pairs.json`: unlabelled target pairs.
- `phase2_corpus/retrieval_documents.jsonl`: sanitized evidence text/IDs/types.

Pilot corpus SHA-256: `a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded`.
Pair file SHA-256: `f229dbd46a8999c2de0256a4f9cb69894a95ff43647d4ab883783fa1558b6d9d`.

Hidden labels (`phase2_ground_truth_vault/pilot_manifest.json`) and generation
provenance are accessed only after inference for scoring. The adapter forwards an
explicit public-field allowlist; inference-boundary tests reject label/provenance
reads. Run artifacts retain the exact retrieved documents for both arms.

The text is generated investigative evidence, not an independent collection of
real police reports. Binary labels represent documented shared burglary activity;
a positive label does not guarantee that enough supporting evidence is retrieved
or even available. The original source graph is absent locally, so its labels
cannot be regenerated here. Known label-correlated cues in the full corpus, reused
entities and development exposure prevent broad generalization claims. The audited
pilot is the small checkpoint evaluation, not an untouched held-out benchmark.

## 3. Baseline experiments

The actual LLM baseline is **A: GPT-OSS 120B with retrieved evidence and no verifier**.
It is compared with B in the same run, using the same initial retrieval.

Existing deterministic systems were also rerun as development diagnostics:

| Deterministic pilot system | TP | FP | TN | FN | Accuracy | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Legacy heuristic A | 5 | 2 | 3 | 0 | 0.80 | 0.8333 |
| Legacy verifier workflow B | 4 | 0 | 5 | 1 | 0.90 | 0.8889 |

Evidence: `research_audit/member3_deterministic_validation.json` and
`research_audit/MEMBER3_HANDOFF.md`. These figures are not LLM performance.
Verifier changes were developed against existing cases; that exposure is disclosed.
Historical saved results were not overwritten.

## 4. Ablations actually executed

The completed primary comparison removes the verifier:

| Arm | Initial evidence | Model requests/pair | Verification |
|---|---|---:|---|
| A: RAG only | Shared top-5 retrieval | 1 | Removed |
| B: RAG + verification | Same shared top-5 retrieval | 2 | One model-selected verifier call and its result |

Both arms use `openai/gpt-oss-120b`, medium reasoning, a 4,096 completion-token cap,
300-second timeout, 65-second request spacing, the same prompt version and no
automatic retry. B receives extra computation; this is not a compute-matched
causal estimate. Model choice, prompts and evidence are not tuned between cases.
No additional retrieval-k, reasoning-level or multi-hop ablation has been run.
Both arms completed all ten cases; no failed or missing cases were substituted.

Each arm has one sampled output per pair. Temperature and seed are not explicitly
set; provider defaults apply. Saved-output scoring is reproducible, but fresh live
generations are not guaranteed to be identical. No repeated-run stability or
statistical-significance result is claimed.

## 5. Results from experiments actually run

### Groq primary pilot

Completed October 30 at **14:59:53 IST**. Actual coverage: **10/10 pairs in both
arms, 20/20 executions, zero failures, zero missing results, 30 HTTP requests**.
Both arms made the same ten three-way decisions. Native output:
`experiment_runs/groq_pilot_01`; selected reproducibility bundle:
[research_audit/groq_checkpoint_20261030](research_audit/groq_checkpoint_20261030/README.md).

| Actual LLM system | TP | FP | TN | FN | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A: RAG only | 4 | 0 | 5 | 1 | 0.90 | 1.00 | 0.80 | 0.8889 |
| B: RAG + verification | 4 | 0 | 5 | 1 | 0.90 | 1.00 | 0.80 | 0.8889 |

Each arm predicted Supported for four cases and Insufficient Evidence for six;
neither predicted Unsupported. Insufficient-evidence rate: 60% in each arm.
`Supported` maps to binary 1; both other decisions map to 0. Binary correctness
alone does not establish evidence-supported reasoning. **The observed verification
gain is zero on this pilot**, while B uses twice as many model requests.

| Condition | Pairs | A correct | B correct |
|---|---:|---:|---:|
| Clean evidence | 2 | 2 | 2 |
| Alias ambiguity | 2 | 2 | 2 |
| Missing evidence | 2 | 1 | 1 |
| Distractors | 2 | 2 | 2 |
| Mixed difficulty | 2 | 2 | 2 |

The shared binary false negative is the positive missing-evidence case. Retrieval
contains phone records without a usable joint-burglary identity link. The corpus's
anonymous incident report identifies no suspects. Both models abstained rather
than infer co-offending from phone contact. This is a binary-label miss; it does
not by itself demonstrate faulty evidence reasoning. Independent review is pending.

| API accounting | A | B | Total |
|---|---:|---:|---:|
| Requests | 10 | 20 | 30 |
| Prompt tokens | 8,737 | 22,219 | 30,956 |
| Completion tokens | 4,627 | 7,008 | 11,635 |
| Total tokens | 13,364 | 29,227 | **42,591** |

Completion includes 7,941 reasoning tokens; they must not be added again. All ten
requested verifier calls were accepted and executed; B's final decision agreed
with its verifier in all ten cases. Positive-citation consistency is 4/4 in each
arm using the same verifier, so it is not independent validation. Smoke used 2,199
additional reported tokens; combined reported usage is 44,790. The local ledger
charges 52,790 after retaining the first blocked attempt's unknown-usage reserve.
External organization usage is not known.

The generation-rule retrieval diagnostic has support-document recall 1.0 for
**only three eligible pairs**. It does not establish complete evidentiary recall
over all ten pairs or prove that missing identities are recoverable. Do not turn
this restricted diagnostic into a blanket 100% retrieval claim.

Evidence: `research_audit/GROQ_LIVE_VALIDATION_20261030.json` and the bundle's
`scores/report.json`. The copied bundle was actually rescored with identical
serialized metrics/input hashes and no API calls. All 30 source files match the
saved source manifest; frozen corpus/historical-artifact hashes remain unchanged.

An [assistant-assisted qualitative review](research_audit/OCT30_ASSISTANT_EVIDENCE_REVIEW.md)
now covers all twenty outputs. It flags timing overstatement, attempted/completed
burglary wording and the benchmark's solved-status proxy. It is not independent
human adjudication and was not imported as human ratings.

Human citation review is pending. Verifier consistency reuses the system's own
verifier and is not independent validation. No human unsupported-assertion rate or
three-way evidence accuracy is claimed from blank review templates.

### Earlier Gemini feasibility attempt - separate model, incomplete

One pair completed in both Gemini arms, both predicting Supported. The next
baseline hit HTTP 503 and the run stopped: A completed 1/4, failed 1, missing 2;
B completed 1/4, failed 0, missing 3. One paired observation is not comparative
accuracy evidence. These outputs are not pooled with Groq or used to fill gaps.

Evidence: `research_audit/OCT30_LIVE_VALIDATION.json` and local
`experiment_runs/checkpoint_20261030_group1_scores/report.json`. Ten inference
attempts were logged in that earlier quota window: six setup and four experiment
attempts, counting timeouts/errors conservatively. The second Gemini block did not run.

## 6. Challenges faced

- Gemini's 20 requests/day could not accommodate the full 30-request comparison
  in one window; timeouts, long latency and HTTP 503 interrupted progress.
- Groq rejected Python's default HTTP client header with HTTP 403 / security-filter
  code 1010. Model-list checks isolated the header issue; an application User-Agent
  fixed it. The failed attempt is preserved, with an 8k local unknown-usage reservation.
- Groq permits 8k tokens/minute and 200k/day under the stated free limits. Offline
  sizing estimated 67,427 input tokens plus up to 122,880 generation tokens;
  the combined 190,307 is a conservative estimate, not measured GPT-OSS tokenization.
- Alias wording, ambiguous attribution and missing evidence require careful
  distinction between a false hypothesis and insufficient accessible evidence.
- Synthetic templates, full-corpus cues, reused entities and missing source data
  limit external validity. Ten pairs cannot support strong significance claims.

## 7. Mitigation plans and work applied

- Switched the new primary cohort entirely to Groq; kept Gemini results separate.
- Validated baseline/tool/final behavior before the full run; retained medium
  reasoning and top-5 evidence rather than reducing quality settings to save quota.
- Spaced requests by at least 65 seconds. The ledger reserves 8k per request and
  replaces it with validated usage; unknown usage remains reserved. Run cap: 170k;
  rolling 24-hour workspace cap: 180k. No automatic retries or provider fallback.
  These guards cannot see external organization usage or guarantee server quotas.
- Recorded every failure, source/configuration hash, exact evidence and provider
  usage. If stopped, score actual coverage and preserve missing/failed distinctions.
- Regression-tested alias grammar and conflicting identities; kept labels outside
  inference. Record evidence availability and retrieval diagnostics separately.
- Give exact evidence and the review CSV to teammates for independent review.
  Do not convert verifier agreement or an assistant's analysis into human ratings.
- Preserve the tested environment and source snapshot under
  `experiment_runs/groq_checkpoint_20261030/frozen_code`.

## 8. Timeline for the final submission

| Dates | Concrete work and deliverable |
|---|---|
| Oct 30 night | Finish/score actual pilot, inspect failures, independent evidence review if feasible, review report and manually push the code/results bundle |
| Oct 31-Nov 2 | Resolve checkpoint findings; recover source data if available; design a cleaner versioned evaluation split and an explicit evidence-availability reference |
| Nov 3-7 | Freeze data/prompts; run larger paired experiments and selected retrieval/verification ablations within quota; retain all attempts |
| Nov 8-11 | Analyze condition errors, alias failures and verifier disagreements; complete independent adjudication and limitations |
| Nov 12-14 | Reproduce saved metrics from a clean checkout; finish report/demo and repository review |
| Nov 15 | Final submission; freeze submitted commit and artifacts |
| Nov 16-19 | Evaluation/demo using the submitted version and saved evidence |

## 9. Repository and reproducibility

Use the [integration branch](https://github.com/Ashish-Beniwal004/Creators-SPYDER/tree/feat/llm-integration-runner)
for the current code, tests and actual experiment artifacts. The M3 verifier/scoring
branch is an intermediate workstream; M1 contains the integrated M2/M3 changes.
The existing default release branch remains a historical starting point.

The selected synthetic-development result bundle is
`research_audit/groq_checkpoint_20261030/`. It contains the exact native run,
score report, unfilled human-review template, evidence packets, dependency versions
and integrity index. No API-key file, quota ledger, raw label file or generation
provenance file was copied into that bundle. Existing benchmark evaluation material
in the repository is documented in [CHECKPOINT_DATA_POLICY.md](CHECKPOINT_DATA_POLICY.md);
this is not a claim of a blinded public release.

For the submission, record the exact integration-branch commit and verify evaluator
access. Report compilation and any optional real human ratings remain separate
from the completed implementation and recorded experiment.

Review procedure and CSV import: [phase2_experiment/SCORING.md](phase2_experiment/SCORING.md).
No additional architecture, autonomous search loop, graph export or UI is required
for tonight's minimum valid experimental pipeline.

### Checkpoint requirement status

| Course requirement | Evidence ready locally | Remaining action |
|---|---|---|
| Progress completed | Section 1, implementation and test record | Team review |
| Datasets used | Section 2, frozen input hashes | Include in submission |
| Baseline experiments | Sections 3 and 5, actual Groq A outputs | Include in submission |
| Ablations | Section 4, completed verifier-removal comparison | Explain unequal model-call budgets |
| Results actually run | Section 5, native run and reproduced score report | Include honest zero-gain finding |
| Challenges | Section 6 and observed API/error records | Include in submission |
| Mitigation plans | Section 7 and implemented safeguards | Include remaining evidence-review work |
| Final timeline | Section 8 through November 15 | Confirm owners with teammates |
| Updated GitHub with code | Integrated implementation, tests, exact run and reproduced scores on the integration branch | Submit the branch/commit link and verify evaluator access |

### Proposal alignment to explain in the checkpoint

The checkpoint implements the proposal's central RAG-versus-verification
comparison with fragmented incident/CDR evidence. It currently evaluates supplied
target pairs rather than discovering an entire network. Tool use follows one
required verifier step; it does not implement autonomous multi-hop investigation.
The verifier is advisory to the final model answer, rather than a controller that
forcibly replaces an unsupported model decision. Those choices must be described
as the current experimental scope. Broader discovery, additional evidence types,
graph/UI outputs and a separately tested hard verification gate remain final-phase
decisions; they are not claimed as implemented in this checkpoint.
