# October 30 checkpoint: data and evaluation scope

This checkpoint is an inspectable synthetic development-pilot experiment. It is
not a new blinded public benchmark release. The existing repository includes
evaluation material; labels being inspectable by developers is distinct from
labels being supplied to the model. Development exposure must be disclosed.

## Inference boundary

Inference uses unlabelled target pairs and sanitized incident/CDR documents.
The LLM adapter forwards only the target, query and explicit public evidence
fields. It receives no label, case condition, factual rationale or generation
provenance. The verifier uses supplied evidence IDs; labels are not a tool input.
Tests cover this implemented path. This is not an operating-system security sandbox
against arbitrary unrelated code reading repository files.

Hidden manifests and internal provenance are used only for post-execution scoring
and dataset audits. They must not be copied into prompts or attached to evidence
review packets. The selected Groq results bundle contains neither raw label files
nor raw generation provenance. It does contain synthetic case outputs, supplied
evidence and aggregate condition scores to make this development run inspectable.

## Existing release-document inconsistency

`phase2_public_artifact_hash_manifest.json` lists internal provenance among public
artifacts, while other documentation calls it audit-only. This remains a legacy
release-description inconsistency. It is recorded by Member 2's audit; the frozen
manifest and data were not silently rewritten to conceal it.

For this checkpoint, make no claim that the repository is label-free or blinded.
The selected new results bundle excludes new copies of raw hidden scoring inputs.
Before any separate blinded/public benchmark release, the team must decide its
distribution policy and create a distinct versioned export with matching metadata.
Changing ignore rules does not erase material already tracked in Git history.

## Source data and interpretation

The upstream source graph is absent locally and its redistribution permission is
unverified. It remains excluded; no source download or regeneration was performed.
Four raw-source checks are skipped, so independent regeneration is unverified.

The full corpus has known construction cues; the checkpoint uses the audited
31-document/ten-pair pilot. Aliases without evidence remain unresolved. Missing
identity attribution and unknown participants are evidence limitations, not a
license to infer identities from hidden labels. Existing text and hashes remain
unchanged. No broad external-validity or real-world operational claim is made.
