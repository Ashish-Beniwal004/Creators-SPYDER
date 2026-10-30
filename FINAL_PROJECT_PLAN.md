# SPYDER: Final Execution Plan for the Mid-Submission

**October 30 update:** The next experiment uses **Groq / openai/gpt-oss-120b**
on all ten pilot pairs. Adapter/quota/scoring integration passes **221 tests with
4 skips**. The full ten-pair Groq pilot completed: **20 executions, 0 failures,
30 requests, 42,591 tokens**. Both arms: **90% binary accuracy, 0.8889 F1**;
no verification gain was observed. Results were reproduced from the copied bundle.
See [MID_SUBMISSION_PROGRESS.md](MID_SUBMISSION_PROGRESS.md) for all nine required
items, evidence review and submission scope. The earlier Gemini partial
run remains separate. Current setup, budgets and commands: [PILOT_RUNBOOK.md](PILOT_RUNBOOK.md).
Do not treat the historical status snapshots below as live Groq results.

**Final checkpoint handoff:** M1-M3 technical work is complete for this checkpoint.
Local commits are organized by merge, runtime, offline checks, results and docs.
A clean Git export passes 221 tests (4 skipped) and reproduces the saved scores
without credentials. See [MID_SUBMISSION_PROGRESS.md](MID_SUBMISSION_PROGRESS.md)
and [the evidence review](research_audit/OCT30_ASSISTANT_EVIDENCE_REVIEW.md) for
current results and limitations. Independent human review is not measured.

**October 29 implementation update:** Member 1's runner and Member 2/3's audited
pilot, verifier fixes and scorer are now integrated locally on
`feat/llm-integration-runner`; the merge awaits review/commit. Combined checks:
**206 passed, 4 skipped**, with an actual-corpus offline integration check. No live
LLM results exist yet. Access must remain **free tier only**. Follow
[PILOT_RUNBOOK.md](PILOT_RUNBOOK.md) for the next actions. The repository audit
below describes the original October 28 checkout; its statements about missing
dependencies/unimplemented components are historical, not the current status.

**Updated:** October 28, 2026 (IST)  
**Repository reviewed:** `release/curated-project-handoff`, commit `88d353d2f834a696fd8e8ad48652814d3afe7f6a`  
**Mid-submission:** October 30 night, 2026  
**Final submission:** November 15, 2026; evaluations November 16-19  
**Scope of this document:** Practical proposal alignment, checkpoint deliverables, four-person ownership, dependency order, parallel work, and the remaining final-submission timeline.

This plan is based on the freshly pulled repository. It distinguishes implemented work, recorded experimental evidence, locally verified facts, and work still to do. This document is the only new artifact created during this review; no implementation, dataset, or saved experiment has been changed.

## 1. What Changed in the Fresh Checkout

Compared with the previously reviewed commit `3c535b6`, the new commit adds three files:

- [Research audit source](research_audit/SPYDER_Research_Audit_and_Next_Phase.tex).
- [Research audit PDF](research_audit/SPYDER_Research_Audit_and_Next_Phase.pdf).
- [Machine-readable audit results](research_audit/audit_results.json).

**No implementation, dependency, dataset, or experimental-output changes were introduced by that commit.** The earlier implementation gaps have therefore not been fixed by the pull. The new audit is useful additional documentation and test evidence.

### Evidence we now have

| Evidence | Status and interpretation |
| --- | --- |
| New committed test record | `audit_results.json` records **148 passed, 4 skipped, 0 failed** for the existing 152-test suite. Its recorded source revision is `3c535b6`; the new commit adds the audit documents. Credit this as a recorded test run in the report author's environment. |
| Current local Python environment | Pydantic, scikit-learn, NumPy and pytest are absent. The full test suite was **not rerun locally** during this review. Setup is still a local prerequisite, not proof that the team's recorded test run failed. |
| Fresh syntax and data checks | All 34 Python files parse; all 20 JSON files and four JSONL files parse. |
| Fresh artifact-integrity checks | All 15 entries in the main hash manifest and all six entries in the public manifest match. The two manifests overlap; these are not 21 distinct artifacts. |
| Fresh result checks | Saved pilot/full binary confusion counts and metrics recompute from case-level outputs and stored labels. Both arms have the same saved initial retrieval, and their citations resolve to retrieved documents. |
| Fresh retrieval check | An independent TF-IDF calculation reproduces the saved rankings and scores for all 210 pilot/full queries. This is not a full dependency-backed pipeline run. |
| Split isolation | Stored pilot/dev/test/reserve partitions have no overlapping entity IDs or source crime IDs. This does not independently validate labels against the absent raw graph. |
| Source regeneration | The upstream raw network is still absent from `phase1_dataset_audit/data/`. Generation from source and source-label checks remain unverified locally. Normal inference over the included corpus does not need that graph. |

The new research audit explicitly leaves case-level failure causes unconfirmed. Its proposed re-retrieval experiment is a future direction, not implemented progress. The checks below provide additional diagnostics; they do not justify promising a particular recall or false-positive rate.

## 2. Existing Work and Practical Proposal Alignment

### What we should reuse

| Area | Current contents | Main evidence |
| --- | --- | --- |
| Dataset selection | Candidate survey, source links and selection rationale | [phase1_dataset_audit/](phase1_dataset_audit/) |
| Labels and splits | Pilot/full labels, case manifests, component partitions, generation scripts and schemas | [phase2_ground_truth_vault/](phase2_ground_truth_vault/) |
| Evidence | Pilot/full generators, searchable incident reports and call-detail records, hidden provenance | [phase2_corpus/](phase2_corpus/) |
| Retrieval | TF-IDF indexing, validation, deterministic ranking | [retriever.py](phase2_retrieval/retriever.py) |
| Verification | Rules for shared solved burglary, aliases, evaluation dates and contradictions | [verifier.py](phase2_verification/verifier.py) |
| Experiments | Two deterministic systems, runner, evaluator, schemas, configurations and saved outputs | [phase2_experiment/](phase2_experiment/) |
| Research documentation | Main report, dataset/corpus notices and the newly committed audit | [docs/](docs/), [research_audit/](research_audit/) |

We have enough infrastructure to extend the project. We do not need to rebuild retrieval, introduce a graph database, or create a new agent framework.

### Differences from the submitted proposal

The proposal is `Creators.pdf` in the parent directory. Treat these differences as scope decisions and pending work rather than reasons to restart.

| Proposal/intended behavior | Current implementation | Practical treatment |
| --- | --- | --- |
| Same base language model in the two arms | Both current systems use handwritten Python rules; there are no LLM calls, prompts or model configuration | Add a small matched LLM comparison by the checkpoint. Preserve current systems as engineering baselines. |
| Model forms a hypothesis and selects/calls verification | System B directly calls the deterministic verifier through Python | Add a bounded model hypothesis/tool-call/final-response path. The verifier itself can remain deterministic. |
| Optional one targeted re-retrieval | Disabled in [config.py](phase2_experiment/config.py); the loop is not implemented | Declare one initial retrieval for both checkpoint arms. Implement optional re-retrieval after October 30. |
| Communication and financial records | Existing evidence uses incident reports and CDRs; financial records are excluded | Use existing modalities for the checkpoint and explicitly disclose the scope change. Revisit final requirements before adding another modality. |
| Hidden evaluation labels and realistic distractors | Files are separated, but the full corpus contains explicit construction cues | Audit the active pilot now; repair a separately versioned larger corpus in parallel. |
| Verification-removal ablation on the same RAG model | Current A/B comparison changes the decision procedure as well as verification | Use the same model, evidence, task definition and final schema in both new arms. |
| Higher relationship F1 as a hypothesis | Historical full-set B has lower F1 than A | Report the tradeoff honestly. Favorable results are not a completion criterion. |

## 3. Current Technical Issues and What They Block

| Issue confirmed in this checkout | Why it matters | Priority for October 30 |
| --- | --- | --- |
| Full corpus has **40** reports containing `(Unlinked to <target ID>)`, all generated for negative cases | Reveals an explicit negative cue and also triggers the naive baseline's co-occurrence rule | Must be removed from any active experimental corpus containing these records. Does not occur in the included pilot. |
| Full corpus has **120** records explicitly marked `Distractor`, and **100** negative-case CDRs use `OID#EXTERN` | Gives models generation shortcuts instead of a fair evidence task | Audit active inputs; fix larger corpus separately. Do not claim that renaming the placeholder alone solves realism. |
| Verifier parses **0 of 40** full-test alias-resolution records | Generator wording such as `operates under moniker` does not match the parser | Repair and add regression examples in parallel with LLM integration. Check the pilot's actual alias chains before its runs. |
| Both alias records are already retrieved in **15/20** alias-positive and **16/20** mixed-positive cases | Retrieval alone cannot explain all 40 failures | Fix parser compatibility before treating re-retrieval as the main solution. These counts identify a concrete issue, not a complete case-by-case causal breakdown. |
| Missing-evidence positives have no primary qualifying report in the searchable corpus | CDRs alone cannot establish shared burglary under the current rules | Preserve `Insufficient Evidence`; do not lower the verifier standard or expect re-retrieval to recover absent records. |
| Full mixed-positive cases retain a primary alias-based report | The full condition does not combine all degradations as described in the proposal | Describe the checkpoint conditions accurately; validate a corrected final protocol later. |
| Only **5/200** saved queries retrieve designated distractors | A noise-heavy corpus is not necessarily a challenging retrieved context | Qualify robustness claims; review checkpoint retrieval examples. |
| Soundness scorer reuses System B's `HypothesisVerifier` | Perfect agreement with the same rules is not independent evidence validation | Add a small independent manual audit and label automated soundness accurately. |
| Runner/evaluator default to overwriting historical output files | A routine run can change frozen artifacts and hashes | Use explicit new run/report paths. The full evaluator also emits case comparisons absent from the frozen aggregate report. |
| `unsupported_decision_rate` counts an output status | This is different from unsupported positive assertions | Define both separately; do not use one as the other in the report. |

Sources: [full generator](phase2_corpus/generate_test_evidence.py), [verifier](phase2_verification/verifier.py), [runner](phase2_experiment/runner.py), [evaluator](phase2_experiment/evaluator.py), and the included corpus/output files.

### Important scope decision

The existing **10-case pilot has 31 evidence documents and none of the three explicit cues above** (`Unlinked to`, `Distractor`, `OID#EXTERN`). This does not certify the pilot as perfect, but makes it a practical starting point after manual review.

**Do not make the first LLM experiment wait for regeneration or repair of all 200 cases.** Audit the 31 pilot records, verify the expected evidence chains, and start there. Preserve the original 200-case corpus as a historical benchmark; larger corrections belong in a new version with their own provenance and hashes. Existing tests that freeze old hashes should not simply be rewritten to accept new data.

## 4. What Must Be Completed by October 30 Night

### A. A small working, reproducible pipeline

- [ ] Working environment with recorded dependency versions; save actual test results and skip reasons.
- [ ] Confirmed model access, exact model identifier, generation settings and budget. The repository currently specifies none of these.
- [ ] Audited active case set, searchable corpus, hidden labels and evidence-sufficiency expectations.
- [ ] LLM RAG-only baseline using the existing retriever.
- [ ] Same-model verification arm: model hypothesis, validated verifier call, tool result, final response.
- [ ] Structured decisions: `Supported`, `Unsupported`, or `Insufficient Evidence`, plus rationale and evidence IDs.
- [ ] Logs of initial retrieval, model responses, tool arguments/results, final outputs and failures.
- [ ] Separate output directory and manifest for each new experiment; scoring runs after inference.
- [ ] Model inputs limited to the pair, task instructions and approved evidence/tool responses. No labels, conditions, provenance, old predictions, reports or repository/filesystem access.
- [ ] Working reproduction instructions checked by another teammate.

### B. Actual baseline and ablation experiments

| Arm | Procedure | Role |
| --- | --- | --- |
| Existing deterministic A/B | Preserve historical outputs; rerun on active pilot if feasible without overwriting them | Engineering progress/reference |
| LLM RAG-only | Same model and initial evidence; final decision without verifier access | Required model baseline |
| LLM plus explicit verification | Same initial retrieval and common task instructions; model forms a hypothesis, invokes verification and uses the result | Main intervention |
| Verification removed | The LLM RAG-only arm above | Main ablation from the proposal; an additional experiment family is unnecessary |

**Minimum:** all 10 audited pilot cases in both LLM arms = **20 primary case-system executions**. A verification execution may involve more than one model call; report actual calls separately.

**Stretch target:** 40 audited development cases, 4 positive and 4 negative per condition, only if source access and generation are ready without delaying the minimum. The split manifest reserves a development pool, but no ready-made development evidence corpus is included. Do not take a convenient test subset and rename it development.

Freeze cases, prompts, model/settings, initial query policy and `top_k` before the reported comparison. Use the same evidence-sufficiency instructions and final schema in both arms. The baseline must not be instructed to make aggressive guesses. Record extra reasoning/model calls in the verification arm.

A 10-case experiment is preliminary progress, not a conclusive five-condition study. The course requirement lists evidence of progress, not a mandatory completed 200-case study at the checkpoint. Do not promise results or claim statistical significance from this pilot.

### C. Metrics and result artifacts

- [ ] Completed/failed runs and class/condition counts for each arm.
- [ ] TP, FP, TN, FN, precision, recall, F1 and accuracy against hidden relationship labels.
- [ ] Status counts and `Insufficient Evidence`/abstention rate.
- [ ] Citation validity, including whether citations were actually retrieved.
- [ ] Retrieval coverage against available support records; distinguish withheld evidence from retrieval misses.
- [ ] Valid tool-call rate and rejected/unapproved-call counts, with explicit denominators; malformed arguments and rejected calls are retained in the logs.
- [ ] Independent manual assessment of positive assertions and selected abstentions. For a 10-case pilot, review all 20 final responses if feasible; disclose the sample if fewer are reviewed.
- [ ] Actual calls, tokens/cost or local runtime where available.
- [ ] Per-condition results plus representative correct, incorrect and insufficient-evidence examples.

Binary scoring convention: only `Supported` maps to positive. State that mapping; it is not three-way evidence-status accuracy. Report three-way accuracy only if an independently checked reference status exists.

Define unsupported assertion rate as unsupported positive claims / reviewed positive claims, report numerator and denominator, and separate indeterminate claims. It is not the frequency of the `Unsupported` response status. If a denominator is zero, report N/A.

### D. The nine required submission items

| Course requirement | Concrete content to deliver | Owner |
| --- | --- | --- |
| **1. Progress completed** | Working modules and changes, repository paths, test evidence; completed versus pending features | Member 4 collects from all |
| **2. Datasets being used** | Backbone attribution, synthetic-evidence declaration, exact active files/version, counts, conditions, split and leakage review | Member 2 |
| **3. Baseline experiments** | Same-model RAG-only procedure, prompts/settings and saved outputs; historical heuristics clearly labeled | You |
| **4. Ablations** | Verification-removal comparison; list what was held constant and differences in calls | You + Member 3 |
| **5. Results from experiments run** | Tables generated from real saved outputs, confusion counts, failures and audit sample size | Member 3 |
| **6. Challenges faced** | Observed issues and concrete examples, including setup/source access, parser compatibility and evidence limitations | All; Member 4 assembles |
| **7. Mitigation plans** | What was fixed, what remains, owner and next action; no unmeasured improvement claims | All; Member 4 assembles |
| **8. Final-submission timeline** | Dates and deliverables through November 15, including final experiments and reproduction | Member 4 |
| **9. Updated GitHub with all code** | Integrated implementation, prompts/configs, setup/tests, scoring/reproduction commands, appropriate results and submission commit | You integrate; Member 4 checks access |

Do not submit only the existing audit PDF as the checkpoint: it is supporting evidence, not the complete nine-item progress package. Avoid reproducing its stale working-tree/latest-commit statements as current facts.

## 5. Four-Person Division With Clear Ownership

Names can be assigned to these roles; the user's identity among the proposal authors is not assumed.

| Person | Primary responsibility | Owned area | Handoff by checkpoint |
| --- | --- | --- | --- |
| **You: model integration and experiments** | Model adapter, common task/output contract, baseline, verification arm, traces, batch execution and integration | New model/prompt files; experiment systems, runner and config as needed | Working two-arm LLM pipeline, complete run artifacts, reproducible invocation |
| **Member 2: data and evidence audit** | Manually review pilot, check labels against included metadata, define evidence expectations, review conditions and construction cues; larger corpus corrections in parallel | Corpus generation/data-version assets, dataset card and vault-generation assets where required | Accepted pilot files/hash manifest and audit notes; development expansion only if feasible |
| **Member 3: verifier and scoring** | Alias compatibility, relevant regression checks, generic scoring, metric definitions and error analysis | Verifier, evaluator and their tests | Compatible verification API, metric tables, reference-status checks and limitations |
| **Member 4: reproducibility and submission** | Setup on another environment, capture test/dependency evidence, assemble report/timeline, independent sample review and repository access check | Setup/environment record, README and checkpoint report | Second-environment reproduction record and complete submission package |

### Interfaces to agree before splitting

1. **Public evidence:** existing document IDs/types/text and retrieval scores; hidden metadata stays separate.
2. **Model output:** target pair, status, rationale and evidence IDs; preserve raw response and parsing failures.
3. **Verification:** two canonical entity IDs plus nonempty unique retrieved evidence IDs; structured status, findings and rationale returned.
4. **Run identity:** dataset/corpus version and hashes, exact model/settings, prompt version, source commit, timestamps and output location.
5. **Scoring:** Member 3 reads saved outputs after inference and joins hidden labels by pair; model inference never reads labels.

You own experiment-schema changes after agreeing them with Member 3. Member 2 owns evidence-schema changes after agreement with Member 3. One owner edits each shared file; other members send small coordinated changes instead of editing it simultaneously.

Use a branch per workstream and integrate small commits. Keep credentials out of Git. Verify course-evaluator access without assuming the repository should be made public. Preserve hidden-input separation even if authorized evaluators can read the labels in the repository.

## 6. Correct Order and What Can Run in Parallel

| Stage | Work and dependency | Work that can proceed in parallel | Done when |
| --- | --- | --- | --- |
| **0. Agree the experiment** | Confirm model access/budget, 10-case minimum, shared evidence rules, formats and owners | Member 4 starts environment setup immediately | Everyone implements the same task and interface |
| **1. Prepare active evidence and model paths** | Pilot audit and model access are prerequisites for reported model runs | You build adapter/baseline; Member 2 reviews 31 pilot documents; Member 3 checks alias fixtures and scorer; Member 4 prepares setup/report | Pilot accepted, environment works, both paths can execute |
| **2. Integrate and smoke-test** | Accepted pilot plus working adapter and compatible verifier | Larger corpus repair continues independently; report methodology is drafted | Direct positive, alias positive, negative and missing-evidence examples produce valid outputs/traces |
| **3. Freeze the pilot experiment** | Fix blocking smoke failures; agree scoring definitions | Member 2 records hashes; you freeze prompts/settings; Member 4 records source commit/procedure | Exact inputs/settings fixed; new output paths selected |
| **4. Execute, score and review** | Stage 3 must precede reported runs | You run; Member 3 scores completed artifacts; Members 2/4 independently inspect evidence and final responses | Both arms complete; failures and metrics retained; manual review recorded |
| **5. Reproduce and submit** | Actual scored outputs available | Member 4 reproduces/assembles; Member 3 verifies tables; Member 2 checks dataset claims; you integrate code | All nine requirements and repository access verified |

**Critical path:** working environment/model access -> accepted pilot and verifier -> frozen two-arm run -> saved outputs -> scoring/review -> submission.

**Not on the minimum checkpoint critical path:** downloading the raw graph, generating a 40-case development corpus, correcting/regenerating the full 200-case benchmark, optional re-retrieval, financial evidence and interface work.

### Your implementation order

1. Confirm one usable model and define the common structured output with Member 3.
2. Add the smallest adapter needed; record the exact model/settings and bound retries/output length.
3. Implement baseline retrieval -> model decision/citations using existing retrieval.
4. Implement model hypothesis -> validated `verify_hypothesis` call -> final response. Reject IDs outside the case's retrieved evidence; keep rejection traces.
5. Save raw model responses, tool traces, usage and errors in a separate run directory.
6. Integrate the accepted pilot/verifier; complete the four smoke examples before batch execution.
7. Freeze settings, execute both arms on all selected cases, and hand outputs to Member 3.
8. Hand the invocation and commit to Member 4 for reproduction; integrate reviewed work for submission.

If the pipeline uses controller-enforced rather than model-selected tool invocation, disclose that narrower capability and do not report it as measured model tool-selection performance.

## 7. October 28-30 Schedule and Scope Gates

All times are IST. Internal targets below are not the official course cutoff; verify that cutoff separately.

| Time | You | Member 2 | Member 3 | Member 4 | Team deliverable |
| --- | --- | --- | --- | --- | --- |
| **October 28: first working block** | Confirm model access; agree output contract; start adapter | Review pilot evidence/conditions | Confirm alias mismatch; review API/scoring | Setup and run existing tests; prepare report outline | Prerequisites and contracts agreed |
| **October 28: remaining blocks** | One baseline and verification execution with full logs | Deliver audited pilot and expected evidence notes | Alias regression checks; pilot scoring support | Record environment/test results; draft progress/dataset/challenges | Integrated small working pipeline |
| **October 29: first working block** | Complete smoke checks and freeze settings | Freeze active pilot hashes; decide if expansion is ready | Validate scoring and reference-status sample | Follow reproduction procedure | Freeze 10 cases unless 40 are already ready |
| **October 29: remaining blocks** | Execute both arms and save complete outputs | Evidence review; larger fixes if time remains | Score and classify errors | Independent review; populate report with measured results | Baseline, ablation and real result tables |
| **October 30: first working block** | Resolve blocking issues only; version necessary reruns | Final dataset/limitations statement | Check metrics against raw files | Second-environment verification; complete nine-item report | Submission candidate ready |
| **October 30: afternoon** | Integrate reviewed code; identify submission commit | Verify data claims | Verify tables and metric definitions | Verify all requirements, links and access | Content/code freeze |
| **October 30: night** | Help submit and verify package | Final review | Final review | Assemble/upload with coordinator | Submit before official cutoff with buffer |

Aim for readiness by **20:00 IST on October 30**, earlier if required by the actual deadline. Do not reserve the last night for model integration or the first experiment.

### If something slips

- **Development expansion is not ready at the October 29 freeze:** run the audited 10-case pilot; state its small sample size. No rushed 200-case run is required for the minimum.
- **Raw graph is unavailable:** use included pilot artifacts, disclose that source regeneration is unverified, and avoid claiming source-label revalidation.
- **Model access is blocked:** make access resolution the first task. If it remains blocked, submit honest corrected deterministic progress and mark LLM work incomplete; this is a weaker fallback, not an equivalent completion.
- **API/format/tool call fails:** apply a declared bounded retry policy to both arms; retain failed attempts and report coverage. Do not silently discard cases or manufacture decisions.
- **Verification reduces F1:** report the result with precision, recall, abstention and evidence support. Do not change rules until the result becomes favorable.
- **Data or prompts change after freeze:** retain the old run, create a new version and run the affected matched comparison. Do not combine incompatible results into one table.

## 8. Historical Results to Include as Existing Progress

These values were freshly recomputed from the saved predictions and stored labels during this review. They remain results from deterministic systems, not the planned LLM arms.

| Dataset | System | TP | FP | TN | FN | Precision | Recall | F1 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pilot, 10 cases | Existing A | 5 | 2 | 3 | 0 | 0.7143 | 1.0000 | 0.8333 | 0.8000 |
| Pilot, 10 cases | Existing B | 4 | 0 | 5 | 1 | 1.0000 | 0.8000 | 0.8889 | 0.9000 |
| Full, 200 cases | Existing A | 100 | 60 | 40 | 0 | 0.6250 | 1.0000 | 0.7692 | 0.7000 |
| Full, 200 cases | Existing B | 40 | 0 | 100 | 60 | 1.0000 | 0.4000 | 0.5714 | 0.7000 |

See [saved outputs](phase2_experiment/outputs/) and the [new audit record](research_audit/audit_results.json). Historical soundness is reported as 11.25% versus 100% by the existing scoring report; distinguish that rule-based score from independent manual review.

Neither stored full-set arm returns `Unsupported`; both use `Supported` and `Insufficient Evidence`. There are 85 target entities reused across cases, so split isolation should not be described as independence of every evaluation observation. The unchanged frozen test has already been inspected; do not call it an untouched blind evaluation.

## 9. Final-Submission Timeline: October 31-November 15

| Dates | Work and deliverable |
| --- | --- |
| **October 31-November 2** | Close checkpoint gaps, agree final modality/condition scope, prepare a corrected benchmark version and development evidence, verify source access and label provenance where possible |
| **November 3-5** | Add at most one targeted re-retrieval for unresolved available evidence; validate stopping, argument checks and tool budgets on development cases |
| **November 6-8** | Finish development-only tuning; freeze dataset, prompts, model/settings and evaluator; decide repeat runs according to budget |
| **November 9-11** | Run the 200-case matched study and verification-removal ablation; retain failure/cost logs. Keep a fixed-evidence comparison to isolate verification if another variant receives extra retrieval |
| **November 12-13** | Independent evidence review, condition-level failure analysis and reproduction by another teammate |
| **November 14** | Finish final report, demo and repository/artifact access checks |
| **November 15** | Submit final package with an upload buffer; no extension assumed |
| **November 16-19** | Evaluation demonstrations and questions, using submitted results |

Keep historical data/results intact and distinguish corrected versions. Disclose prior test-set inspection, and do not tune against its scores. A novel holdout requires an appropriate unused pool and a documented generation protocol; a new filename alone does not create one.

Defer a UI, graph database, dense-retrieval infrastructure, fine-tuning, multiple model families and multi-agent architecture. Add financial evidence only if needed for the agreed final scope and the core experiment is already reliable.

## 10. Immediate Next Action and Completion Definition

**Start with three parallel tasks:** you confirm model access and begin the adapter; Member 2 audits all 31 pilot records; Member 3 checks the pilot alias/evidence examples and scoring. Member 4 establishes the environment and report outline in parallel. Integrate once the pilot and interfaces are accepted. Larger full-benchmark repairs must not block that integration.

The checkpoint is ready when it contains implemented progress, an identified dataset, a real model baseline and verification-removal ablation, saved results from completed runs, observed challenges and mitigations, a dated final timeline, and an accessible GitHub commit containing the implementation and reproduction procedure. Pending experiments must remain labeled as pending.
