# SPYDER: Evidence-Grounded Agentic Criminal Network Investigation

[![Tests](https://img.shields.io/badge/pytest-221%20passed%2C%204%20skipped-brightgreen.svg)]()
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

## Current checkpoint work — October 30, 2026

**Start with [MID_SUBMISSION_PROGRESS.md](MID_SUBMISSION_PROGRESS.md)** for
implemented progress, actual experiment results, limitations and the final timeline.
The [checkpoint data policy](CHECKPOINT_DATA_POLICY.md) explains the development
evaluation scope and the separation between inference and scoring inputs.

The new `phase3_llm` pipeline uses **Groq / openai/gpt-oss-120b** for the
paired pilot. **The real ten-pair experiment completed:** 20 executions, zero
failures, 30 requests and 42,591 tokens. Both arms achieved 90% binary accuracy
and 0.8889 F1; no verification gain was observed on this small development pilot.
The [mid-submission report](MID_SUBMISSION_PROGRESS.md) covers actual results,
limitations. The [saved-output bundle](research_audit/groq_checkpoint_20261030/README.md)
was rescored successfully without API calls.
Use [PILOT_RUNBOOK.md](PILOT_RUNBOOK.md)
and [the LLM package README](phase3_llm/README.md) for current commands.
Earlier Gemini attempts produced one complete paired case before provider errors;
they remain separate and are not combined with Groq results. Historical deterministic
architecture/results below describe the original benchmark. The new LLM verifier
arm records the model's final decision without forcibly replacing it with the tool verdict.

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
│   ├── outputs/                             # Raw outputs, manifests, and scoring reports
│   │   ├── full_test_run_manifest.json      # Full-test run manifest (parameters, timestamps, seeds)
│   │   ├── full_test_scoring_report.json    # Audited aggregate scoring report (Wilson CIs, McNemar test)
│   │   ├── original_full_test_scoring_report.json # Historical pre-audit report with prefix bug
│   │   ├── system_a_full_test_outputs.json  # System A 200-case raw execution outputs
│   │   ├── system_b_full_test_outputs.json  # System B 200-case raw execution outputs
│   │   ├── pilot_run_manifest.json          # Pilot run manifest
│   │   ├── pilot_scoring_report.json        # Pilot scoring report
│   │   ├── system_a_pilot_outputs.json      # System A pilot outputs
│   │   └── system_b_pilot_outputs.json      # System B pilot outputs
│   └── tests/                               # Runner quarantine, integrity, and scoring tests
├── phase2_ground_truth_vault/               # Private evaluation assets and ground truth
│   ├── ground_truth.json                    # Pilot ground truth (10 cases)
│   ├── test_ground_truth.json               # Full evaluation ground truth (200 cases)
│   ├── pilot_manifest.json                  # Pilot manifest
│   ├── test_manifest.json                   # Full evaluation test manifest
│   ├── split_manifest.json                  # Disjoint graph partition manifest
│   ├── pilot_evidence_sample.json           # Sample evidence fixtures
│   ├── build_test_benchmark.py              # Deterministic benchmark builder
│   ├── freeze_pilot.py                      # Pilot benchmark freezer
│   ├── schemas.py                           # Ground-truth schema definitions
│   └── tests/                               # Split isolation, leakage, and schema tests (32 tests)
├── phase1_dataset_audit/                    # Dataset discovery, audit, and governance documentation
│   ├── DATASET_DECISION.md                  # Canonical dataset selection rationale
│   ├── dataset_inventory.csv                # Survey of 14 criminal network datasets
│   ├── public_vs_synthetic_requirements.csv # Allocation matrix of real vs. synthetic layers
│   └── sources.md                           # Provenance citations and upstream download routes
├── phase2_artifact_hash_manifest.json       # SHA-256 hash manifest for all 15 frozen project artifacts
├── phase2_public_artifact_hash_manifest.json# SHA-256 hash manifest for 6 public frozen artifacts
├── DATASET_NOTICE.md                        # Dataset provenance, licensing terms, and access policy
├── LICENSE                                  # MIT License (original SPYDER code only)
├── requirements.txt                         # Core dependencies (pydantic, scikit-learn, numpy, pytest)
├── .gitignore                               # Excludes caches and raw third-party police data
├── .gitattributes                           # Line-ending and binary Git configurations
└── README.md                                # This repository overview
```

---

## 5. Setup, Testing, and Evaluation Reproduction

### Installation
```bash
# Clone the private repository
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

### Running the Complete Test Suite
Execute the 152 automated tests across all five project test suites:
```bash
python -m pytest phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests phase2_ground_truth_vault/tests -v
```
*Expected Output:* `148 passed, 4 skipped in ~3s (Exit Code 0)`.
*(The 4 skipped tests require the raw third-party police network file; when downloaded to `phase1_dataset_audit/data/`, all 152 tests pass).*

### Reproducing Full Benchmark Evaluation
To re-score the frozen execution outputs against the 200-case ground-truth vault:
```bash
python -c "import phase2_experiment.evaluator as ev; ev.evaluate_full_test_runs()"
```

### Verifying Frozen Artifact Hashes
Verify all 15 frozen project artifacts against their cryptographic SHA-256 baselines:
```bash
python -c "
import json, hashlib
manifest = json.load(open('phase2_artifact_hash_manifest.json'))
for path, meta in manifest['files'].items():
    actual = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    assert actual == meta['sha256'], f'MISMATCH: {path}'
print(f'All {len(manifest[\"files\"])} frozen project artifacts verified successfully!')
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
