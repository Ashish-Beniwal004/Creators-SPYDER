# Member 2 — Pilot Evidence Audit

## 1. Purpose and scope

This read-only audit inspected the existing 10-case pilot corpus, its schemas, manifests, retrieval/verifier path, and recorded pilot run artifacts. It did not access the original police dataset, run tests, or regenerate data. Ground-truth labels and hidden rationales are intentionally not reproduced here.

## 2. Branch and audit date

- Branch: `member-2/pilot-evidence-audit`
- Audit date: 2026-10-28

## 3. Files and data roles inspected

- Model-facing inputs: `phase2_experiment/pilot_target_pairs.json` (unlabelled pairs) and `phase2_corpus/retrieval_documents.jsonl` (sanitized evidence).
- Hidden audit material: `phase2_ground_truth_vault/pilot_manifest.json`, `phase2_ground_truth_vault/ground_truth.json`, `phase2_ground_truth_vault/split_manifest.json`, and `phase2_corpus/internal_provenance.jsonl`. These hold case assignments, labels, conditions, source references, or generation metadata and must not enter model/retriever input.
- Recorded artifacts: `phase2_experiment/outputs/pilot_run_manifest.json`, `system_a_pilot_outputs.json`, `system_b_pilot_outputs.json`, and `pilot_scoring_report.json`.
- Supporting implementation and documentation: `phase2_experiment/config.py`, `runner.py`, `system_a.py`, `system_b.py`, `phase2_retrieval/retriever.py`, `phase2_verification/verifier.py`, `phase2_ground_truth_vault/schemas.py`, `phase2_ground_truth_vault/README.md`, `phase2_corpus/CORPUS_CARD.md`, and `phase2_corpus/generate_pilot_evidence.py`.

The normal runner selects the target-pair file and sanitized corpus. The retriever indexes `text_content` only. This is a code-path separation, not a filesystem-level security boundary.

## 4. Verified counts and schema checks

The pilot contains **10 cases**, **31 retrieval documents** (20 `incident_report`, 11 `call_detail_record`) and **31 provenance records**. Per-case evidence counts:

| Case | Incident reports | CDRs | Verifier result on case evidence |
|---|---:|---:|---|
| PILOT_CASE_01 | 1 | 2 | Supported |
| PILOT_CASE_02 | 1 | 1 | Insufficient Evidence |
| PILOT_CASE_03 | 2 | 1 | Supported |
| PILOT_CASE_04 | 1 | 1 | Insufficient Evidence |
| PILOT_CASE_05 | 1 | 3 | Insufficient Evidence |
| PILOT_CASE_06 | 1 | 0 | Insufficient Evidence |
| PILOT_CASE_07 | 4 | 1 | Supported |
| PILOT_CASE_08 | 2 | 1 | Insufficient Evidence |
| PILOT_CASE_09 | 4 | 1 | Supported |
| PILOT_CASE_10 | 3 | 0 | Insufficient Evidence |

All 31 retrieval documents passed `SanitizedRetrievalDocument` validation; all 31 provenance records passed `EvidenceProvenanceEnvelope` validation. No duplicate document/provenance IDs, unmatched document-to-provenance references, unexpected provenance case IDs, or schema errors were found. The manifest, target-pair file, and vault each contain 10 cases; their case and pair sets agree. Pilot target entities were found in the pilot partition.

Verifier results summarize evidence handling, not ground-truth labels. CDR contact alone was not treated as sufficient evidence.

## 5. Construction-cue search and limitations

Searches of the model-facing pilot evidence found **zero** occurrences of `Unlinked to`, `Distractor`, and `OID#EXTERN`. Searches also found no explicit ground-truth/label strings, pilot case IDs, condition names, or the schema’s listed artificial-negative phrases.

Other wording detected:

- `false alarm`: once, `DOC_IR_2647291e` in `phase2_corpus/retrieval_documents.jsonl`, line 17.
- `Unidentified`/`unidentified`: 7 occurrences in 6 documents: `DOC_IR_68652ed0` (line 13), `DOC_IR_2647291e` (line 17), `DOC_IR_b2f0efab` (line 22, twice), `DOC_IR_eaaffe3f` (line 25), `DOC_IR_c40e284d` (line 26), and `DOC_IR_2a68fdcb` (line 27).

These are descriptions of evidence or unknown actors, not explicit answer labels. They may nevertheless act as evidence-quality or construction cues. The search covered the listed phrases and selected schema-related terms; it is not an exhaustive semantic leakage assessment.

## 6. Case-level evidence sufficiency and aliases

Using the configured top-five retrieval and current verifier, the evidence supported the hypothesis in cases 01, 03, 07, and 09. The verifier returned insufficient evidence in cases 02, 04, 05, 06, 08, and 10. These outcomes do not establish benchmark correctness.

- Cases 03 and 09 contain alias mappings expressed in forms recognized by the current verifier, and the verifier supported them using incident evidence.
- Case 04 contains “The Spark” in the evidence but no case-specific canonical identity resolution; the verifier returned insufficient evidence.
- Case 10 refers to “The Driver” as unidentified and the incident describes an attempted burglary; no canonical identity mapping was found and the verifier returned insufficient evidence.
- For cases 01 and 07, support comes from incident evidence; phone contact alone would not satisfy the documented verification rule.
- The remaining cases did not establish joint, solved-burglary participation from the evidence available to the verifier.

Cases 04 and 10 are **unresolved evidence-design concerns**, not confirmed dataset defects. Team review is needed to determine whether the gaps are intentional or inconsistent with the intended pilot design.

## 7. Hash and artifact integrity

Read-only SHA-256 comparisons found all declared entries matching:

- `phase2_artifact_hash_manifest.json`: 15/15 entries.
- `phase2_public_artifact_hash_manifest.json`: 6/6 entries.
- `pilot_run_manifest.json`: recorded corpus and target-pair hashes match current files; both recorded System A/B output hashes match their files.

The pilot corpus hash is `a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded`. Methods used: Python `hashlib.sha256` over manifest paths and run-manifest paths; JSON/JSONL parsing and schema validation. No manifests were edited.

## 8. Model-input and hidden-metadata separation

The retrieval records have only the expected document fields (`doc_id`, `doc_type`, `timestamp`, `text_content`, `metadata`); observed metadata keys are `date`, `incident_id`, and `sector`. The inspected runner and retrieval code use target pairs and the sanitized corpus, and the retriever indexes `text_content`; the normal inference path inspected does not load the vault or internal provenance. These checks do not prove protection against arbitrary repository access by a model or tool.

## 9. Release-boundary concern: internal provenance

`phase2_public_artifact_hash_manifest.json` lists `phase2_corpus/internal_provenance.jsonl` as a public frozen artifact, while the schema and documentation designate that file internal/audit-only. The provenance schema contains case assignments, target pairs, conditions, source references, and generation rules. This is a confirmed manifest/documentation boundary inconsistency. Whether the file is intended for a public release requires a team decision; no raw provenance contents are included here.

## 10. Prioritized recommendations and decisions required

1. **Decide the provenance release policy.** Confirm whether internal provenance may be distributed; align the release manifest and documentation in a later approved change.
2. **Review alias cases 04 and 10.** Decide whether unresolved aliases are intentional insufficiency or a gap against the intended pilot evidence design. Do not equate alias co-occurrence with identity proof.
3. **Review cue wording.** Decide whether “false alarm” and “unidentified” are acceptable evidence content or unintended condition cues; preserve factual evidence descriptions.
4. **Retain and extend separation checks.** Ensure future runner/index paths use only unlabelled targets and sanitized evidence, and assess tool access separately from code-path checks.

## 11. Change statement

No existing project artifacts were intentionally changed during this audit. No tests, generation commands, commit, or push were performed. The audit was read-only with respect to corpus, ground truth, provenance, manifests, outputs, and source code.
