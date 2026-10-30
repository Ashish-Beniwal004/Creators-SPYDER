# Scoring new LLM runs

`score_run.py` consumes the native artifacts produced by `phase3_llm.runner` on the
Member 1 branch. It runs **after inference**, with explicit access to hidden labels.
Do not import it into the model, retrieval, or verification path.

## Inputs and command

Once the Member 1 and Member 3 changes are integrated, run this from the repository
root in PowerShell. Replace `REVIEWED_RUN` with the actual saved corpus-run folder.
The scoring destination must not already exist.

```powershell
.venv/Scripts/python.exe -B -m phase2_experiment.score_run `
  --run-dir experiment_runs/REVIEWED_RUN `
  --pairs phase2_experiment/pilot_target_pairs.json `
  --corpus phase2_corpus/retrieval_documents.jsonl `
  --labels phase2_ground_truth_vault/pilot_manifest.json `
  --provenance phase2_corpus/internal_provenance.jsonl `
  --output-dir experiment_runs/REVIEWED_RUN_scores
```

`--provenance` is optional; without it retrieval relevance diagnostics are omitted.
For a full-corpus run use its corresponding pairs, corpus, labels and provenance.
The exact target cohort and ordering, pair-file hash and corpus hash must match
the run. A subset smoke run needs a matching subset pairs file and label manifest
prepared separately for post-execution scoring. Never put labels in its pairs file.
The standalone fictional runner fixtures have no benchmark corpus/label join and
are not accepted as benchmark results.

The scorer verifies run artifact hashes, shared retrieved evidence and scores,
pair/arm/index consistency, citations, execution counts and basic trace counts.
It rejects duplicates, mismatched datasets, verdicts attached to failures, citations
outside retrieved evidence and supported assertions without citations. Hashes detect
changes relative to the saved manifest; they are not a signature or proof against
someone rewriting both artifacts and the manifest.

## Outputs and interpretation

- `report.json`: coverage and failures, completed-case binary metrics, per-condition
  metrics, paired completed-case metrics, decision/abstention counts, tool-call counts,
  provider-reported usage, optional retrieval diagnostics and manual-review summaries.
- `review_template.csv`: completed outputs with citations, retrieved IDs and rationale,
  with **blank** review columns. It contains no hidden labels.

Binary scoring maps `Supported` to 1 and both other verdicts to 0. It measures
documented co-offending prediction. It does not show whether abstaining was justified
by the evidence available to the model. A positive hidden label can legitimately
have insufficient retrieved evidence. Failures and missing results are never
converted to decisions; they are excluded from decision metrics and counted in
coverage. Compare arms on `paired_completed_binary_metrics` when coverage differs.
No observations yields null metrics. F1 is zero when errors exist and true positives
are zero; it is undefined when `2TP + FP + FN = 0`.

`verifier_consistency_on_positive_citations` reuses the deterministic verifier. This
is a consistency diagnostic, **not independent evidentiary validation**. It may share
the verifier's errors. The scorer does not infer a human unsupported-assertion rate.
Likewise generation-rule retrieval relevance is a synthetic-corpus diagnostic;
documents withheld from the corpus are excluded from recall denominators and
reported separately. It reports the actual configured top-k, not an assumed k=5.

API usage includes failed calls when the provider returned usage before failure.
Missing provider usage cannot be reconstructed. Tokens are not converted into cost.
Requested tool calls without an accepted-call event count as unaccepted, including
multiple calls in a response or a call in the baseline arm. A missing required tool
call produces an execution failure, even though it contributes no requested calls.

## Independent human review

Give the generated CSV and the exact sanitized corpus to a teammate who did not
write the verdicts. Review all 20 pilot outputs if feasible. Reviewers must read
the retrieved/cited text; do not copy verifier judgments into review fields.

1. `reference_status`: `Supported`, `Unsupported`, or `Insufficient Evidence`, based
   on **all retrieved evidence**, independent of the hidden binary label.
2. `support_assessment`: `supported`, `unsupported`, or `indeterminate`, judging
   whether a **positive model assertion** follows from its cited documents.
3. `reviewer`: reviewer identifier; `notes`: short evidence-based reason. Leave
   unreviewed fields blank. Keep model fields unchanged.

Pass the completed CSV using `--manual-review PATH` and choose a **new** scoring
directory. Unsupported-assertion rate uses decisively reviewed positives only;
indeterminate counts and review coverage remain explicit. Three-way accuracy uses
only outputs with manual reference statuses. This import records reviewer statements;
independence and reviewer quality still require the team's actual review process.

Review outputs and notes before publishing: do not automatically publish hidden
manifests, provenance, case-level scores or provider traces. Run directories are
ignored locally; select the approved reproducibility bundle explicitly for GitHub.

## Existing deterministic evaluator

`python -m phase2_experiment.evaluator --dataset pilot` now returns/prints a report
without writing a file. An explicit `--output NEW_FILE` writes with exclusive create;
an existing report causes an error. The Python evaluation functions likewise write
only when `report_output_file` is provided. Historical reports remain unchanged.
The old runner still defaults to historical output locations; use the Member 1
runner for LLM runs, and pass an explicit fresh `outputs_dir` for legacy diagnostics.

Historical advanced metric field names are retained for compatibility. New reports
should use the definitions in `score_run.py`, especially for verifier consistency
versus human evidence review. Repeated entities and development exposure make
independent-case significance/generalization claims inappropriate without a fresh
evaluation design.

## Verification

```powershell
.venv/Scripts/python.exe -B -m pytest phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests phase2_ground_truth_vault/tests -q -p no:cacheprovider
```

This runs locally without API access. Raw-source regeneration checks skip when the
excluded upstream dataset is unavailable. `research_audit/member3_environment.txt`
records the exact environment used for the Member 3 validation; existing broad
dependency requirements are unchanged.
