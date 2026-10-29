# Member 3 implementation and handoff — October 29, 2026

## Branches and scope

Current local branch: `member-3/verifier-scoring`, based on Member 2's
`fd7c6653354fd4e6cbd59ca600760cebf4f3a7d7`. Member 2's audit, burglary-classification
fix and regression tests are inherited. Member 1's committed LLM work remains on
`feat/llm-integration-runner` at `6f35e83d447cf3040310ccd813e90f7aa9e3cd9c`.
No merge, commit or push was performed for Member 3. Changes await local review.

Member 2's changes are sufficient to develop against the frozen pilot: input
counts/hashes, provenance assignments and classification guards were checked.
Its report initially lacked a post-change test run; that gap is now closed by
the baseline run below. Source-data regeneration remains unverified locally.
An unresolved alias is not permission to invent an identity: pilot cases 04/10
retain their evidence limitations. Public distribution policy for internal
provenance still needs the team's decision.

## Completed changes

| Path | Change |
|---|---|
| `phase2_verification/verifier.py` | Recognizes explicit `operates under ... moniker` and single-entity verified interview subject attributions. Matches alias casing/spacing without changing display spelling. Preserves competing identity candidates and leaves conflicts unresolved across and within documents. Emits conflict findings. |
| `phase2_verification/tests/test_alias_grounding.py` | Tests affirmative versus unverified/negative subject attributions, multi-entity ambiguity, conflict/order behavior, absence of solved burglary support, and compatibility with all 40 existing full-corpus resolution records. |
| `phase2_experiment/score_run.py` | Scores native Member 1 JSONL runs with hash/cohort/output checks, failure coverage, per-condition/paired metrics, tool and usage accounting, optional provenance diagnostics and explicit human review import. |
| `phase2_experiment/tests/test_score_run.py` | Checks scoring boundaries, failure/missing handling, citation/context/hash rejection, no overwrite, human-review separation, usage/tool accounting, withheld evidence and F1 edge cases. |
| `phase2_experiment/evaluator.py` | Correct F1 denominator; explicit/exclusive report writes; summaries use computed counts instead of hardcoded historical assertions; significance assumption and same-verifier limitations clarified. |
| `phase2_experiment/SCORING.md` | Commands, metric definitions, manual-review procedure, artifact limitations and publication guidance. |
| `.gitignore` | Ignores local run folders using the same change already on Member 1. |

No corpus, targets, hidden labels, provenance or historical output/report was
edited. No new runtime dependency was added. Existing requirements were installed
in the isolated `.venv`; the exact tested versions are recorded separately.

## Checks actually run

- Member 2 baseline: **155 passed, 4 skipped** before Member 3 edits.
- Completed Member 3 suite: **177 passed, 4 skipped**. Four checks need the absent
  upstream raw dataset; these are not passes. Frozen artifact hash tests passed.
- Offline integration: loaded Member 1's committed Python package into a temporary
  directory without switching branches, using the current repository services.
  Ran the real pilot retrieval/verifier with scripted responses. **20/20 executions,
  30 scripted model calls, 10 paired cases**, zero API calls. Native scorer accepted
  the real runner's artifact format and reported `complete_experiment_run=false`.
  Verifier-guided scripted outputs were 4 Supported / 6 Insufficient Evidence.
- Fresh deterministic legacy diagnostics on pilot and full corpus, written only
  into new ignored run directories. Aggregates and source hashes are preserved in
  `research_audit/member3_deterministic_validation.json`.

| Diagnostic | A: TP / FP / TN / FN | B: TP / FP / TN / FN | B F1 |
|---|---|---|---|
| Pilot, 10 pairs | 5 / 2 / 3 / 0 | 4 / 0 / 5 / 1 | 0.8889 |
| Full corpus, 200 pairs | 100 / 60 / 40 / 0 | 71 / 0 / 100 / 29 | 0.8304 |

These are **deterministic development diagnostics, not LLM experiments**. A is the
existing heuristic, B the deterministic verifier workflow. Historical full B had
40 true positives; this rerun has 71 after fixing parsing of existing alias text.
Do not replace the frozen historical report or call this an independent held-out
improvement. Development has inspected these artifacts. Full-corpus lexical label
cues remain, as do withheld evidence, repeated entities and limited synthetic
language. No human adjudication was fabricated or completed by these checks.

Local bridge artifacts are in
`experiment_runs/member3_bridge_20261029T061911281307Z` and the adjacent `_scores`
folder. The local temporary bridge script is ignored under `scratch/`; the
permanent scoring tests and command documentation are tracked for review.

## What remains before October 30 night

1. **Review and commit Member 3 locally.** Nothing is pushed. Keep this branch as
   the reviewable Member 2 + Member 3 line of work.
2. **Return to Member 1 after that commit**, and merge the reviewed Member 3 branch
   locally into the integration branch. There is no verifier/scorer file overlap
   with Member 1; both branches add the same run-folder ignore entry. Run the
   combined suite, including `phase3_llm/tests`, and repeat offline integration.
3. **Set up actual model access.** An API key is still needed for real experiments.
   Store it locally in the environment. The provider adapter has not been tested
   against the live service. Check model availability, access limits and request
   format with a tiny smoke run before freezing an experiment configuration.
4. **Run the minimum pilot experiment:** same real model and initial top-5 evidence
   for all 10 target pairs in both arms, A without verifier and B with one verifier
   call. Nominal budget: 30 model requests, with no automatic retries. Save the
   config, complete traces, decisions, failures and hashes in a new run directory.
   This A/B comparison is the minimum verifier-removal ablation. Do not call the
   scripted pipeline an experiment. Any interrupted or failed run remains visible.
5. **Score and review:** run the new scorer only after inference; another teammate
   reviews all 20 pilot outputs with retrieved/cited evidence if feasible. Report
   binary metrics alongside evidence-level judgments, failures and coverage.
   A single 10-pair run supports a feasibility checkpoint, not a strong quality claim.
6. **Prepare the mid-submission:** actual progress and dataset versions/counts;
   deterministic baseline clearly separated from the live LLM comparison; ablation
   definition; actual tables with denominators; alias/parsing/API/evidence challenges
   and mitigations; limitations; and the final timeline below. Select the reviewed
   reproducibility bundle and code for the user's manual GitHub push. Hidden
   audit material and provider traces require publication review.

If model access fails, submit the actual deterministic progress and explain the
API blocker honestly. It does not satisfy a completed LLM experiment. Add another
ablation (such as lower retrieval k) only after the paired pilot and scoring are
working, while holding other settings fixed and reporting its evidence budget.

## Remaining ownership and order

- **Member 1 / us:** local integration, API smoke check, fixed model/config,
  paired live runner, failure triage and scoring execution.
- **Member 2:** can independently finalize corpus/version handoff and document
  unresolved pilot aliases/evidence limitations. Do not edit the frozen pilot
  while an experiment uses it.
- **Member 3:** implementation above is ready for review; after integration,
  support scorer/verifier regressions and manual-review protocol. An independent
  teammate, not the verifier author alone, should provide evidence judgments.
- **Member 4:** can prepare report structure, dataset description, challenges and
  final timeline now; insert actual experiment tables after scoring. Coordinate
  the 20-output evidence review with Member 2. Review/freeze the publication bundle
  after results are final.

API setup, report writing and Member 2 documentation can proceed in parallel with
code review. Live runs depend on integration + a passing smoke run. Scoring depends
on saved runs; evidence review and final tables depend on their outputs. Version
or prompt changes require a new identified run, not edits to saved results.

## October 31–November 15

- **Oct 31–Nov 2:** address checkpoint feedback, independent evidence adjudication
  and API reliability; design a fresh/versioned evaluation corpus without label
  cues and with clearly specified available-versus-withheld evidence.
- **Nov 3–7:** freeze the final evaluation protocol; run paired experiments and
  agreed ablations on the approved corpus, repeat where quotas permit, and log
  all attempted executions. Keep development exposure explicit.
- **Nov 8–11:** analyze errors by condition, review assertion support independently,
  quantify uncertainty appropriately for reused entities and document limitations.
  Extend retrieval only if these results justify it and enough rerun time remains.
- **Nov 12–14:** freeze code/results, reproduce from documented commands in a
  clean environment, finish report/demo and verify the reviewed GitHub contents.
- **Nov 15:** submit final artifacts; prepare Nov 16–19 evaluations. No feature
  should displace reproducibility or submission checks near the fixed deadline.
