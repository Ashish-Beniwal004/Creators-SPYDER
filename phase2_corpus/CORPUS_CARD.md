# CORPUS CARD: Synthetic Investigative Evidence Corpus (Phase 2B.1 Remediated Pilot)

**Dataset Title:** Evidence-Grounded Agentic Criminal Network Investigation — Pilot Retrieval Corpus<br>
**Corpus Version:** `1.1.0` (Phase 2B.1 Remediated Pilot)<br>
**Creation Date:** October 2026<br>
**Deterministic Seed:** `42`<br>
**License / Access:** Strictly Academic Research Use Only<br>
**Corpus Location:** `phase2_corpus/retrieval_documents.jsonl`<br>
**Internal Provenance:** `phase2_corpus/internal_provenance.jsonl`<br>

---

## 1. Executive Summary & Purpose

The **Phase 2B.1 Remediated Pilot Retrieval Corpus** is a controlled, synthetic investigative dataset designed to evaluate Retrieval-Augmented Generation (RAG) pipelines and LLM-based autonomous agent architectures on the task of **Evidence-Grounded Criminal Network Investigation**.

The corpus provides retrievable operational records for **10 frozen pilot investigation cases** (5 co-offending positive pairs and 5 non-co-offending negative pairs) spanning five distinct difficulty conditions:
1. `clean_evidence` (unambiguous co-presence and direct communications)
2. `alias_ambiguity` (street monikers requiring multi-hop identity resolution across separate files)
3. `missing_evidence` (primary arrest reports withheld; relationship inferred via circumstantial CDRs)
4. `distractors` (local incident noise and false alarms)
5. `mixed_difficulty` (simultaneous alias resolution, primary file omission, and distractor noise)

---

## 2. Phase 2B.1 Leakage Remediation & Identifier Sanitization

Following the Phase 2B.1 consistency audit, two critical leakage vectors were remediated:

### 2.1 Replacement of Original Crime Identifiers
* **Vulnerability in v1.0:** Original source dataset crime identifiers (e.g., `CID#6456`, `CID#5170`, `CID#2293`) were exposed through incident report headers and `metadata.incident_id`.
* **Remediation in v1.1:** All original crime IDs in searchable text and retriever metadata have been replaced with **synthetic, non-semantic incident references** formatted as `INC-2020-xxxx` (e.g., `INC-2020-7182`, `INC-2020-4916`). Original source CIDs are preserved **exclusively** within `internal_provenance.jsonl` for evaluation audit.

### 2.2 Opaque, Non-Semantic Document Identifiers
* **Vulnerability in v1.0:** Retrieval document IDs embedded pilot case references (e.g., `DOC_IR_PILOT_01_A`, `CDR_PILOT_03_01`), creating an unintended case-grouping side channel.
* **Remediation in v1.1:** Every retrieval document is assigned an **opaque 8-character hex hash identifier**:
  - Incident reports: `DOC_IR_[0-9a-f]{8}` (e.g., `DOC_IR_68ca5aaf`)
  - Communication intercepts: `CDR_[0-9a-f]{8}` (e.g., `CDR_055ad8bc`)
  - No document ID contains `PILOT`, `CASE`, case numbers (`01`–`10`), entity IDs (`OID#`), or condition strings.

---

## 3. Synthetic Data Declaration & Disclaimer

> [!IMPORTANT]
> **SYNTHETIC RESEARCH MATERIAL NOTICE**<br>
> All text narratives, incident summaries, wiretap timestamps, and call durations in this corpus are **synthetically generated research artifacts**.<br>
> While calibrated against empirical distributions from the Israel National Police (INP) Burglary Offender Network (Jan 1 – Jun 30, 2020) and ROXANNE consortium communications data, **no text in this dataset represents actual historical police transcripts, real persons, or authentic wiretap audio**.<br>
> All entity identifiers (`OID#xxxx`) and incident references (`INC-2020-xxxx`) represent anonymized benchmark keys.

---

## 4. Approved Evidence Scope

In compliance with the project's approved scope, this corpus contains **strictly two evidence types**:

1. **`PoliceIncidentReport` (`doc_type: incident_report`)**:
   - Structured summaries of reported burglaries, forced entry methods, stolen item classifications, observed persons of interest, and responding officer field notes.
   - Grounded in authentic coordinate clusters, dates, and group sizes from the source network.
2. **`CallDetailRecord` (`doc_type: call_detail_record`)**:
   - Structured telecommunication intercept logs recording caller handle, callee handle, duration (seconds), originating cell tower sector, and communication mode (`voice_call` or `sms`).
   - Calibrated against empirical call frequency and duration distributions from empirical Israel LEA Case 2 speaker networks.

**Explicitly Excluded / Disallowed:**<br>
Pawn shop transaction logs, stolen property fencing ledgers, banking/financial records, and digital forensics images are out of scope for Phase 2B/2B.1 and are strictly prohibited from this corpus.

---

## 5. Closed-World Evaluation Policy & Epistemic Limitations

### 5.1 Positive Co-Offending ($y = 1$)
A pair $(O_u, O_v)$ is ground-truth positive if and only if they co-participated in at least one solved joint burglary incident recorded in the INP database between January 1 and June 30, 2020:
$$y(O_u, O_v) = 1 \iff \exists CID_k \text{ s.t. } O_u, O_v \in \text{Offenders}(CID_k)$$

### 5.2 Negative Pairs ($y = 0$) & The Closed-World Assumption (CWA)
A pair $(O_u, O_v)$ is ground-truth negative if they share zero recorded crime incidents in the observation window:
$$y(O_u, O_v) = 0 \iff \text{CIDs}(O_u) \cap \text{CIDs}(O_v) = \emptyset$$

### 5.3 Epistemic Disclaimer
In criminological intelligence, the absence of a recorded co-arrest does **not** constitute metaphysical proof that two individuals have never met or have no illicit relationship (*the dark figure of crime*).
Accordingly:
- Evaluated agents are scored on whether the **retrieved investigative evidence supports an inference of co-offending**, not on ontological omniscience.
- The retrieval corpus **never** contains artificial assertions stating that negative pairs "never spoke", "are definitely innocent", or "have no relationship".
- A lack of retrieved linkage legitimately supports an output of **`Insufficient Evidence`** or **`Non-Associated based on available records`**.

---

## 6. Corpus Architecture & Privacy Separation

The corpus strictly decouples public, retriever-facing documents from internal audit provenance:

```
+-------------------------------------------------------------------------------+
|                       CORPUS SECURITY ARCHITECTURE                            |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |  phase2_corpus/retrieval_documents.jsonl (PUBLIC SEARCH SPACE)        |   |
|   |  - Opaque doc_id (DOC_IR_[0-9a-f]{8}, CDR_[0-9a-f]{8})                |   |
|   |  - doc_type (incident_report, call_detail_record)                     |   |
|   |  - timestamp (chronological sorting)                                  |   |
|   |  - text_content (sanitized natural language / logs; INC-2020-xxxx)    |   |
|   |  - metadata (sector, date, synthetic incident_id ONLY)                |   |
|   |  * ZERO labels, ZERO conditions, ZERO rationales, ZERO comp IDs       |   |
|   |  * ZERO source CIDs, ZERO pilot case identifiers                      |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |  phase2_corpus/internal_provenance.jsonl (INTERNAL AUDIT ONLY)        |   |
|   |  - document_id (matching opaque doc_id)                               |   |
|   |  - is_synthetic (True)                                                |   |
|   |  - generation_seed (42)                                               |   |
|   |  - ground_truth_case_id (PILOT_CASE_01 .. 10)                         |   |
|   |  - target_pair (canonical tuple)                                      |   |
|   |  - source_incident_cid (authentic INP CID#xxxx)                       |   |
|   |  - condition (clean, alias, missing, distractor, mixed)               |   |
|   |  - generation_rule (explicit generator rule)                          |   |
|   |  - underlying_entity_references (all referenced IDs & monikers)       |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

---

## 7. Corpus Statistics (Pilot v1.1)

| Metric | Value |
|---|---|
| **Total Retrievable Documents** | **31** |
| **Police Incident Reports** | 20 (64.5%) |
| **Call Detail Records (CDRs)** | 11 (35.5%) |
| **Cases Covered** | 10 / 10 Pilot Cases (100%) |
| **Average Documents per Case** | 3.1 |
| **Distractor Documents** | 7 (22.6% of corpus) |
| **Distinct Spatial Sectors** | 5 (`Sector-Central-East`, `Sector-North-West`, `Sector-West-Central`, `Sector-South-Central`, `Sector-South-West`) |
| **Temporal Range** | January 17, 2020 – June 25, 2020 |
| **Total Byte Size** | 18,257 bytes (`retrieval_documents.jsonl`) |
| **Retrieval File SHA-256** | `a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded` |
| **Internal Provenance Byte Size** | 12,916 bytes (`internal_provenance.jsonl`) |
| **Internal Provenance SHA-256** | `ae29dcd873a3f87f01dff4e5dceb3edd041caf64e21f7065d74114ad2f9287bc` |
| **Automated Test Suite Status** | 46 / 46 Pytest Tests Passing (100%) |

---

## 8. Known Biases & Dataset Limitations

1. **Window Truncation:** Data covers a 6-month cross-sectional slice (Jan–Jun 2020). Longitudinal links preceding or following this period are not captured.
2. **Offense Specificity:** Records are restricted to residential and commercial burglary offenses. Ancillary criminal relationships (e.g., narcotics, vehicle theft, violence) are absent.
3. **Police Recording Filter:** Only detected, reported, and cleared offenses appear in the underlying graph. Solitary actors or unsolved burglaries are under-represented.
4. **Spatial Scaling:** Geographic coordinates are min-max scaled to $[0, 1]$ to protect authentic police jurisdiction locations.

---

## 9. Prohibited Uses

- **No Individual Profiling:** Under no circumstances may this corpus or its identifiers be matched against living individuals.
- **No Real-World Judicial Inference:** This benchmark is an algorithm evaluation tool; outputs cannot be used for predictive policing or criminal charging.
- **No Transductive Indexing:** Evaluated agents must never have access to `internal_provenance.jsonl` or `phase2_ground_truth_vault/`.
