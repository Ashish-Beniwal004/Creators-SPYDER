# PHASE 2A REPORT: Freezing & Validating the 10-Case Pilot

**Project Title:** Evidence-Grounded Agentic Criminal Network Investigation
**Academic Focus:** Language Models and Agents (LMA) Research
**Target Candidate:** Israel Burglary Offender Network (ROXANNE EU Consortium / Israel National Police)
**Phase:** 2A & 2A.1 — Freeze and Validate the 10-Case Pilot (Consistency & Evidence Scope Audit)
**Status:** Complete, Validated & Frozen (18/18 Pytest Suites Passing)
**Date:** October 2026
**Author:** AI Research Assistant (Antigravity)
**Deterministic Seed:** `42`
**Vault Path:** `e:\LMA SPYDER\phase2_ground_truth_vault\`

---

## 1. Executive Summary

Phase 2A establishes the immutable evaluation foundation for the project before implementing vector indexing, RAG pipelines, or agentic verification loops. Phase 2A.1 executes an exhaustive consistency audit of negative-pair selection difficulty, reconciles evidence types to the approved scope (Police Incident Reports and CDRs only), verifies condition operationalization, and prevents ground-truth leakage.

### Key Milestones Achieved
1. **Strictly Quarantined Vault:** Created `phase2_ground_truth_vault/` containing frozen split manifests, ground-truth answer keys, evidence schemas, and automated test suites, fully isolated from any retrieval search space.
2. **Proven Component Isolation:** The 6-month slice's 316 multi-node connected components were partitioned deterministically (`seed=42`) into Pilot (10 components, 26 nodes), Dev (50 components, 140 nodes), Test (200 components, 528 nodes), and Reserve (56 components, 165 nodes). We proved **zero entity overlap, zero edge overlap, and zero crime incident overlap** between partitions.
3. **10 Frozen Pilot Cases:** Selected 5 verified positive co-offending pairs and 5 verified hard-negative pairs across all 5 planned difficulty conditions (1 positive and 1 negative per condition).
4. **Negative-Pair Policy Audit:** Verified exact spatial distances and activity months for all 5 negative pairs directly from source data. Formally documented the mathematical properties and sampling constraints of the 10-component pilot partition.
5. **Reconciled Evidence Scope:** Strictly confined evidence types to `PoliceIncidentReport` and `CallDetailRecord`. Removed all legacy references to pawn logs or asset disposal records from rationales and manifests.
6. **100% Automated Test Pass Rate:** 18 automated unit tests across 6 test modules in `phase2_ground_truth_vault/tests/` verify case balance, label veracity against raw source data, partition disjointness, schema validation, leakage rejection, approved evidence scope, and seed reproducibility.

---

## 2. Vault Architecture & Security Perimeter

To prevent evaluation contamination and transductive leakage, the ground-truth vault operates behind a strict security firewall.

```
+--------------------------------------------------------------------------+
|                 PHASE 2 VAULT & RETRIEVAL FIREWALL                       |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |  phase2_ground_truth_vault/ (STRICTLY QUARANTINED)                 |  |
|  |                                                                    |  |
|  |  - ground_truth.json       --> Definitive target labels & rationale|  |
|  |  - pilot_manifest.json     --> Frozen case metadata & conditions   |  |
|  |  - split_manifest.json     --> Disjoint graph partition mapping    |  |
|  |  - schemas.py              --> Pydantic models & validation rules  |  |
|  |  - freeze_pilot.py         --> Deterministic generator script      |  |
|  |  - tests/                  --> Automated verification test suite   |  |
|  |  - README.md / .gitignore  --> Security quarantine policy          |  |
|  +--------------------------------------------------------------------+  |
|                                     |                                    |
|                   FIREWALL: DO NOT INDEX IN RETRIEVAL                    |
|                   FIREWALL: DO NOT EXPOSE TO AGENTS                      |
|                                     v                                    |
|  +--------------------------------------------------------------------+  |
|  |  phase2_corpus/ (FUTURE RETRIEVAL SEARCH SPACE - PHASE 2B)         |  |
|  |                                                                    |  |
|  |  - incident_reports.jsonl  --> Sanitized natural language text     |  |
|  |  - call_records.jsonl      --> Sanitized communication logs        |  |
|  |  - distractor_docs.jsonl   --> Unrelated background incidents      |  |
|  |  (ONLY SanitizedRetrievalDocument objects; NO labels or conditions)|  |
|  +--------------------------------------------------------------------+  |
+--------------------------------------------------------------------------+
```

### Vault Security Protocols:
* **No Indexing:** `ground_truth.json` and `pilot_manifest.json` must NEVER be indexed into BM25 or vector search indices.
* **No Evaluation Input:** Neither baseline RAG nor agentic verification may access this directory during testing.
* **Version Control Policy:** All manifests, schemas, and reports are version-controlled for scientific reproducibility. Scratch test artifacts and pytest caches are ignored via `.gitignore`.

---

## 3. Label Policy & Closed-World Definition

### 3.1 Ground-Truth Positive Pairs ($y=1$)
A pair of offenders $(O_i, O_j)$ is classified as **Positive** if and only if they co-participated in at least one documented, solved burglary case ($CID_k$) in the Israel National Police dataset during the observation window (Jan 1 – Jun 30, 2020):

$$y(O_i, O_j) = 1 \iff \exists CID_k \text{ s.t. } O_i, O_j \in \text{Offenders}(CID_k)$$

* **Verification:** Every positive pilot pair was verified against `israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json`. All 5 positive pairs exist as authentic edges in the co-offending graph and share documented burglary cases.

### 3.2 Hard-Negative Pairs ($y=0$)
A pair of offenders $(O_i, O_j)$ is classified as **Negative** if they have zero shared crime incidents in the observation window:

$$y(O_i, O_j) = 0 \iff \text{CIDs}(O_i) \cap \text{CIDs}(O_j) = \emptyset$$

* **Closed-World Formulation:** Negative pairs are drawn from different connected components within the pilot partition and have zero recorded co-offending links across the entire observation window.

### 3.3 Epistemic Limitations of the Closed-World Assumption (CWA)
In criminological science and real-world police intelligence, the absence of a recorded co-arrest does not constitute ontological proof of real-world non-association. An unobserved relationship may exist due to:
* Undetected offenses (*the dark figure of crime*).
* Criminal operations outside the 6-month temporal window (pre-2020 or post-June 2020).
* Offenses outside the burglary offense code (e.g. narcotics or vehicle theft).

**Formal Operationalization:** The negative label in this benchmark strictly means:
*"No documented joint burglary case exists in solved Israeli National Police records between January 1 and June 30, 2020."*
Evaluated systems are scored on whether the investigative evidence *supports* a relationship, not on metaphysical claims of real-world truth. Retrieval-facing evidence for negative cases does not artificially assert that suspects "never spoke"; instead, lack of evidence supports an `Insufficient Evidence` response.

---

## 4. Audit of Negative-Pair Selection Difficulty (Phase 2A.1)

### 4.1 Comparison Against Phase 1B Policy Criteria
In `phase1_dataset_audit/PHASE1_VALIDATION_REPORT.md` (Section 4.2), candidate hard-negative criteria were described as spatial distance $\le 0.015$ in min-max scaled coordinates and matching active calendar months.

We performed an exhaustive empirical audit of all 5 negative pilot cases directly against the source data:

| Case ID | Target Pair | Comps | Measured Spatial Dist | Phase 1B Dist Threshold ($\le 0.015$) | Active Months ($O_u$ vs $O_v$) | Shared Active Months | Audit Assessment |
|---|:---:|:---:|:---:|:---:|---|:---:|---|
| **`PILOT_CASE_02`** | `('OID#4418', 'OID#5590')` | (1, 4) | **0.00847** | **PASS** ($0.00847 \le 0.015$) | `['2020-01']` vs `['2020-03','04','06']` | `[]` | Exceptionally close spatial proximity (dist < 0.009), but operates across different seasonal periods. |
| **`PILOT_CASE_04`** | `('OID#8595', 'OID#8827')` | (5, 3) | **0.04649** | FAIL ($0.04649 > 0.015$) | `['2020-02']` vs `['2020-01','02','05']` | `['2020-02']` | Exact active month match (Feb 2020). Distance is 0.046 (< 0.05 regional sector threshold). |
| **`PILOT_CASE_06`** | `('OID#4866', 'OID#5631')` | (7, 3) | **0.13483** | FAIL ($0.13483 \gg 0.015$) | `['2020-02']` vs `['2020-02']` | `['2020-02']` | Exact day match (`2020-02-25`). Distance is 0.135 (inter-sector spatial separation). |
| **`PILOT_CASE_08`** | `('OID#7661', 'OID#7994')` | (8, 9) | **0.02139** | FAIL ($0.02139 > 0.015$) | `['2020-06']` vs `['2020-05']` | `[]` | Very close spatial proximity (dist 0.021); active in consecutive calendar months (May / June). |
| **`PILOT_CASE_10`** | `('OID#4381', 'OID#6449')` | (0, 4) | **0.01731** | FAIL ($0.01731 \approx 0.015$) | `['2020-06']` vs `['2020-06']` | `['2020-06']` | Exact active month match (June 2020). Distance is 0.0173 (within 0.0023 of the 0.015 threshold). |

### 4.2 Mathematical Infeasibility Proof for the 10-Component Pilot
Why do the negative pairs in the pilot exhibit distances $> 0.015$ or unshared months?

* **Sample Size Disparity:**
  * In Phase 1B, the $\le 0.015$ threshold was demonstrated on the **Test partition (200 components, 528 nodes)**. Across the Test partition, there are $\binom{528}{2} = 139,128$ pairs and 29,261 pairs with shared active months. With 139k candidate pairs, finding hundreds of pairs with distance $\le 0.015$ and matching active months is trivial.
  * In the **Pilot partition (10 components, 26 nodes)**, there are only $\binom{26}{2} = 325$ total pairs and exactly **301 cross-component pairs** (a pool **460 times smaller**).
* **Exhaustive Combinatorial Verification:**
  We iterated across **all 301 cross-component pairs** in the 10 pilot components:
  1. Exactly **4 pairs** have distance $\le 0.015$ (distances 0.00847 and 0.01338). All 4 are between Component 1 and Component 4, and **none share an active calendar month** (Jan vs Mar/Apr/Jun).
  2. Exactly **65 pairs** share an active calendar month. The minimum distance among all pairs sharing an active month is **0.01731** (`('OID#1964', 'OID#6449')`, `('OID#2568', 'OID#6449')`, and `('OID#4381', 'OID#6449')` in June 2020).
  3. Therefore, across all 301 pairs in the pilot partition, **EXACTLY ZERO pairs** simultaneously satisfy both $\text{distance} \le 0.015$ AND matching active months.

### 4.3 Policy Decision for Pilot vs. Full Benchmark
* **Full Benchmark (Phase 3, 200 Cases):** The strict $\le 0.015$ spatial distance and matching active month criterion remains fully feasible and locked for the 200-case Test benchmark.
* **Pilot Partition (10 Cases):** In the 10-case pilot, pairs were selected to balance spatial proximity (mean distance = 0.0457, min = 0.0085) and temporal proximity (3 pairs share exact active calendar months, 1 pair active in consecutive months, 1 pair with ultra-close spatial distance 0.0085).

---

## 5. Reconciliation of Approved Evidence Types (Phase 2A.1)

In alignment with Phase 2B project scope, evidence types are strictly restricted to:
1. **`PoliceIncidentReport`**: Official residential and commercial burglary summaries based on authentic incident metadata.
2. **`CallDetailRecord`**: Intercepted telecommunication logs calibrated against empirical INP Case 2 call weights.

### Changes Executed:
* **Pawn Logs Removed:** The factual rationale for `PILOT_CASE_05` originally referenced "pawn disposal records". This has been formally reconciled to:
  *"...via circumstantial evidence (corroborating pre-incident and post-incident wiretap communication logs linking the suspects around the burglary timeline)."*
* **Zero Disallowed Keywords:** Automated tests verify that no case rationale or evidence schema contains references to pawn records, fencing transactions, bank statements, or financial ledgers.

---

## 6. Audit of Condition & Evidential Validity

| Condition | Implemented Pilot Mechanism | Leakage Safeguard |
|---|---|---|
| **1. Clean Evidence** | Unambiguous suspect OID identifiers in primary incident report and direct pre-crime CDR communication logs. | No label, condition, or target pair tags in retrieval metadata. |
| **2. Alias Ambiguity** | Suspect OID#8595 is referred to in evidence by alias monikers ("The Wire", "Blue Sedan Driver"). Agent must resolve moniker across reports. | Aliases do not contain canonical OIDs or ground-truth conclusions. |
| **3. Missing Evidence** | Primary joint arrest report (`CID#2293`) is omitted from the retriever search space. Relationship must be inferred via circumstantial CDR patterns. | Omission is enforced at corpus construction; missing files are physically excluded. |
| **4. Distractors** | Retrieval corpus is padded with 3x irrelevant local incident reports from nearby coordinates and bystander statements. | Distractor reports describe real solo burglaries without referencing target pairs. |
| **5. Mixed Difficulty** | Combines unlinked suspect monikers ("The Locksmith"), omitted primary incident report, and distractor noise simultaneously. | Multi-degradation applied without leaking answers. |

---

## 7. The 10 Frozen Pilot Cases

Frozen in [`pilot_manifest.json`](pilot_manifest.json) and [`ground_truth.json`](ground_truth.json):

| Case ID | Target Pair | Label | Condition | Comps | Shared CIDs | Spatial Dist | Shared Months | Approved Evidence Basis |
|---|:---:|:---:|---|:---:|:---:|:---:|:---:|---|
| **`PILOT_CASE_01`** | `('OID#4418', 'OID#8864')` | **1 (Pos)** | `clean_evidence` | (1, 1) | `['CID#6456']` | 0.00000 | 2020-01 | Incident report & CDRs linking suspects in residential burglary CID#6456. |
| **`PILOT_CASE_02`** | `('OID#4418', 'OID#5590')` | **0 (Neg)** | `clean_evidence` | (1, 4) | `[]` | 0.00847 | — | Independent incident reports in Sector-Central-East; zero shared crimes. |
| **`PILOT_CASE_03`** | `('OID#6819', 'OID#8595')` | **1 (Pos)** | `alias_ambiguity` | (5, 5) | `['CID#5170']` | 0.00000 | 2020-02 | Joint burglary CID#5170. OID#8595 referenced under alias "The Wire". |
| **`PILOT_CASE_04`** | `('OID#8595', 'OID#8827')` | **0 (Neg)** | `alias_ambiguity` | (5, 3) | `[]` | 0.04649 | 2020-02 | Independent suspects active in Feb 2020; unlinked monikers in corpus. |
| **`PILOT_CASE_05`** | `('OID#4866', 'OID#6315')` | **1 (Pos)** | `missing_evidence` | (7, 7) | `['CID#2293']` | 0.00000 | 2020-02 | Joint burglary CID#2293. Primary arrest file omitted; linked via CDRs. |
| **`PILOT_CASE_06`** | `('OID#4866', 'OID#5631')` | **0 (Neg)** | `missing_evidence` | (7, 3) | `[]` | 0.13483 | 2020-02 | Both active on 2020-02-25; separate incident records with no joint CDRs. |
| **`PILOT_CASE_07`** | `('OID#6612', 'OID#7994')` | **1 (Pos)** | `distractors` | (9, 9) | `['CID#4927']` | 0.00000 | 2020-05 | Joint burglary CID#4927. Corpus padded with 3x local distractor reports. |
| **`PILOT_CASE_08`** | `('OID#7661', 'OID#7994')` | **0 (Neg)** | `distractors` | (8, 9) | `[]` | 0.02139 | — | Adjacent south-west sector burglaries; padded with local distractor noise. |
| **`PILOT_CASE_09`** | `('OID#1964', 'OID#2568')` | **1 (Pos)** | `mixed_difficulty` | (0, 0) | `['CID#1288']` | 0.00000 | 2020-06 | Joint burglary CID#1288. Alias ("The Locksmith"), missing primary record, & distractors. |
| **`PILOT_CASE_10`** | `('OID#4381', 'OID#6449')` | **0 (Neg)** | `mixed_difficulty` | (0, 4) | `[]` | 0.01731 | 2020-06 | Both active in June 2020 in adjacent sectors (dist 0.0173); degraded evidence corpus. |

---

## 8. Automated Test Suite & Verification Results

All tests are implemented in `phase2_ground_truth_vault/tests/`:

```powershell
python -m pytest "e:\LMA SPYDER\phase2_ground_truth_vault\tests" -v
```

### Actual Command Output:
```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: E:\LMA SPYDER\phase2_ground_truth_vault
plugins: anyio-4.12.1
collecting ... collected 18 items

tests/test_audit_consistency.py::test_approved_evidence_scope_no_pawn_or_unsupported_types PASSED [  5%]
tests/test_audit_consistency.py::test_negative_pair_distance_and_month_verification PASSED [ 11%]
tests/test_audit_consistency.py::test_condition_operationalization PASSED [ 16%]
tests/test_audit_consistency.py::test_retrieval_facing_evidence_no_leakage_or_artificial_negation PASSED [ 22%]
tests/test_evidence_schemas.py::test_police_incident_report_validation PASSED [ 27%]
tests/test_evidence_schemas.py::test_call_detail_record_validation PASSED [ 33%]
tests/test_evidence_schemas.py::test_pilot_evidence_sample_file PASSED   [ 38%]
tests/test_leakage_safeguards.py::test_sanitized_retrieval_document_allows_clean_payload PASSED [ 44%]
tests/test_leakage_safeguards.py::test_sanitized_retrieval_document_rejects_leakage_keys PASSED [ 50%]
tests/test_leakage_safeguards.py::test_sanitized_retrieval_document_rejects_leakage_in_text PASSED [ 55%]
tests/test_leakage_safeguards.py::test_ground_truth_vault_security_quarantine PASSED [ 61%]
tests/test_pilot_cases.py::test_pilot_case_count_and_balance PASSED      [ 66%]
tests/test_pilot_cases.py::test_condition_assignments PASSED             [ 72%]
tests/test_pilot_cases.py::test_ground_truth_labels_match_source_data PASSED [ 77%]
tests/test_pilot_cases.py::test_ground_truth_vault_synchronization PASSED [ 83%]
tests/test_reproducibility.py::test_seed_reproducibility PASSED          [ 88%]
tests/test_split_isolation.py::test_split_disjointness PASSED            [ 94%]
tests/test_split_isolation.py::test_pilot_cases_contained_in_pilot_partition PASSED [100%]

============================= 18 passed in 0.21s ==============================
```

---

## 9. Reproducibility & Readiness Summary

### Exact Commands to Reproduce Artifacts & Tests:
```powershell
# 1. Regenerate frozen manifests and vault
python "e:\LMA SPYDER\phase2_ground_truth_vault\freeze_pilot.py"

# 2. Run automated validation test suite
python -m pytest "e:\LMA SPYDER\phase2_ground_truth_vault\tests" -v
```

### Readiness for Phase 2B:
* **Approved Evidence Scope:** Confirmed (Police Incident Reports and CDRs only).
* **Quarantined Vault:** Complete and firewalled from retrieval.
* **Component Isolation:** 100% leak-free across Pilot, Dev, and Test.
* **Condition Design:** Operationalized and tested.
* **Next Step (Phase 2B):** Build the deterministic synthetic evidence generator (`generate_pilot_evidence.py`) to produce the complete pilot corpus in `phase2_corpus/`.
