# Human evidence review handoff

These packets are generated only after both arms finish a pair, from the exact
saved retrieval and model outputs. They contain no hidden labels or generation
provenance. Existing packets are never overwritten, so reviewers may add notes.
Packets are authoring aids; they are not completed reviewer judgments.

Member 2: pairs 01-05. Member 3: pairs 06-10. Both arms need review for each pair.
Read all retrieved evidence and decide the three-way reference status before using
any model/verifier answer as evidence. For each positive model assertion, separately
judge whether its cited documents support it. Do not infer missing facts from an
OID, a phone link, the hidden label, or another case.

After the scorer finishes, enter actual ratings into a copy of
`../scores/review_template.csv`. Keep model fields unchanged. Valid values:

- reference_status: Supported / Unsupported / Insufficient Evidence
- support_assessment: supported / unsupported / indeterminate
- reviewer: actual reviewer identifier
- notes: brief evidence-based explanation

Unreviewed rows stay blank. The scorer can import partial review and will report
coverage. It will not invent ratings. See `phase2_experiment/SCORING.md` in the
repository for the `--manual-review` command. Use a new score destination; preserve
the original run and original unreviewed score report.
