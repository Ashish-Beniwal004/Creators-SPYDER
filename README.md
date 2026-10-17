# SPYDER: Evidence-Grounded Agentic Criminal Network Investigation

[![Tests](https://img.shields.io/badge/pytest-120%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/benchmark-frozen%20%26%20hash--verified-success.svg)]()

> **Official Research Codebase & Benchmark Repository**<br>
> **Title:** Evidence-Grounded Agentic Criminal Network Investigation<br>
> **Subtitle:** Discovering Hidden Relationships from Fragmented and Incomplete Investigative Evidence<br>
> **Canonical Full Report:** [`docs/FINAL_ACADEMIC_REPORT.md`](docs/FINAL_ACADEMIC_REPORT.md)<br>
> **Dataset & Provenance Policy:** [`DATASET_NOTICE.md`](DATASET_NOTICE.md)<br>
> **Software License:** [MIT License](LICENSE) (original SPYDER code only)

---

## 1. What SPYDER Investigates

The **SPYDER** (Structured Provenance Yielding Deterministic Evidence Reasoning) project investigates automated relationship discovery in high-stakes investigative intelligence. In complex criminal network investigations, evidence is fragmented across multiple sources, obfuscated by street monikers, degraded by missing records, and corrupted by distractor noise.

Standard Retrieval-Augmented Generation (RAG) pipelines frequently hallucinate relationships, elevate casual telecommunication contact (CDRs) to criminal co-offending, and suffer from "spurious precision" (guessing true labels on circumstantial evidence). SPYDER introduces an explicit symbolic hypothesis verification gate to enforce strict evidentiary standards.

### Research Question
> *"Does explicit evidence verification improve evidence-supported relationship discovery over RAG-only when evidence contains aliases, missing records, and distractors?"*

### Operational Scope & Disclaimer
* **Research Benchmark Only:** SPYDER provides an experimental benchmark evaluating RAG-only discovery versus tool-gated hypothesis verification over semi-synthetic investigative evidence.
* **Not an Operational Tool:** SPYDER does **not** predict criminality, does **not** prove legal guilt, and must **never** be used for real-world surveillance, arrest, or judicial decisions.

---

## 2. System Architecture: System A vs. System B

Both systems query an identical read-only lexical TF-IDF retrieval index over sanitized evidence documents, but differ fundamentally in their reasoning and decision architectures:

```
                                  [ Target Pair: (u, v) ]
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │    TF-IDF Lexical Retriever   │
                             │   (top_k = 5, text_content)   │
                             └───────────────┬───────────────┘
                                             │
                                     Retrieved Snippets
                                             │
                     ┌───────────────────────┴───────────────────────┐
                     ▼                                               ▼
         ┌───────────────────────┐                       ┌───────────────────────┐
         │       SYSTEM A        │                       │       SYSTEM B        │
         │      (RAG-Only)       │                       │  (RAG + Verification) │
         └───────────┬───────────┘                       └───────────┬───────────┘
                     │                                               │
           Naive Heuristic Match                           Deterministic Verifier
         ├── Direct entity co-occurrence                   ├── Window compliance
         ├── CDR communication check                       ├── Crime qualification
         └── Unverified alias guess                        ├── Clearance by arrest
                     │                                     ├── Joint culpability
                     │                                     └── Contradiction check
                     ▼                                               ▼
         ┌───────────────────────┐                       ┌───────────────────────┐
         │     Final Decision    │                       │     Final Decision    │
         │ (Aggressive Discovery)│                       │ (Evidentiary Gated)   │
         └───────────────────────┘                       └───────────────────────┘
```

* **System A (RAG-Only Baseline):** Naively matches entity co-occurrences and treats phone calls (CDRs) as evidence of co-offending. Achieves high recall ($100.0\%$), but produces a severe False Positive Rate ($60.0\%$, 60 false accusations out of 100 negative pairs) and low evidentiary soundness ($11.25\%$).
* **System B (RAG + Verification):** Formulates a formal hypothesis and invokes an isolated, deterministic verification tool (`HypothesisVerifier`). Achieves **$100.0\%$ precision, $100.0\%$ specificity, zero false positives ($FPR = 0.0\%$), and $100.0\%$ evidentiary soundness**, at the cost of lower recall ($40.0\%$) due to single-turn retrieval limitations.

---

## 3. Benchmark Results & Precision-Recall Trade-Off

Across the frozen 200-case full benchmark evaluation (January 1–June 30, 2020 window):

| Metric | System A (RAG-Only) | System B (RAG + Verifier) | Operational Interpretation |
| :--- | :---: | :---: | :--- |
| **Accuracy** | **70.00%** ($140/200$) | **70.00%** ($140/200$) | Overall accuracy is tied, masking diametrically opposite error profiles. |
| **Precision** | 62.50% ($100/160$) | **100.00%** ($40/40$) | System B achieves perfect precision (+37.5 percentage points). |
| **Recall (Sensitivity)** | **100.00%** ($100/100$) | 40.00% ($40/100$) | System B abstains when evidence is incomplete or uncorroborated. |
| **Specificity** | 40.00% ($40/100$) | **100.00%** ($100/100$) | System B eliminates all false accusations ($FPR = 0.0\%$). |
| **False Positive Rate** | 60.00% ($60/100$) | **0.00%** ($0/100$) | System A falsely accuses 60 innocent/unlinked pairs. |
| **Evidentiary Soundness** | 11.25% ($18/160$) | **100.00%** ($40/40$) | **System B provides an 8.9x advantage in verified evidence backing.** |

### Key Takeaways
1. **The Precision-Recall Trade-Off:** System A maximizes recall at the cost of catastrophic false discovery ($60\%$ false positive rate). System B trades recall ($40\%$) for evidentiary safety ($100\%$ precision, $0\%$ false positive rate).
2. **Evaluator Bug Correction & Audit Integrity:** The historical pre-audit scoring report credited System A with $48.75\%$ soundness due to a prefix-matching defect in the original evaluator (where citing any `DOC_IR_` document was marked sound). The audited evaluator corrected this defect: System A's true soundness is **$11.25\%$** ($18/160$). System B maintained **$100.0\%$** soundness under both evaluators. The historical pre-audit report and case-level predictions are preserved offline in the vault archive to prevent benchmark label contamination, while the authoritative audited aggregate metrics are published in `phase2_experiment/outputs/full_test_scoring_report.json` and Section 11 of the final report.
3. **Statistical Non-Equivalence (McNemar Test):** While McNemar's test on aggregate accuracy yields non-significance ($\chi^2 = 0.0083, p = 0.927$) due to identical total error counts ($60$ vs. $60$), their error types are orthogonal: System A's errors are 100% False Positives; System B's errors are 100% False Negatives.

---

## 4. Repository Structure

```
Creators-SPYDER/
├── docs/
│   └── FINAL_ACADEMIC_REPORT.md             # Canonical 17-section comprehensive academic manuscript
├── phase2_corpus/
│   ├── CORPUS_CARD.md                       # Corpus provenance, schema, and split documentation
│   ├── generate_pilot_evidence.py           # Pilot evidence generator script
│   ├── generate_test_evidence.py            # Test evidence generator script
│   ├── internal_provenance.jsonl            # Open dev pilot provenance records (31 records)
│   ├── retrieval_documents.jsonl            # Open dev pilot retrieval corpus (31 documents)
│   ├── test_retrieval_documents.jsonl       # Frozen public test retrieval corpus (680 documents)
│   └── tests/                               # Corpus integrity and anti-leakage test suite
├── phase2_retrieval/
│   ├── retriever.py                         # Deterministic TF-IDF lexical retrieval engine
│   ├── schemas.py                           # Retrieval request/response schemas
│   └── tests/                               # Deterministic retrieval validation tests
├── phase2_verification/
│   ├── verifier.py                          # Deterministic symbolic HypothesisVerifier tool
│   ├── schemas.py                           # Verification findings and result schemas
│   └── tests/                               # Symbolic rule and clearance validation tests
├── phase2_experiment/
│   ├── config.py                            # Fixed experimental controls and path aliases
│   ├── evaluator.py                         # Rigorous scoring and evidentiary soundness evaluator
│   ├── runner.py                            # Experiment runner orchestrating Systems A & B
│   ├── schemas.py                           # Experiment execution schemas
│   ├── system_a.py                          # System A (RAG-Only Baseline) implementation
│   ├── system_b.py                          # System B (RAG + Verification) implementation
│   ├── pilot_target_pairs.json              # Pilot target pairs (10 cases)
│   ├── test_target_pairs.json               # Frozen unlabelled evaluation target pairs (200 cases)
│   ├── outputs/                             # Audited aggregate scoring report & run manifest (2 files)
│   │   ├── full_test_run_manifest.json      # Frozen run manifest (parameters, timestamps, seeds)
│   │   └── full_test_scoring_report.json    # Audited aggregate scoring report (Wilson CIs, McNemar test)
│   └── tests/                               # Runner quarantine, integrity, and scoring tests
├── phase2_public_artifact_hash_manifest.json# SHA-256 hash manifest for all 6 frozen public artifacts
├── DATASET_NOTICE.md                        # Dataset provenance, licensing terms, and access policy
├── LICENSE                                  # MIT License (original SPYDER code only)
├── requirements.txt                         # Core dependencies (pydantic, scikit-learn, numpy, pytest)
├── .gitignore                               # Quarantines test vault, raw data, and offline prediction outputs
├── .gitattributes                           # Line-ending and binary Git configurations
└── README.md                                # This repository overview
```

---

## 5. Setup and Running Public Tests

### Installation
```bash
# Clone the repository
git clone https://github.com/Ashish-Beniwal004/Creators-SPYDER.git
cd Creators-SPYDER

# Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Public Test Suite
Execute the 120 automated unit, integration, and quarantine regression tests:
```bash
python -m pytest phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests -v
```
*Expected Output:* `120 passed in ~3s (Exit Code 0)`.

### Verifying Public Frozen Artifact Hashes
Verify that all 6 distributed frozen artifacts match their audited cryptographic SHA-256 baselines:
```bash
python -c "
import json, hashlib
manifest = json.load(open('phase2_public_artifact_hash_manifest.json'))
for path, meta in manifest['files'].items():
    actual = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    assert actual == meta['sha256'], f'MISMATCH: {path}'
print(f'All {len(manifest[\"files\"])} public frozen artifact hashes verified successfully!')
"
```

---

## 6. Canonical Full Report

For complete methodological details, formal mathematical definitions, ablation studies, and independent rule-based adjudication results, refer to:
* **[`docs/FINAL_ACADEMIC_REPORT.md`](docs/FINAL_ACADEMIC_REPORT.md)** — Canonical 17-section academic manuscript including:
  * Problem formulation & graph topologies
  * Evaluator correction analysis (48.75% vs. 11.25% soundness)
  * McNemar contingency analysis & odds ratios
  * Independent rule-based adjudication (Table 3)
  * Ethical and operational considerations for investigative AI

---

## 7. Dataset Restrictions, Licensing, and Limitations

* **Software License:** Original SPYDER code is licensed under the [MIT License](LICENSE) (Copyright (c) 2026 Ashish Beniwal).
* **External Dataset Provenance:** The underlying network topology derives from the Israel National Police Burglary Co-Offender Network (Ahmadi et al., 2023; EU Horizon 2020 ROXANNE Grant No. 833635). The MIT license applies strictly to SPYDER source code, **not** to the external dataset. The raw dataset is excluded from this repository because third-party redistribution rights remain unverified. See [`DATASET_NOTICE.md`](DATASET_NOTICE.md) for data access details.
* **Blinded Benchmark Quarantine:** The 200-case test ground-truth labels (`test_ground_truth.json`) are quarantined outside the public repository to prevent contamination of web crawlers and LLM pretraining corpora, preserving benchmark integrity for future blind evaluations.
* **Semi-Synthetic Evidence:** All narrative incident reports (`DOC_IR_*`) and call detail records (`CDR_*`) in the retrieval corpus are synthetic research materials generated from anonymized graph structures; they do not represent real-world individuals or actual police case files.
* **Core Limitation:** System B's single-turn retrieval design causes false negatives when evidence requires multi-hop alias resolution across multiple documents. Multi-hop iterative retrieval represents the primary roadmap direction for future work.
