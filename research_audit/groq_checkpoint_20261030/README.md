# Groq checkpoint reproducibility bundle - October 30, 2026

The real ten-pair pilot completed: 20/20 executions, 0 failures, 30 requests.
Both arms: TP=4, FP=0, TN=5, FN=1; accuracy=0.90, precision=1.00,
recall=0.80, F1=0.8889. Both made the same ten decisions. This pilot shows no
measured classification improvement from verification. B used 20 requests versus
A's 10, with the same initial evidence. No compute-matched claim is made.

Actual usage: 30,956 prompt + 11,635 completion = 42,591 tokens. Completion includes
7,941 reasoning tokens; do not add reasoning again. Smoke used 2,199 more tokens.
The first blocked smoke retains an 8k unknown-usage local reservation.

## Contents

- `groq_pilot_01/`: exact native config, manifest, retrieval, provider/tool traces,
  results, errors and compatible per-arm exports. Files are unchanged copies.
- `scores/report.json`: validated actual coverage, metrics, conditions and usage.
- `scores/review_template.csv`: 20 output rows with blank human-review fields.
- `evidence_review/`: ten packets with exact shared retrieved text and model answers.
- `source_manifest.json`: code hashes, pre-commit source state and runtime versions.
- `requirements-tested.txt`: exact installed runtime/test versions; no installation
  was performed to create this record.
- `bundle_sha256.json`: hashes of this bundle at handoff; verify before publication.

No key, hidden label file, generation provenance or quota ledger was copied here.
The run metadata captures the pre-commit working tree: its recorded base HEAD
alone does not contain the implementation. Code commit `9544f85` includes the
recorded source files; compare code hashes and use root `M4_HANDOFF.md` for final
branch/commit/push status. The full local source snapshot is retained under
`experiment_runs/groq_checkpoint_20261030/frozen_code`.

## Reproduce saved-output metrics - no API calls

Run from repository root with the existing environment. Choose a new destination.

```powershell
.venv/Scripts/python.exe -B -m phase2_experiment.score_run `
  --run-dir research_audit/groq_checkpoint_20261030/groq_pilot_01 `
  --pairs phase2_experiment/pilot_target_pairs.json `
  --corpus phase2_corpus/retrieval_documents.jsonl `
  --labels phase2_ground_truth_vault/pilot_manifest.json `
  --provenance phase2_corpus/internal_provenance.jsonl `
  --output-dir experiment_runs/groq_reproduced_REVIEW
```

This copied bundle was actually rescored and matched the original serialized
metrics and input hashes. No extra API generation was used for this reproduction.
Live commands are in `PILOT_RUNBOOK.md`. Sampling uses provider defaults with no
explicit seed/temperature, so fresh generations are not guaranteed to match.

## Review and interpretation

Another teammate must assess the evidence; no human ratings have been imported.
Use a copy of the CSV, retain model fields, fill real reviewer identifiers/ratings,
and rescore with `--manual-review` into a new directory. See
`phase2_experiment/SCORING.md` and `evidence_review/README.md`.

The missing-evidence positive has only phone-contact evidence in retrieval, so the
shared abstention counts as a binary false negative without proving a reasoning
failure. The anonymous incident report in the corpus does not identify the target
pair. Binary truth and evidence adequacy require separate interpretation. The
retrieval diagnostic's 100% recall covers only three generation-rule-eligible
pairs; it is not an exhaustive evidence audit. Verifier consistency is not an
independent human judgment.

This tiny synthetic development pilot has no demonstrated verification gain,
no repeat-run stability result and no broad generalization/significance claim.
Earlier Gemini outputs are separate. Local commits are being finalized; the user
reviews, pushes and submits. Final status is in root `M4_HANDOFF.md`.
Preserve native run files; if review documents change later, refresh the bundle's
hash index before publication and retain the original score report.
