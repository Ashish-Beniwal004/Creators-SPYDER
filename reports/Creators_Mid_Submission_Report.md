# SPYDER Mid-Submission Report

Team Name: Creators  
Date: October 30, 2026

## 1. Project Purpose and Implemented Scope

SPYDER investigates whether evidence verification improves retrieval-augmented generation (RAG) when incident and call-detail records contain aliases, missing identity links and distractors.

The checkpoint evaluates whether two target entities jointly participated in a documented solved burglary between January 1 and June 30, 2020.

- Arm A retrieves up to five documents and answers without verification tools.
- Arm B uses the same retrieved evidence, selects evidence IDs for one verifier call, receives its result and produces a final answer.
- The controller fixes this sequence and preserves the model's final decision, including any disagreement with the verifier.

This checkpoint implements bounded tool use over supplied target pairs. Full network discovery and autonomous multi-hop investigation remain outside the current scope. The benchmark uses apprehension, detention or positive perpetrator identification as operational solved-status cues, without establishing formal case closure or legal guilt.

## 2. Progress Completed

- Integrated the audited pilot corpus, LLM runner and verifier/scorer on `feat/llm-integration-runner`.
- Implemented Groq `openai/gpt-oss-120b`, native verifier calls, structured JSON decisions, citation and argument validation, and experiment logging.
- Added request pacing, token accounting, per-run limits and separate output directories. Provider failures are recorded without assigning a decision.
- Improved alias attribution and conflict handling in the deterministic verifier, with regression tests. Frozen data and historical results were preserved.
- Implemented post-execution scoring, paired coverage, condition analysis, tool-call statistics and a human-review CSV template.
- Completed the real ten-pair Groq comparison with 20 successful executions and no failures.
- Validation recorded 221 tests passed, 4 skipped and 30 subtests passed. The skipped checks require the unavailable upstream graph.
- A clean committed-source export reproduced the saved metrics and matched 24 bundle hashes and 30 source hashes without API-key files. This used the same installed environment.

The initial Groq smoke test completed both arms with 3 requests and 2,199 tokens using fictional evidence. Smoke and scripted-test outputs are excluded from experimental performance metrics.

Implementation: `phase3_llm/`, `phase2_verification/verifier.py` and `phase2_experiment/score_run.py`.

## 3. Datasets Being Used

The repository documents the source backbone as the Israel National Police (INP) / ROXANNE Burglary Offender and Crime Network, using the January to June 2020 slice. Source attribution and dataset references are recorded in [DATASET_NOTICE.md](https://github.com/Ashish-Beniwal004/Creators-SPYDER/blob/f9018bbd35af1473f14107c748c87d1adfe0c46f/DATASET_NOTICE.md), with the upstream files in the [source repository](https://github.com/erichoang/criminal-network-visualization).

The experiment uses the project's frozen evidence assets rather than the raw source graph. Incident and call-detail texts are generated evidence, not original police reports or transcripts.

| Dataset                     | Contents                                                                                                         | Use                                                        |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Frozen pilot v1.1           | 10 pairs, 5 positive and 5 negative, with 31 documents comprising 20 incident reports and 11 call-detail records | Primary live comparison                                    |
| Existing full corpus        | 200 pairs, 100 positive and 100 negative, with 680 documents                                                     | Deterministic development diagnostics                      |
| Fictional software fixtures | 4 cases, with 1 used for live smoke testing                                                                      | Software and API checks, excluded from performance metrics |

Primary inference files:

- `phase2_experiment/pilot_target_pairs.json`, containing unlabelled target pairs.
- `phase2_corpus/retrieval_documents.jsonl`, containing sanitized evidence text, IDs and types.

Labels and provenance are excluded from inference inputs and used separately for dataset auditing and post-execution scoring. The adapter forwards only approved public fields. Inference-boundary tests check that labels and provenance are not read by the inference path.

The source graph is unavailable locally, so label regeneration has not been independently reproduced. The audited pilot has been inspected during development. The larger corpus has known construction cues and is not used as the live quality benchmark. Input hashes are retained in the saved run and source manifests.

## 4. Baseline Experiments

The LLM baseline is Arm A, GPT-OSS 120B with retrieved evidence and no verifier. It is compared with Arm B on the same target pairs and initial retrieval.

The existing deterministic systems were also rerun as development diagnostics:

| Deterministic pilot system | TP  | FP  | TN  | FN  | Accuracy | F1     |
| -------------------------- | --- | --- | --- | --- | -------- | ------ |
| Legacy heuristic A         | 5   | 2   | 3   | 0   | 0.80     | 0.8333 |
| Legacy verifier workflow B | 4   | 0   | 5   | 1   | 0.90     | 0.8889 |

These are deterministic results, not LLM performance. Records are in `research_audit/member3_deterministic_validation.json`. Verifier changes were developed against existing cases, and historical outputs were not overwritten.

## 5. Ablation Experiment

The completed ablation removes verification while keeping the model and initial evidence fixed.

| Arm                   | Initial evidence            | Model requests per pair | Verification                                    |
| --------------------- | --------------------------- | ----------------------- | ----------------------------------------------- |
| A: RAG only           | Shared top-5 retrieval      | 1                       | Removed                                         |
| B: RAG + verification | Same shared top-5 retrieval | 2                       | One model-selected verifier call and its result |

Both arms use `openai/gpt-oss-120b`, medium reasoning, a 4,096 completion-token limit, a 300-second timeout and 65-second request spacing. Prompt version and evidence are fixed, with no automatic retries or tuning between cases.

Each arm produces one sampled output per pair. Temperature and seed use provider defaults. Arm B receives additional computation, so this comparison is not compute matched. No additional retrieval-k, reasoning-level or multi-hop ablation has been run.

## 6. Results from Experiments Run

### 6.1 Groq pilot

The run completed on October 30, 2026 at 14:59:53 IST. Both arms completed all ten pairs, giving 20 successful executions, zero failures, zero missing results and 30 model requests.

| LLM system            | TP  | FP  | TN  | FN  | Accuracy | Precision | Recall | F1     |
| --------------------- | --- | --- | --- | --- | -------- | --------- | ------ | ------ |
| A: RAG only           | 4   | 0   | 5   | 1   | 0.90     | 1.00      | 0.80   | 0.8889 |
| B: RAG + verification | 4   | 0   | 5   | 1   | 0.90     | 1.00      | 0.80   | 0.8889 |

Both arms made the same ten decisions, with 4 Supported and 6 Insufficient Evidence. Neither predicted Unsupported. Binary scoring maps Supported to 1 and both other decisions to 0.

No verification improvement was observed on this pilot. Arm B used twice as many model requests for the same binary result.

| Condition        | Pairs | A correct | B correct |
| ---------------- | ----- | --------- | --------- |
| Clean evidence   | 2     | 2         | 2         |
| Alias ambiguity  | 2     | 2         | 2         |
| Missing evidence | 2     | 1         | 1         |
| Distractors      | 2     | 2         | 2         |
| Mixed difficulty | 2     | 2         | 2         |

The shared false negative is the positive missing-evidence case. Retrieved phone records do not provide a usable joint-burglary identity link, and the anonymous incident report identifies no suspects. Both models therefore abstained. This counts as a binary-label miss without, by itself, establishing a reasoning error.

| API usage         | A      | B      | Total  |
| ----------------- | ------ | ------ | ------ |
| Requests          | 10     | 20     | 30     |
| Prompt tokens     | 8,737  | 22,219 | 30,956 |
| Completion tokens | 4,627  | 7,008  | 11,635 |
| Total tokens      | 13,364 | 29,227 | 42,591 |

Completion usage includes 7,941 reasoning tokens. All ten required verifier calls were accepted and executed. The 2,199 smoke-test tokens are separate from the pilot totals above.

The selected run and score report are in `research_audit/groq_checkpoint_20261030/`. Saved-output rescoring reproduced identical metrics without model calls. Independent human unsupported-assertion rate and three-way evidence accuracy have not been measured.

### 6.2 Earlier Gemini feasibility attempt

An earlier Gemini run completed one pair in both arms before HTTP 503 stopped the next baseline request. This incomplete attempt is retained as feasibility evidence and is not pooled with Groq results. Its record is `research_audit/OCT30_LIVE_VALIDATION.json`.

## 7. Challenges Faced

- Gemini's 20-request daily limit, timeouts and HTTP 503 interrupted the planned comparison.
- Groq initially rejected Python's default HTTP client header with HTTP 403. A model-access check isolated the header issue.
- Free-tier token limits required careful request sizing and pacing.
- Ambiguous aliases and missing identity links make binary labels different from the evidence available to the model.
- Qualitative review found a timing overstatement in Pair 07 and imprecise attempted-burglary wording in Pairs 06 and 10. These details were not captured by binary accuracy alone.

## 8. Mitigation Plans

- Ran the complete primary comparison on Groq and kept Gemini results separate.
- Added an application User-Agent, validated the tool and final-answer stages, and retained medium reasoning and top-5 evidence.
- Used 65-second spacing, a 170,000-token run limit and a 180,000-token rolling workspace limit. Unknown usage remains conservatively reserved, with no automatic retry or provider fallback.
- Preserved exact evidence, responses, errors, usage and configuration hashes. Failed or missing executions are never replaced with negative decisions.
- Added alias and ambiguity regression tests, kept labels outside inference, and retained unresolved identities without inventing mappings.
- Retained the original answers and documented rationale issues. Independent evidence review and clearer evidence-availability references are planned for the final evaluation.

## 9. Timeline for Final Submission

| Dates            | Work and deliverable                                                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Oct 30           | Pilot, scoring and code/results push complete, finalize and submit the mid-submission report                                            |
| Oct 31 to Nov 2  | Address checkpoint findings, check source-data availability and design a cleaner evaluation split with evidence-availability references |
| Nov 3 to Nov 7   | Freeze data and prompts, run larger paired experiments and selected ablations within available quota                                    |
| Nov 8 to Nov 11  | Analyze condition errors, alias failures and verifier disagreements, complete independent evidence review                               |
| Nov 12 to Nov 14 | Reproduce saved metrics, finalize report, demo and repository                                                                           |
| Nov 15           | Final submission and freeze of submitted artifacts                                                                                      |
| Nov 16 to Nov 19 | Evaluation and demonstration                                                                                                            |

## 10. Repository and Reproducibility

The updated code and selected results are on the [integration branch](https://github.com/Ashish-Beniwal004/Creators-SPYDER/tree/feat/llm-integration-runner) at commit [f9018bb](https://github.com/Ashish-Beniwal004/Creators-SPYDER/commit/f9018bbd35af1473f14107c748c87d1adfe0c46f). The default release branch contains earlier work.

The bundle `research_audit/groq_checkpoint_20261030/` contains the native run, scores, evidence packets, review template, dependency versions and integrity index. Credentials and the local quota ledger are excluded. The source and environment validation record is `research_audit/CHECKPOINT_CLOSEOUT_20261030.json`.

The run used Python 3.13.2 with pydantic, scikit-learn, numpy and pytest. Saved-output reproduction needs installed dependencies but no API key.

Run the test suite from the repository root:

```powershell
.venv/Scripts/python.exe -B -m pytest phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests phase2_ground_truth_vault/tests phase3_llm/tests -q -p no:cacheprovider
```

Expected result: 221 passed, 4 skipped and 30 subtests passed.

Rescore the saved experiment to a new destination:

```powershell
.venv/Scripts/python.exe -B -m phase2_experiment.score_run --run-dir research_audit/groq_checkpoint_20261030/groq_pilot_01 --pairs phase2_experiment/pilot_target_pairs.json --corpus phase2_corpus/retrieval_documents.jsonl --labels phase2_ground_truth_vault/pilot_manifest.json --provenance phase2_corpus/internal_provenance.jsonl --output-dir experiment_runs/m4_reproduced_scores_NEW
```

Expected result: ten paired cases, with TP=4, FP=0, TN=5, FN=1, accuracy 0.90 and F1 0.8889 in each arm. This command reads labels only for post-execution scoring and makes no model calls.

## 11. Current Limitations

- This is a ten-pair synthetic development pilot with one sampled output per arm. Larger evaluations and repeated runs are needed to assess stability and generalization.
- The verifier arm uses more model calls, so the comparison does not isolate verification under equal compute.
- Independent human ratings remain unmeasured. The assistant-assisted qualitative review identifies issues to investigate, rather than providing human accuracy or unsupported-assertion rates.

## 12. Team Members and Roles

| Roll Number | Name                     | Assigned Workstream | Responsibility                          |
| ----------- | ------------------------ | ------------------- | --------------------------------------- |
| 2025204006  | Shada praneeth reddy     | M1                  | LLM integration and experiment runner   |
| 2026909001  | Ashish benwal            | M2                  | Dataset and evidence audit              |
| 2025204003  | Nagam Chandrakanth reddy | M3                  | Verifier, tests and scoring             |
| 2025204022  | Paila Tejeswara Rao      | M4                  | Environment, reproducibility and report |

## 13. Contribution Details

M1 - Shada praneeth reddy (2025204006):

- Built model adapter, common prompts, structured output contract and experiment logging.
- Implemented Groq provider (openai/gpt-oss-120b), native verifier tool call, strict JSON decisions, bounded A/B execution and trace/config/manifest exports.
- Implemented shared request pacing, token ledger, per-run call and token caps.
- Conducted Groq smoke test and full ten-pair pilot run. Saved responses, tool traces, citations, failures and usage.

M2 - Ashish benwal (2026909001):

- Inspected the 10-case pilot corpus in a separate review. Checked evidence conditions, counts, schemas and hashes.
- Verified 10 cases, 31 retrieval documents (20 incident reports + 11 call-detail records), 31 provenance records.
- Checked label and provenance separation, alias limitations, construction cues and hash integrity.
- Documented unresolved aliases and provenance release boundary. Did not edit frozen pilot during experiments.

M3 - Nagam Chandrakanth reddy (2025204003):

- Investigated alias parsing and verifier failure modes. Fixed alias attribution and conflict handling.
- Added regression tests. Defined decision labels and scoring metrics.
- Implemented post-execution native-artifact validation and scoring (score_run.py), coverage and paired metrics, condition diagnostics, retrieval diagnostics and human-review CSV handling.
- Validated output and evaluator contracts. Ran deterministic baseline diagnostics.

M4 - Paila Tejeswara Rao (2025204022):

- Reviewed recorded dependencies and setup steps.
- Reviewed and incorporated the recorded clean committed-source reproduction evidence, including tests, saved-output rescoring and bundle and source hash matching.
- Assembled this mid-submission report from measured results. Verified branch and commit links for submission.
