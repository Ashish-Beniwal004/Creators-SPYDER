# Phase 1 Dataset Decision Document

**Project:** Evidence-Grounded Agentic Criminal Network Investigation
**Phase:** 1 — Public Dataset Discovery, Feasibility Audit, and Synthetic Data Requirements
**Status:** Approved & Validated
**Decision Date:** October 2026

---

## 1. Selected Dataset

**Primary Backbone:** **Israel Burglary Offender Network (6-Month Temporal Slice: Jan 1 – Jun 30, 2020)**
* **Source:** Israel National Police / ROXANNE EU Consortium (Ahmadi et al., *Journal of Computational Science*, 2023).
* **Repository:** `https://github.com/erichoang/criminal-network-visualization`
* **File:** `israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json` (1.14 MB uncompressed).
* **Secondary Calibration Data:** `israel_lea_case2_speakers.json` (42 KB) for real-world call frequency parameterization.
* **Full-Scale Fallback:** `israel_lea_inp_burglary_offender_id_network.json` (15.55 MB, 17,237 offenders, 21,302 edges).

---

## 2. Rationale for Selection

1. **Direct Public Accessibility & Verified Download:**
   Unlike the restricted ROXANNE Simulated Dataset (ROXSD) which requires signed institutional agreements, or the Montreal co-offending dataset which is legally barred from distribution, the Israel Burglary network is hosted directly in open GitHub files under a permissive BSD-3-style license.
2. **Empirically Proven Ground-Truth Co-Offending:**
   The dataset captures genuine, solved law enforcement burglary records anonymized under GDPR and approved by Israeli police legal counsel. Ground-truth relationships reflect actual co-arrest and co-charge facts.
3. **Sufficient Independent Cases Without Data Leakage:**
   The 6-month slice alone provides **1,658 offender nodes, 1,728 co-offending links, 1,671 distinct crime cases**, and **316 multi-node connected components**. This guarantees that the proposed 200 frozen evaluation cases (100 positive, 100 negative) can be constructed from completely disjoint graph components, avoiding entity overlap and label leakage between development and evaluation sets.
4. **Complete Metadata for Investigative Grounding:**
   100% of crime incidents contain exact timestamps (`YYYY-MM-DD HH:MM:SS`), normalized geographic coordinates (`X, Y`), and co-offender group sizes (`num_of_offenders`). Zero missing timestamps or coordinates were detected in local verification.
5. **Computationally Lightweight:**
   At 1.14 MB, the slice loads in Python via NetworkX in < 0.2 seconds and consumes < 50 MB RAM, easily satisfying our academic compute and deadline constraints.

---

## 3. Data Breakdown: Real vs. Synthetic Allocation

| Layer | Component | Status | Source / Operationalization |
|---|---|---|---|
| **Structural Ground Truth** | Offender Entities (`OID#xxx`) | **Real** | Israel Burglary Offender Network |
| **Structural Ground Truth** | Crime Cases (`CID#xxx`) | **Real** | Israel Burglary Offender Network |
| **Structural Ground Truth** | Co-Offending Labels | **Real** | Documented shared burglary cases |
| **Spatio-Temporal Ground Truth** | Incident Dates & Times | **Real** | `crime_details[CID]['date']` |
| **Spatio-Temporal Ground Truth** | Incident Coordinates | **Real** | Normalized `X, Y` coordinates |
| **Investigative Evidence** | Police Narrative Reports | **Synthetic** | Templated/LLM-generated incident narratives matching real metadata |
| **Investigative Evidence** | Call Detail Records (CDRs) | **Synthetic** | Calibrated against real Israel LEA Case 2 call-frequency distribution |
| **Investigative Evidence** | Fencing / Pawn Transactions | **Synthetic** | Generated property disposal records |
| **Experimental Manipulation** | Suspect Aliases | **Synthetic** | Controlled moniker injection (Conditions 2 & 5) |
| **Experimental Manipulation** | Missing Evidence Omissions | **Protocol** | Systematic withholding of primary incident records (Conditions 3 & 5) |
| **Experimental Manipulation** | Distractor Incidents | **Synthetic + Real** | Unrelated burglary reports and bystander interviews (Conditions 4 & 5) |

---

## 4. Evaluation Set Architecture (200 Frozen Cases)

The dataset fully supports the proposed evaluation architecture:
* **Positive Cases (100 pairs):** 100 disjoint pairs $(O_i, O_j)$ with documented co-offending in a shared crime ($CID_k$), sampled from separate graph clusters.
* **Negative Cases (100 pairs):** 100 hard-negative pairs $(O_i, O_m)$ operating in the same spatial sector and active month with zero co-offending history.
* **Difficulty Allocation (40 cases per condition: 20 positive, 20 negative):**
  1. *Condition 1 (Clean Baseline):* Unambiguous narrative reports and CDRs.
  2. *Condition 2 (Alias Ambiguity):* One or both suspects referenced by aliases across evidence documents.
  3. *Condition 3 (Missing Evidence):* Direct joint arrest report withheld; relationship supported only by indirect CDR or pawn transaction.
  4. *Condition 4 (Distractors):* Retrieval corpus padded with 3x irrelevant local incident reports.
  5. *Condition 5 (Mixed Difficulty):* Simultaneous aliases, missing primary records, and distractors.

---

## 5. Next Immediate Actions (Phase 2 Roadmap)

1. **Freeze Graph Split:** Isolate 200 evaluation pairs and 50 dev/pilot pairs into a permanent, version-controlled ground-truth vault (`phase2_data_vault/ground_truth.json`).
2. **Develop Evidence Synthesis Engine:** Implement a deterministic generator script (`synthesize_evidence.py`) using fixed random seeds and structured Pydantic schemas to produce incident reports, CDRs, and pawn receipts.
3. **Build Pilot Corpus:** Generate a 10-case pilot corpus (5 positive, 5 negative) to validate retrieval ingestion and schema validity before building the full 200-case evaluation corpus.
