# SPYDER Dataset and Provenance Notice

**Project:** Evidence-Grounded Agentic Criminal Network Investigation (SPYDER)<br>
**Document ID:** `DATASET_NOTICE.md`<br>
**Date:** October 2026<br>
**Status:** Permanent Provenance, Licensing, and Access Policy Document<br>

---

## 1. Overview and Scope

This notice documents the origin, licensing, transformation, and access policies for all empirical datasets, semi-synthetic evidence collections, and benchmark ground-truth artifacts utilized within the SPYDER project.

---

## 2. Source Datasets, Provenance, and Redistribution Terms

### 2.1 Primary Dataset Backbone: Israel National Police (INP) / ROXANNE
* **Title:** Israel National Police Burglary Offender and Crime Network (6-Month Evaluation Slice)
* **Citation:**<br>
  Zahra Ahmadi, Hoang H. Nguyen, Zijian Zhang, Dmytro Bozhkov, Daniel Kudenko, Maria Jofre, Francesco Calderoni, Noa Cohen, and Yosef Solewicz. *"Inductive and Transductive Link Prediction for Criminal Network Analysis."* **Journal of Computational Science**, Vol. 72, Article 102063, September 2023. DOI: [10.1016/j.jocs.2023.102063](https://doi.org/10.1016/j.jocs.2023.102063).
* **Affiliation:** European Union Horizon 2020 Research and Innovation Programme, Project ROXANNE (Grant Agreement No. 833635).
* **Upstream Source Repository:** [https://github.com/erichoang/criminal-network-visualization](https://github.com/erichoang/criminal-network-visualization)
* **Upstream Direct Data URL:** [https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json](https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json)
* **Dataset Characteristics and Expected Schema:**
  - Format: NetworkX node-link JSON serialization.
  - Nodes (1,658): Offender IDs (`OID#xxx`), 2D normalized spatial coordinates (`pos`), crime occurrence mappings (`crime_details`), incident list (`list_cid`), and Louvain community assignments (`community_id`).
  - Edges (1,728): Co-offending links between offender pairs with co-arrest frequency weights and timestamps.
  - File Size: 1,193,405 bytes.
  - Verified SHA-256 Checksum: `ba367e9123bfc7739c9f3bf686c39d00e733de8188e8471c608f4bf4eb679d84`.
* **Licensing and Redistribution Gate Finding:**
  - **Software License Distinction:** The upstream GitHub repository contains a BSD-3-Clause license (`LICENSE`). However, authoritative legal inspection confirms this license applies strictly to the visualization *software* source code, not to the underlying law-enforcement operational dataset.
  - **Redistribution Permission Unverified:** While the research paper describes that the Israel National Police anonymized the records under Israeli legal supervision and GDPR standards, neither the upstream repository, the ROXANNE project deliverables, nor the published manuscript contains an explicit authoritative statement granting third parties rights to redistribute or re-host the raw law-enforcement graph files.
  - **Public Release Exclusion Policy:** In accordance with strict licensing compliance, the raw graph dataset `israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json` is **excluded from this public Git repository release**.
  - **Impact on Public Clone:** The public clone includes the full sanitized semi-synthetic evidence corpus (`test_retrieval_documents.jsonl`), unlabelled target pairs, and pilot assets. Out-of-the-box public tests and verification run on these assets without requiring the raw police data. Benchmark ground-truth regeneration, however, requires authorized upstream data retrieval as documented below.

### 2.2 Excluded Historical Datasets (Phase 1 Audit Candidates)
During Phase 1, multiple candidate datasets were audited for domain relevance and degree calibration. The following datasets are **excluded** from the publication release because no Phase 2 pipeline component, retriever, verifier, or evaluation test depends on them:
* **Israel LEA Wiretap Speaker Networks (`case1_speakers.json`, `case2_speakers.json`):** Audited for degree calibration; excluded from release.
* **Moreno St. Louis Crime Network (`moreno_crime.json`):** 1990s homicide network audited for topological comparison; excluded from release.
* **Israel LEA 1-Month Slice (`...2020-01-01_to_2020-01-31.json`):** Redundant sub-slice; excluded in favor of the canonical 6-month backbone.
* **External Candidate Sources:** For historical reference, external sources audited during exploratory phases included:
  - Israel LEA Wiretap Networks: `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_case1_speakers.json`
  - Moreno St. Louis Crime Network: `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/moreno_crime.json`
  - Montagna Operation Sicilian Mafia Network: Cavallaro et al., PLOS ONE 2020, Zenodo DOI: 10.5281/zenodo.3943343.

---

## 3. Classification of Project Data Files

To maintain strict epistemic integrity, project data artifacts are classified into five operational categories:

| Category | Artifact Locations | Runtime Access Policy | Publication Status | Teammate Function |
| :--- | :--- | :---: | :---: | :--- |
| **1. Backbone Network** | Upstream external download (`israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json`) | Build-time only | **Excluded from Git** (External Upstream Download) | Canonical 6-month source network for benchmark generation. Must be downloaded from upstream prior to local benchmark regeneration. |
| **2. Public Searchable Corpus** | `phase2_corpus/test_retrieval_documents.jsonl` | **Public Searchable** | **Included** | Sanitized, opaque documents searchable by System A/B via TF-IDF index. |
| **3. Target Entity Pairs** | `phase2_experiment/test_target_pairs.json` | **Public Inputs** | **Included** | Unlabelled candidate pairs $(e_i, e_j)$ evaluated blindly by systems. |
| **4. Frozen Aggregate Outputs** | `phase2_experiment/outputs/full_test_scoring_report.json`, `full_test_run_manifest.json` | Immutable Audit Records | **Included** | Audited aggregate metrics, Wilson confidence intervals, and run manifest. |
| **5. Quarantined Ground-Truth Vault & Predictions** | `phase2_ground_truth_vault/*.json`, `*internal_provenance.jsonl`, `phase2_experiment/outputs/*full_test_outputs.json`, `original_full_test_scoring_report.json` | **Strict Quarantine** | **Vault-Restricted** | Case labels, per-case predictions, causal chains, and synthetic document provenance envelopes. |

---

## 4. Ground-Truth Publication Decision: Blind Evaluation vs. Reproducibility

### 4.1 The Epistemic Trade-Off
A core question in publishing machine learning benchmarks is whether to include ground-truth test labels:
1. **Public Reproducibility:** Including test labels allows external researchers to run `evaluator.py` and execute the full test suite immediately upon cloning.
2. **Blind Benchmark Integrity:** Publishing test labels or case-level prediction ledgers on an open GitHub repository exposes them to search engines, web scrapers, and frontier LLM pretraining corpora. This causes benchmark contamination, destroying the validity of future blind evaluations.

### 4.2 Publication Policy: Private Collaboration Repository
SPYDER establishes a **Private Collaboration Repository Release**:
* **Directly Included Evaluation Assets:** Because repository visibility is confirmed **Private**, the project-owned ground-truth vault (`phase2_ground_truth_vault/test_ground_truth.json`, `test_manifest.json`, `split_manifest.json`), test provenance envelopes (`test_internal_provenance.jsonl`), full-test model predictions (`system_a_full_test_outputs.json`, `system_b_full_test_outputs.json`), and historical pre-audit scoring report (`original_full_test_scoring_report.json`) are included directly in the repository to enable seamless collaborative reproduction and verification by authorized team members.
* **Excluded Third-Party Raw Data:** In accordance with strict licensing compliance, the raw third-party police network (`israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json`) remains **excluded from Git** pending confirmed redistribution rights from the original data holders.
* **Pilot Set (Open Dev Split):** The 10-case pilot ground truth (`ground_truth.json`), pilot manifest, pilot provenance (`internal_provenance.jsonl`), and pilot outputs are included in the repository to support development and smoke testing.

### 4.3 Teammate-Access Procedure for the Quarantined Vault
Teammates, authorized evaluators, and peer reviewers requiring access to the 200-case test ground truth can access or reconstruct the vault through two authorized procedures:
1. **Secure Research Drive Download:** Authorized project members can retrieve the verified cryptographic archive `SPYDER_phase2g4_audited.zip` from the project's internal research storage and place the vault files into `phase2_ground_truth_vault/` and `phase2_corpus/`.
2. **Deterministic Local Regeneration (Requires Upstream Data Access):**<br>
   > [!IMPORTANT]
   > **Regeneration Limitation:** The complete 200-case test benchmark cannot be regenerated from the public repository alone without authorized access to the excluded raw dataset.

   Because benchmark generation is 100% deterministic, authorized teammates can generate the byte-identical vault assets once the raw source network is downloaded:
   ```bash
   # Step A: Download the raw 6-month INP network from the upstream ROXANNE repository
   curl -L -o israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json \
     https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json

   # Step B: Verify dataset checksum (must match ba367e9123bfc7739c9f3bf686c39d00e733de8188e8471c608f4bf4eb679d84)
   python -c "
   import hashlib
   h = hashlib.sha256(open('israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json', 'rb').read()).hexdigest()
   assert h == 'ba367e9123bfc7739c9f3bf686c39d00e733de8188e8471c608f4bf4eb679d84'
   print('Upstream raw dataset checksum verified!')
   "

   # Step C: Deterministically generate the vault and test corpus
   python phase2_ground_truth_vault/build_test_benchmark.py
   python phase2_corpus/generate_test_evidence.py
   ```
3. **Cryptographic Integrity Verification:** After populating the vault, run:
   ```bash
   python -c "
   import json, hashlib
   manifest = json.load(open('phase2_public_artifact_hash_manifest.json'))
   for path, meta in manifest['files'].items():
       actual = hashlib.sha256(open(path, 'rb').read()).hexdigest()
       assert actual == meta['sha256'], f'MISMATCH: {path}'
   print(f'All {len(manifest[\"files\"])} public frozen hashes verified!')
   "
   ```

---

## 5. Architectural Quarantine and Anti-Leakage Policy

Within the SPYDER runtime architecture:
1. **Zero Runtime Leakage:** The retrieval indexer (`EvidenceRetriever`), the evaluated systems (`System A`, `System B`), and the runner (`runner.py`) are structurally prohibited from importing or reading from `phase2_ground_truth_vault/` or any `*internal_provenance.jsonl` file.
2. **Automated Quarantine Tests:** Regression tests (`test_scoring_audit_and_quarantine.py`) programmatically verify that zero quarantined tokens, CID identifiers, or ground-truth rationales leak into the runtime or system outputs.
3. **No ID-Based Soundness Cheating:** Evaluator rules mandate that evidence soundness requires substantive factual alignment between extracted evidence text and verified graph events; document ID prefixes alone never confer evidentiary soundness.

---

## 6. Synthetic Evidence Disclaimer

> [!IMPORTANT]<br>
> All narrative incident reports (`DOC_IR_*`) and call detail records (`CDR_*`) in the retrieval corpus are **semi-synthetic research materials**. They were generated algorithmically from anonymized graph topologies to simulate investigative evidence without exposing confidential operational police texts. They do **not** represent authentic police case files or real-world individuals.
