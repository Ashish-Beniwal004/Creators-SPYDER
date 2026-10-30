# October 30 evidence review: assistant-assisted, not human adjudication

Review scope: all ten saved retrieval packets and all twenty original Groq outputs
in `groq_checkpoint_20261030/evidence_review/`, checked against the native run.
No new model API calls were made. This review used the evidence and model answers;
it was not blinded, independent human review. No values from this document were
inserted into the scorer's human-review CSV or human-derived metrics.

All output citations belong to the corresponding saved retrieval. Citation validity
is a structural check, not proof that every sentence of a rationale is justified.
Both arms made identical final decisions, but their citations/rationales differ.

## Case findings

Pair numbering follows the run's zero-based case index plus one. A is RAG only;
B is RAG with the verifier. Original outputs and evidence remain unchanged.

| Pair | A / B decisions | Evidence-based assessment and caveats |
|---|---|---|
| 01 | Supported / Supported | Both cite `DOC_IR_68ca5aaf`: both targets are apprehended after the burglary with matching stolen property. The central joint-participation assertion follows from this report under the benchmark's operational status rule. |
| 02 | Insufficient / Insufficient | The two reports concern different participant pairs; neither establishes the target pair's joint offending. Abstention is reasonable. B calls both cases solved; this relies on the benchmark's identification/apprehension proxy rather than a formal closure record. |
| 03 | Supported / Supported | `DOC_IR_c1c7b4bb` explicitly maps The Wire to the target identity; `DOC_IR_71acf05c` records the other target with The Wire in the burglary. The identity chain is present in both citation sets. One participant escaped; describe the benchmark's solved-status proxy rather than claim judicial resolution. |
| 04 | Insufficient / Insufficient | The Wire maps to one target; the burglary names the other target with The Spark. No supplied document equates Spark with Wire or the first target. Do not invent an alias resolution. |
| 05 | Insufficient / Insufficient | All three retrieved records are phone communications. They do not establish a joint burglary. This is the shared binary false negative, but the abstention is consistent with the accessible evidence. Hidden truth must not be used to invent a missing identity link. |
| 06 | Insufficient / Insufficient | The incident concerns a lone target scouting a perimeter, with no entry achieved; the CDRs link the other target to somebody else. Neither a completed joint burglary nor full-window exclusion is established. A's phrase "that burglary" is imprecise: the source describes scouting/no entry. B preserves the attempt qualification. |
| 07 | Supported / Supported | `DOC_IR_eb659cb3` links both targets to detention with stolen equipment; this supports joint participation under the benchmark rule. B additionally says the CDR corroborates interaction "at the same time". The call is at 01:30:25 and incident at 02:50:00, about 80 minutes apart. That timing claim is overstated; the incident report supports the central verdict without it. |
| 08 | Insufficient / Insufficient | The reports show the targets with different partners on different dates. No joint target-pair incident or alias chain is supplied. The CDRs do not bridge that gap. The benchmark's solved-status wording remains a proxy, not independent official clearance verification. |
| 09 | Supported / Supported | `DOC_IR_80e4d5d3` maps The Locksmith to one target; `DOC_IR_bf7db53a` names the other target with that alias in the burglary. Both outputs cite both documents. The report identifies participants but has no explicit case-closure disposition; the word solved uses the existing benchmark convention. |
| 10 | Insufficient / Insufficient | The Driver is unidentified; no document links that alias to the other target. The first incident is explicitly an attempted burglary. Both rationales describe it as a burglary without preserving the attempt qualifier. The final abstention remains appropriate; the rationale wording should be flagged. |

## Interpretation for the checkpoint

- The evidence review supports treating the identical binary results as a
  feasibility finding, not demonstrated verification improvement.
- Zero binary false positives does not mean zero unsupported narrative details.
  The timing overstatement and attempt/completion imprecision are concrete examples.
- The verifier accepts arrest/detention or positive perpetrator identification as
  operational solved-status cues (`determine_solved_status` in
  `phase2_verification/verifier.py`). These are not proof of formal case closure,
  conviction or legal guilt. The final phase should make this convention explicit
  in dataset references and prompts, or adopt a separately versioned stricter
  task. Do not change this completed run's task or outputs retrospectively.
- Missing identity evidence is an intentional difficulty in this development
  corpus. Cases 04/10 must stay unresolved unless new versioned evidence supplies
  the missing mapping. Case 05's incident report is anonymous, not a usable joint
  identity link; increasing retrieval alone does not establish that missing link.
- Some retrieved documents recur across pairs. The corpus is synthetic and has
  been inspected during development; do not claim independent held-out accuracy.

## Remaining independent review

The twenty human-review CSV rows remain blank. If a real person completes review,
record their identity and actual ratings, then import a copy using
`--manual-review` into a new score directory. Leave the original run/report intact.
Until then report human unsupported-assertion rate and human three-way accuracy
as **not measured**, not zero and not inferred from this assistant review.
