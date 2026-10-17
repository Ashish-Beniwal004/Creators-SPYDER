# Evidence-Grounded Agentic Criminal Network Investigation
## Discovering Hidden Relationships from Fragmented and Incomplete Investigative Evidence

**Authors:** SPYDER Research Consortium & Evaluation Group<br>
**Document ID:** `docs/FINAL_ACADEMIC_REPORT.md`<br>
**Date:** October 2026<br>
**Status:** Pre-Publication Audited Final Report<br>
**Benchmark Artifact Status:** Frozen & Hash-Verified (Zero Asset Drift)<br>
**Test Suite Status:** 152 Passed (Full Vault) / 138 Passed, 14 Skipped (Public Blinded Clone)<br>

---

## Abstract

Automating criminal network analysis (CNA) using Large Language Model (LLM) agents and Retrieval-Augmented Generation (RAG) offers substantial potential for synthesizing voluminous investigative dossiers. However, standard RAG architectures face severe vulnerabilities when evidence is fragmented, incomplete, or corrupted by distractors: they routinely conflate casual telecommunications with co-offending, confuse physical proximity with joint culpability, and produce high apparent benchmark accuracy through "spurious precision"—asserting true relationship labels based on circumstantial or legally non-qualifying evidence.

This paper presents a rigorous, controlled experimental evaluation of **SPYDER** (Structured Provenance Yielding Deterministic Evidence Reasoning), investigating whether explicit symbolic hypothesis verification improves evidence-grounded relationship discovery over standard RAG. Using a 200-case frozen benchmark grounded in the Israel National Police (INP) burglary co-offender network across a six-month evaluation window (January 1–June 30, 2020), we compare **System A** (a standard RAG-only baseline) against **System B** (RAG coupled with a deterministic, tool-isolated hypothesis verifier). Evaluation spans five balanced conditions: clean evidence, alias ambiguity, missing evidence, distractors, and mixed difficulty.

Both systems achieve identical aggregate benchmark accuracy of **70.0%** ($140/200$, 95% Wilson CI: [63.3%, 75.9%]), and paired statistical testing yields a non-significant result across three McNemar formulations (uncorrected $\chi^2 = 0.000, p = 1.000$; Edwards continuity-corrected $\chi^2 = 0.00833, p = 0.927$; exact two-sided binomial $p = 1.000$). Crucially, this non-significance does **not** indicate system equivalence; rather, the two architectures inhabit completely orthogonal error domains. System A acts as an aggressive discoverer ($100.0\%$ recall, but $60.0\%$ false-positive rate, generating 60 false-positive relationship predictions on negative benchmark cases). System B acts as an evidentiary certifier ($100.0\%$ precision, $100.0\%$ specificity, and $0.0\%$ false-positive rate, eliminating all benchmark false positives at the cost of 60 false negatives/abstentions).

An independent rule-based evidentiary adjudication of all 200 positive predictions—decoupled from the evaluated verifier—reveals that System A achieves only **11.25%** evidentiary soundness ($18/160$, 95% CI: [7.24%, 17.08%]), with 82 predictions grounded solely in wiretap call records without crime evidence. In contrast, System B achieves **100.0%** evidentiary soundness ($40/40$, 95% CI: [91.2%, 100.0%]), establishing an **8.9x advantage in rule-audited evidentiary soundness** on this benchmark ($100.0\%$ vs. $11.25\%$). We conclude that explicit verification provides an effective computational safeguard against unsupported relationship predictions in synthetic benchmark evidence, identify the single-turn retrieval bottleneck responsible for System B's recall collapse under alias ambiguity, and establish an epistemic framework for responsible decision-support deployment.

---

## 1. Introduction and Motivation

Law enforcement and intelligence analysts face an information environment characterized by information overload and evidentiary degradation. Modern criminal investigations rarely feature centralized, unambiguous dossiers. Instead, analysts must piece together fragmented intelligence spread across incident reports, wiretap Call Detail Records (CDRs), surveillance logs, and field interview reports. Within this unstructured evidentiary corpus, criminal actors actively obfuscate their identities using street monikers, operate in decentralized network cells, and mix legitimate activities with illicit operations.

The emergence of Retrieval-Augmented Generation (RAG) and agentic workflows has spurred interest in automated decision-support systems for Criminal Network Analysis (CNA). By retrieving relevant case documents into the context window of a reasoning agent, RAG systems promise to uncover hidden co-offending ties and synthesize cross-case links that human investigators might overlook.

However, deploying generative RAG pipelines in high-stakes investigative settings introduces acute legal, ethical, and epistemic risks:
1. **The Spurious Precision Trap:** In benchmark evaluations, RAG models frequently achieve high precision scores by guessing that two individuals are connected. If the ground-truth label happens to be positive, the prediction is counted as a "True Positive" even if the model cited an irrelevant parking citation or a wiretap record showing casual phone contact.
2. **Conflation of Communication and Culpability:** Telecommunication contact between two individuals does not constitute legal proof of co-participation in a specific burglary offense. Unconstrained RAG systems routinely elevate circumstantial phone contact to co-offending culpability.
3. **Susceptibility to Distractor Noise:** In dense urban jurisdictions, multiple independent incidents occur in spatial proximity. Naive retrieval pipelines frequently conflate independent actors or commercial false alarms with co-offending networks.
4. **Catastrophic Costs of Type I Errors:** In traditional information retrieval, False Positives (Type I errors) represent minor inconveniences (e.g., an irrelevant web search result). In investigative decision-support, False Positives represent unsupported relationship assertions that can generate ungrounded investigative hypotheses, risking unwarranted scrutiny and misdirected investigative resources.

To address these vulnerabilities, this paper conducts a controlled experimental investigation comparing a standard RAG-only architecture (**System A**) against an evidence-grounded agentic architecture featuring explicit, symbolic hypothesis verification (**System B**). We formally evaluate both systems across a frozen 200-case benchmark designed to simulate realistic evidentiary degradations, evaluate their performance through independent evidentiary adjudication, and reconcile their statistical properties.

---

## 2. Research Question and Hypotheses

### 2.1 Research Question
We evaluate the following primary research question:
> **Research Question:** *Does explicit evidence verification improve evidence-supported relationship discovery over RAG-only when the evidence contains aliases, missing records, and distractors?*

### 2.2 Formal Hypotheses
We formalize this research question into two operational hypotheses:

* **Hypothesis 1 (Precision and Evidentiary Soundness):**<br>
  *Integrating an isolated, deterministic hypothesis verification gate will eliminate false-positive co-offending assertions ($FPR \to 0\%$) and yield significantly higher evidentiary soundness than a RAG-only baseline, wherein positive predictions must be grounded in verified, qualifying crime documents rather than circumstantial or non-qualifying records.*

* **Hypothesis 2 (Recall Trade-off and Retrieval Bottleneck):**<br>
  *Under single-turn retrieval, explicit hypothesis verification will incur a substantial recall penalty in conditions with missing evidence or unresolved aliases, because the verifier will conservatively reject incomplete evidence chains rather than generating speculative links.*

---

## 3. Background and Related-Work Positioning

Our work intersects four primary domains in computational criminology, artificial intelligence, and natural language processing:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 LITERATURE CONVERGENCE                                 │
├─────────────────────────┬──────────────────────────────────────────────────────────────┤
│ Criminal Network        │ Link prediction and co-offender extraction from police data  │
│ Analysis (CNA)          │ (Ahmadi et al., 2023; Cavallaro et al., 2020; Rosenfeld).    │
├─────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Retrieval-Augmented     │ Context retrieval from unstructured knowledge corpora        │
│ Generation (RAG)        │ (Lewis et al., 2020; Gao et al., 2023).                     │
├─────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Evidence Attribution    │ Grounded question answering and citation verification        │
│ & Factuality            │ (Rashkin et al., 2021; Bohnet et al., 2022).                 │
├─────────────────────────┼──────────────────────────────────────────────────────────────┤
│ LLM Self-Correction     │ Deterministic tool gating and symbolic critiquing            │
│ & Verification          │ (Gou et al., 2023; Asai et al., 2023; Weng et al., 2023).    │
└─────────────────────────┴──────────────────────────────────────────────────────────────┘
```

### 3.1 Criminal Network Analysis and Public Datasets
Criminal network analysis traditionally applies graph theory and social network analysis (SNA) to structured co-arrest or intelligence databases (Sparrow, 1991; Calderoni, 2012). Recent advancements focus on machine learning and graph neural networks for link prediction (Ahmadi et al., 2023; Cavallaro et al., 2020). However, existing CNA methods assume pre-structured relational tables, ignoring the messy, unstructured document layer where evidence is initially documented. SPYDER addresses this gap by evaluating the extraction and verification of co-offending ties directly from semi-synthetic narrative incident reports and telecommunication records.

### 3.2 Retrieval-Augmented Generation (RAG)
RAG architectures combine non-parametric dense or sparse document retrievers with parametric neural language models (Lewis et al., 2020; Guu et al., 2020). While RAG dramatically reduces hallucinations in general domain question answering, recent studies demonstrate that RAG models struggle with multi-hop reasoning, temporal constraints, and distractor suppression (Gao et al., 2023; Barnett et al., 2024). In investigative contexts, standard RAG lacks mechanisms to enforce strict legal standards of proof.

### 3.3 Evidence Attribution and Faithfulness
Evaluating whether generated claims are entailed by cited sources has been formalized through benchmarks such as TRUE (Honovich et al., 2022) and AttrEval (Bohnet et al., 2022). These frameworks demonstrate that language models frequently generate valid citations for false claims, or cite passages that do not strictly entail the asserted proposition. SPYDER operationalizes evidence attribution in an adversarial investigative setting where systems must explicitly substantiate target relationships.

### 3.4 Tool-Interactive Verification
Recent work in agentic reasoning demonstrates that decoupling generation from verification via external tools improves logical consistency (Gou et al., 2023 [CRITIC]; Asai et al., 2023 [Self-RAG]; Schick et al., 2023 [Toolformer]). Rather than relying on self-reflection—which suffers from sycophancy and shared error modes—SPYDER implements a deterministic, symbolic verifier operating as an isolated oracle.

### 3.5 Academic Positioning
We do **not** claim novelty for RAG, hypothesis verification, or criminal network analysis in isolation. The scientific contribution of SPYDER is the **controlled, reproducible experimental measurement of the trade-offs between RAG-only and verification-gated discovery across systematically degraded evidence conditions**, substantiated by independent rule-based evidentiary adjudication.

---

## 4. Dataset and Provenance

### 4.1 Real-World Dataset Backbone
The empirical foundation of the SPYDER benchmark is derived from the **Israel National Police (INP) Burglary Offender and Crime Network**, published by Ahmadi et al. (2023) as part of the European Union Horizon 2020 ROXANNE consortium (Grant Agreement No. 833635).

* **Dataset Characteristics:**
  - **Offender Population:** 7,105 unique anonymized individuals designated as `OID#xxx`.
  - **Crime Events:** 14,863 documented burglary incidents across residential and commercial sectors.
  - **Co-Offending Network:** Bipartite person-to-incident graph projecting to 14,863 co-offending links.
  - **Temporal Span:** Multi-year observation period spanning 2018–2021.
  - **Anonymization & Privacy:** Approved by INP legal counsel; individual names replaced by opaque numeric IDs; spatial locations min-max normalized; text descriptions embedded as vectors.
* **Licensing Distinction and Public Release Policy:**
  While the upstream GitHub repository containing the graph data is released under a BSD-3-Clause software license and the operational data was anonymized under GDPR standards, third-party permission to redistribute or re-host the raw law-enforcement graph files remains unverified. Accordingly, to uphold strict data-licensing compliance, the raw INP graph dataset is not redistributed directly within the public Git release. The public release includes the complete, sanitized semi-synthetic evidence corpus (`test_retrieval_documents.jsonl`), unlabelled target entity pairs, and frozen experiment outputs.

  > [!IMPORTANT]
  > **Benchmark Regeneration Limitation:** The complete 200-case test benchmark cannot be regenerated from the public repository alone without authorized access to the excluded raw dataset.

  Authorized researchers seeking to deterministically regenerate the benchmark ground truth must retrieve the raw network directly from the upstream ROXANNE repository (`https://github.com/erichoang/criminal-network-visualization`) and verify it against the documented SHA-256 checksum (`ba367e9123bfc7739c9f3bf686c39d00e733de8188e8471c608f4bf4eb679d84`).

### 4.2 Benchmark Evaluation Window
To establish a rigorous, realistic temporal boundary, SPYDER isolates a continuous six-month observation window:
$$\mathcal{W}_{\text{eval}} = [\text{2020-01-01 00:00:00}, \quad \text{2020-06-30 23:59:59}]$$

All target claims, incident reports, and telecommunication logs are strictly bounded by this window. Offenses occurring prior to January 1, 2020, or after June 30, 2020, are legally out-of-scope for the evaluation.

### 4.3 Component-Level Split Isolation
To guarantee zero contamination across experimental phases, the INP offender-crime graph was partitioned into mutually exclusive, disconnected subgraphs using weakly connected component decomposition:
* **Pilot Split:** 10 cases (5 positive, 5 negative) used for initial pipeline integration and smoke testing.
* **Development Split:** Reserved for pipeline prototyping.
* **Full Test Split:** 200 cases (100 positive, 100 negative) used for the frozen benchmark evaluation.
* **Reserve Split:** Quarantined for prospective testing.

Component isolation guarantees that no target entity, co-offender, or incident in the full test set shares any graph edge or entity reference with the pilot or development sets (`phase2_ground_truth_vault/split_manifest.json`, SHA-256: `04dc346d4628d1ad59d6b34d3580f6ddb40548e35921f48cc24a0d6a389d0ffd`).

---

## 5. Ground-Truth Construction and Operational Definitions

### 5.1 Operational Target Definition
In criminal justice research, establishing a relationship requires precise operationalization. Within SPYDER, the target relationship is defined as:
> **Target Relationship Definition:** Two target entities $u$ and $v$ share a qualifying co-offending relationship if and only if they are documented as joint participants in at least one solved residential or commercial burglary incident occurring within the evaluation window ($\mathcal{W}_{\text{eval}}$).

Under this definition:
1. **Crime Qualification:** The offense must be a burglary (residential or commercial). Traffic stops, field interviews, and general intelligence logs do not qualify.
2. **Temporal Window:** The offense date must fall within January 1–June 30, 2020.
3. **Official Clearance:** The narrative must document official case clearance (arrest, detention on scene, charges filed, or formal custody).
4. **Joint Culpability:** Both entities must be documented as co-participants, either directly (both named in report) or through an unbroken alias chain substantiated in the evidence.
5. **Circumstantial Exclusion:** Telecommunications (CDRs) alone, spatial proximity without joint commission, or concurrent independent offenses do **not** constitute a qualifying relationship.

### 5.2 Closed-World Benchmark Labels vs. Real-World Truth
A critical epistemic distinction must be maintained regarding benchmark labels:
* **Benchmark Positive ($y = 1$):** The pair possesses at least one documented qualifying joint burglary in the official INP registry during $\mathcal{W}_{\text{eval}}$.
* **Benchmark Negative ($y = 0$):** No qualifying joint burglary record exists in the selected database and temporal window.

> [!IMPORTANT]<br>
> A negative benchmark label does **not** prove physical-world innocence or non-association. It signifies closed-world non-observation in official police records during the selected window.

---

## 6. Synthetic Evidence Generation and Degradation Conditions

Because raw narrative investigative reports from the Israel National Police contain confidential operational intelligence and cannot be released publicly under GDPR, the evidence corpus was constructed via calibrated semi-synthetic generation. Generation scripts transformed the structured graph topologies into natural-language narratives and Call Detail Records.

### 6.1 Approved Evidence Types
The retrieval corpus is strictly restricted to two evidence schemas:
1. **`PoliceIncidentReport` (`incident_report`):** Formal police documentation recording incident date, geographic sector, entry method, stolen inventory, persons of interest, and narrative summary.
2. **`CallDetailRecord` (`call_detail_record`):** Telecommunication metadata recording timestamp, origin OID, destination OID, call duration, and cell tower sector.

All generated documents adhere to strict Pydantic schemas enforcing opaque document IDs (`DOC_IR_[a-f0-9]{8}`, `CDR_[a-f0-9]{8}`), zero leaked ground-truth labels, and zero synthetic generation metadata (`phase2_ground_truth_vault/schemas.py`).

### 6.2 Five Controlled Evidence Conditions
The 200-case test set is evenly divided across five controlled experimental conditions ($N = 40$ cases each; 20 positive, 20 negative):

```
                        EXPERIMENTAL EVALUATION CONDITIONS (N = 200)
┌──────────────────────┬──────────────────────────────────────────────────────────────────┐
│ Condition            │ Evidentiary Characteristics                                      │
├──────────────────────┼──────────────────────────────────────────────────────────────────┤
│ 1. Clean Evidence    │ Direct incident reports naming both entities; corroborating CDRs;│
│    (40 cases)        │ minimal background noise.                                        │
├──────────────────────┼──────────────────────────────────────────────────────────────────┤
│ 2. Alias Ambiguity   │ Accomplice identified in primary burglary report only by street  │
│    (40 cases)        │ moniker (e.g., 'The Lynx'); separate field record resolves alias.│
├──────────────────────┼──────────────────────────────────────────────────────────────────┤
│ 3. Missing Evidence  │ Primary joint crime report intentionally withheld from corpus;   │
│    (40 cases)        │ only peripheral CDR logs or independent records available.       │
├──────────────────────┼──────────────────────────────────────────────────────────────────┤
│ 4. Distractors       │ Qualifying crime reports buried among false alarm incident       │
│    (40 cases)        │ reports, sole-actor crimes, and unrelated community calls.       │
├──────────────────────┼──────────────────────────────────────────────────────────────────┤
│ 5. Mixed Difficulty  │ Highly noisy environment combining aliases, distractor reports,  │
│    (40 cases)        │ peripheral CDRs, and explicit unlinked notations.                │
└──────────────────────┴──────────────────────────────────────────────────────────────────┘
```

### 6.3 Quarantined Evidence Corpus Layout
The test environment comprises:
* **Sanitized Public Retrieval Corpus (`phase2_corpus/test_retrieval_documents.jsonl`):** 680 documents accessible to the systems at runtime.
* **Quarantined Internal Provenance (`phase2_corpus/test_internal_provenance.jsonl`):** 700 audit envelopes containing ground-truth generation rules and withheld records (including the 20 primary incident reports withheld in `missing_evidence`), strictly isolated from runtime access.

---

## 7. System Architecture and Implementation

Both systems share an identical retrieval pipeline, differing solely in the presence of the downstream verification gate.

```
                           SYSTEM ARCHITECTURAL COMPARISON
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

### 7.1 Shared Retrieval Infrastructure
The retrieval layer (`phase2_retrieval/retriever.py`) operates as a read-only indexer:
- **Indexing Engine:** Scikit-learn `TfidfVectorizer` paired with cosine similarity and deterministic tie-breaking.
- **Searchable Space:** Strictly restricted to the `text_content` field of sanitized retrieval documents.
- **Custom Tokenizer (`evidence_tokenizer`):** Deterministically preserves canonical entity IDs (`oid#4418`), extracts numeric sub-tokens (`4418`), preserves compound sector tokens (`central`, `west`), and normalizes case.
- **Query Formulation:** Formats queries strictly as `query = f"{entity_a} {entity_b}"`.
- **Budget:** Exactly $top\_k = 5$ documents returned per query.

### 7.2 System A: RAG-Only Experimental Arm
System A (`phase2_experiment/system_a.py`) represents the standard generative RAG paradigm:
1. Receives the top-5 retrieved document items.
2. Applies a textual extraction heuristic (`evaluate_rag_relationship`):
   - If both entities co-occur in any incident report $\rightarrow$ Emits `Supported`.
   - If both entities co-occur in any Call Detail Record $\rightarrow$ Emits `Supported` (incurs telecommunication inference).
   - If an incident report mentions entity $u$ alongside a street moniker, and entity $v$ is mentioned in any other retrieved document $\rightarrow$ Emits `Supported` (assumes moniker links to partner).
   - If no co-occurrence or communication is identified $\rightarrow$ Emits `Insufficient Evidence`.
3. Does **not** verify incident dates, crime types, clearance status, or alias attributions.

### 7.3 System B: RAG + Verification Experimental Arm
System B (`phase2_experiment/system_b.py`) implements evidence-grounded verification:
1. Receives the identical top-5 retrieved documents as System A.
2. Extracts the unique, valid document IDs from the retrieved items.
3. Formulates a hypothesis and invokes the external verification tool:
   ```python
   verification_result = verify_hypothesis(
       entity_a=entity_a,
       entity_b=entity_b,
       evidence_ids=valid_doc_ids
   )
   ```
4. **Symbolic Verification Engine (`HypothesisVerifier`):**
   - Validates that every cited document ID exists and is non-empty.
   - Inspects incident dates against $\mathcal{W}_{\text{eval}}$ (`2020-01-01` to `2020-06-30`).
   - Verifies offense category is residential or commercial burglary.
   - Verifies explicit case clearance (e.g., "cleared by arrest", "detained on scene").
   - Traces alias attribution chains across cited documents.
   - Checks for global contradictions (e.g., continuous custodial detention precluding community offenses).
5. **Decision Conditioning:** Directly maps the verifier outcome to the system decision:
   - `Supported` $\rightarrow$ Positive prediction ($y_{\text{pred}} = 1$).
   - `Unsupported` $\rightarrow$ Negative prediction ($y_{\text{pred}} = 0$).
   - `Insufficient Evidence` $\rightarrow$ Negative prediction / Abstention ($y_{\text{pred}} = 0$).

---

## 8. Experimental Design and Evaluation Protocol

### 8.1 Protocol Integrity and Quarantine
Execution adhered to strict anti-leakage safeguards:
* Unlabelled target pairs were passed to the runner via `phase2_experiment/test_target_pairs.json` containing only `[entity_a, entity_b]`.
* Runtime environments were prohibited from importing vault schemas, ground truth, or provenance.
* Evaluator scoring (`phase2_experiment/evaluator.py`) occurred post-execution by comparing raw system output files against the quarantined vault manifest.

### 8.2 Evaluation Metrics
We report standard binary classification metrics alongside evidentiary soundness:
* **True Positives (TP), False Positives (FP), True Negatives (TN), False Negatives (FN)**
* **Accuracy:** $(TP + TN) / N$
* **Precision:** $TP / (TP + FP)$ (defined as `null` if $TP + FP = 0$)
* **Recall (Sensitivity):** $TP / (TP + FN)$
* **Specificity:** $TN / (TN + FP)$
* **False Positive Rate (FPR):** $FP / (FP + TN) = 1 - \text{Specificity}$
* **F1 Score:** $2 \cdot (\text{Precision} \cdot \text{Recall}) / (\text{Precision} + \text{Recall})$
* **Confidence Intervals:** 95% Wilson Score intervals with continuity correction for all proportions:
  $$w = \frac{p + \frac{z^2}{2n} \pm z\sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}, \quad z = 1.95996$$
* **Evidentiary Soundness:** Fraction of asserted positive predictions grounded in verified qualifying crime evidence.

---

## 9. Benchmark Results

### 9.1 Overall Benchmark Performance
Table 1 presents the overall classification results across the frozen 200-case evaluation set.

**Table 1: Overall Classification Performance ($N = 200$)**

| Metric | System A (RAG-Only) | System B (RAG + Verifier) | Delta ($\Delta_{B - A}$) |
| :--- | :---: | :---: | :---: |
| **Total Test Cases ($N$)** | 200 | 200 | 0 |
| **True Positives (TP)** | 100 | 40 | -60 |
| **False Positives (FP)** | 60 | 0 | -60 |
| **True Negatives (TN)** | 40 | 100 | +60 |
| **False Negatives (FN)** | 0 | 60 | +60 |
| **Accuracy** | **70.00%** ($140/200$)<br>95% CI: [63.32%, 75.93%] | **70.00%** ($140/200$)<br>95% CI: [63.32%, 75.93%] | 0.00% |
| **Precision** | **62.50%** ($100/160$)<br>95% CI: [54.79%, 69.63%] | **100.00%** ($40/40$)<br>95% CI: [91.24%, 100.00%] | **+37.50%** |
| **Recall (Sensitivity)** | **100.00%** ($100/100$)<br>95% CI: [96.30%, 100.00%] | **40.00%** ($40/100$)<br>95% CI: [30.94%, 49.80%] | **-60.00%** |
| **Specificity** | **40.00%** ($40/100$)<br>95% CI: [30.94%, 49.80%] | **100.00%** ($100/100$)<br>95% CI: [96.30%, 100.00%] | **+60.00%** |
| **False Positive Rate (FPR)** | **60.00%** ($60/100$)<br>95% CI: [50.20%, 69.06%] | **0.00%** ($0/100$)<br>95% CI: [0.00%, 3.70%] | **-60.00%** |
| **F1 Score** | **0.7692** | **0.5714** | -0.1978 |

### 9.2 Condition-by-Condition Analysis
Table 2 breaks down performance across the five experimental conditions ($N = 40$ cases each; 20 positive, 20 negative).

**Table 2: Condition-Specific Classification Breakdown**

| Condition | Metric | System A (RAG-Only) | System B (RAG + Verifier) | Operational Takeaway |
| :--- | :--- | :---: | :---: | :--- |
| **1. Clean Evidence** | Accuracy | 85.0% ($34/40$) | **100.0%** ($40/40$) | System B achieves perfect accuracy; |
| ($N = 40$) | Precision | 76.9% ($20/26$) | **100.0%** ($20/20$) | System A produces 6 false positives on negative pairs. |
| | Recall | 100.0% ($20/20$) | 100.0% ($20/20$) | |
| | Specificity | 70.0% ($14/20$) | **100.0%** ($20/20$) | |
| **2. Alias Ambiguity** | Accuracy | 50.0% ($20/40$) | 50.0% ($20/40$) | Polar opposite error modes: |
| ($N = 40$) | Precision | 50.0% ($20/40$) | `null` ($0/0$) | System A has 20 FPs; |
| | Recall | 100.0% ($20/20$) | 0.0% ($0/20$) | System B has 20 FNs. |
| | Specificity | 0.0% ($0/20$) | **100.0%** ($20/20$) | |
| **3. Missing Evidence** | Accuracy | 87.5% ($35/40$) | 50.0% ($20/40$) | System B correctly abstains (20 FNs); |
| ($N = 40$) | Precision | 80.0% ($20/25$) | `null` ($0/0$) | System A makes 20 ungrounded positive guesses |
| | Recall | 100.0% ($20/20$) | 0.0% ($0/20$) | based solely on phone calls. |
| | Specificity | 75.0% ($15/20$) | **100.0%** ($20/20$) | |
| **4. Distractors** | Accuracy | 77.5% ($31/40$) | **100.0%** ($40/40$) | System B perfectly filters distractor noise; |
| ($N = 40$) | Precision | 69.0% ($20/29$) | **100.0%** ($20/20$) | System A produces 9 false positives on distractors. |
| | Recall | 100.0% ($20/20$) | 100.0% ($20/20$) | |
| | Specificity | 55.0% ($11/20$) | **100.0%** ($20/20$) | |
| **5. Mixed Difficulty** | Accuracy | 50.0% ($20/40$) | 50.0% ($20/40$) | Combined stress test: |
| ($N = 40$) | Precision | 50.0% ($20/40$) | `null` ($0/0$) | System A predicts positive for 100% of cases; |
| | Recall | 100.0% ($20/20$) | 0.0% ($0/20$) | System B predicts negative for 100% of cases. |
| | Specificity | 0.0% ($0/20$) | **100.0%** ($20/20$) | |

---

## 10. Independent Rule-Based Evidentiary Adjudication

### 10.1 Adjudication Protocol and Separation
To ensure unbiased evaluation, the Phase 2G.4 audit implemented a dedicated, rule-based adjudication engine (detailed below in Table 3 and Section 10.2). The adjudicator operated directly on raw evidence text retrieved by the systems, completely isolated from `HypothesisVerifier` code, regex patterns, or scoring routines.

Every positive prediction asserted by either system ($N = 160$ for System A; $N = 40$ for System B) was evaluated against five transparent rules:
1. **Rule 1 (CDR Alone):** Telecommunication CDRs alone cannot establish a burglary offense $\rightarrow$ Marked `Unsupported`.
2. **Rule 2 (Direct Joint Burglary):** A qualifying incident report within $\mathcal{W}_{\text{eval}}$ cleared by arrest documenting joint co-participation $\rightarrow$ Marked `Supported`.
3. **Rule 3 (Explicit Unlinked Negation):** Police narratives explicitly noting the target as unlinked (e.g., `(Unlinked to OID#...)`) $\rightarrow$ Marked `Unsupported`.
4. **Rule 4 (Field Interview Only):** Field intelligence interviews of an isolated subject without a crime report $\rightarrow$ Marked `Unsupported`.
5. **Rule 5 (Unresolved Accomplice Moniker):** Burglary narrative names one target entity and an unidentified accomplice moniker, but no cited document resolves that moniker to the second entity $\rightarrow$ Marked `Indeterminate` (relationship unresolved on cited evidence alone).

> [!NOTE]<br>
> This adjudication constitutes an **independent rule-based audit**, not human-panel ground truth. Automated rules cannot capture subtle prosecutorial nuances.

### 10.2 Adjudication Results Breakdown
Table 3 details the independent evidentiary adjudication outcomes.

**Table 3: Independent Evidentiary Adjudication of Positive Predictions**

| Adjudication Metric | System A (RAG-Only) | System B (RAG + Verifier) | Operational Meaning |
| :--- | :---: | :---: | :--- |
| **Total Positive Predictions ($N_{\text{pos}}$)** | **160** | **40** | System A asserts positive in 80% of all cases; System B in 20%. |
| **Adjudicated `Supported`** | **18** (11.25%) | **40** (100.00%) | Validated joint burglary co-offending documented. |
| **Adjudicated `Unsupported`** | **131** (81.88%) | **0** (0.00%) | Affirmatively fails legal or factual qualification. |
| **Adjudicated `Indeterminate`** | **11** (6.88%) | **0** (0.00%) | Incomplete evidence; unverified accomplice moniker. |
| **Adjudication Coverage** | 93.12% ($149/160$) | 100.00% ($40/40$) | Resolved classification rate ($Supported + Unsupported$). |
| **Unresolved Cases Rate** | 6.88% ($11/160$) | 0.00% ($0/40$) | Cases marked `Indeterminate`. |
| **Evidentiary Soundness (All Positives)** | **11.25%** ($18/160$)<br>95% CI: [7.24%, 17.08%] | **100.00%** ($40/40$)<br>95% CI: [91.24%, 100.00%] | **System B achieves an 8.9x advantage in rule-audited soundness on this benchmark ($40/40$ vs. $18/160$).** |
| **Evidentiary Soundness (Resolved Only)** | **12.08%** ($18/149$)<br>95% CI: [7.78%, 18.29%] | **100.00%** ($40/40$)<br>95% CI: [91.24%, 100.00%] | Computed over resolved cases only ($18 / [18 + 131]$). |

### 10.3 Failure Taxonomy of System A Positive Predictions ($N = 160$)
The 160 positive predictions made by System A decompose into five distinct categories:
1. **`DIRECT_VERIFIED_BURGLARY` (18 cases, 11.25%):** All 18 cases occurred in the `distractors` condition, where System A successfully retrieved and cited the primary joint burglary report.
2. **`CDR_COMMUNICATION_ALONE` (82 cases, 51.25%):** System A cited wiretap CDR logs alone. While 80 of these pairs were true co-offenders on the benchmark, the cited evidence contained zero proof of an offense.
3. **`EXPLICIT_UNLINKED_NEGATION` (40 cases, 25.00%):** In negative cases within `alias_ambiguity` (20 cases) and `mixed_difficulty` (20 cases), System A matched target entities in distractor incident reports that explicitly stated: `(Unlinked to OID#xxx)`. System A asserted co-offending despite explicit textual negation.
4. **`FIELD_INTERVIEW_ONLY_NO_CRIME` (9 cases, 5.62%):** Intelligence field interviews or traffic stops naming an isolated suspect without any burglary crime report cited.
5. **`UNRESOLVED_ACCOMPLICE_MONIKER` (11 cases, 6.88%):** Qualifying burglary reports citing one entity and an unverified moniker, lacking the corresponding alias resolution field report.

### 10.4 The Spurious Precision Phenomenon
A central empirical finding is the dramatic decoupling between **Benchmark Precision** and **Evidentiary Soundness**:

```
                                SYSTEM A (RAG-Only)
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Benchmark Precision: 62.50% (100 / 160)                                         │
│ ├── 100 cases had ground-truth label = 1 (Scored as True Positives)             │
│ └── 60 cases had ground-truth label = 0 (Scored as False Positives)             │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Independent Evidentiary Soundness: 11.25% (18 / 160)                            │
│ ├── 18 cases cited valid, verified joint burglary incident reports              │
│ ├── 82 cases cited wiretap CDRs alone (spurious "lucky" true positives)         │
│ ├── 49 cases cited unlinked negations or single-person field interviews         │
│ └── 11 cases cited unresolved accomplice monikers                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Standard benchmark scoring credits System A with 100 True Positives because $y_{\text{pred}} == y_{\text{true}} == 1$. However, in **82 of those 100 cases**, System A cited only a phone call. The system guessed correctly on the benchmark, but its decision was evidentiary unsound. When evaluated on the factual sufficiency of the cited evidence, System A collapses to **11.25%**, whereas System B remains at **100.0%**.

---

## 11. Statistical Analysis

### 11.1 Paired 2x2 Contingency Table
Because both systems were evaluated on the identical 200 test cases, their classification outcomes form a paired $2 \times 2$ contingency table (Table 4).

**Table 4: Paired 2x2 Contingency Table of Classification Outcomes**

| | System B Correct ($y_{B} = y$) | System B Incorrect ($y_{B} \ne y$) | Row Totals |
| :--- | :---: | :---: | :---: |
| **System A Correct ($y_{A} = y$)** | $a = 80$ (Both Correct) | $b = 60$ (A Correct, B Incorrect) | 140 (70.0%) |
| **System A Incorrect ($y_{A} \ne y$)** | $c = 60$ (B Correct, A Incorrect) | $d = 0$ (Both Incorrect) | 60 (30.0%) |
| **Column Totals** | 140 (70.0%) | 60 (30.0%) | **$N = 200$ (100.0%)** |

- **Cell $a = 80$:** 40 True Positives where both systems correctly identified qualifying burglaries (`clean_evidence` and `distractors`), and 40 True Negatives where both systems correctly rejected negative pairs.
- **Cell $b = 60$:** Discordant cases favoring System A. All 60 cases represent **False Negatives of System B** (20 in `alias_ambiguity`, 20 in `missing_evidence`, 20 in `mixed_difficulty`).
- **Cell $c = 60$:** Discordant cases favoring System B. All 60 cases represent **False Positives of System A** (6 in `clean_evidence`, 20 in `alias_ambiguity`, 5 in `missing_evidence`, 9 in `distractors`, 20 in `mixed_difficulty`).
- **Cell $d = 0$:** Zero cases where both systems were simultaneously incorrect.

### 11.2 Statistical Formulations and Reconciled Values
We evaluate paired marginal symmetry using three standard statistical formulations:

#### 1. Uncorrected McNemar Chi-Square Test
$$\chi^2 = \frac{(b - c)^2}{b + c} = \frac{(60 - 60)^2}{60 + 60} = \frac{0}{120} = \mathbf{0.000000}, \quad p = \mathbf{1.000000} \quad (\text{df} = 1)$$

#### 2. Edwards Continuity-Corrected McNemar Test
$$\chi^2_{\text{Edwards}} = \frac{(|b - c| - 1)^2}{b + c} = \frac{(|60 - 60| - 1)^2}{120} = \frac{1}{120} \approx \mathbf{0.008333}$$
$$p = P(\chi^2_1 \ge 1/120) = \text{scipy.stats.chi2.sf}(1/120, \text{df}=1) \approx \mathbf{0.927264}$$

#### 3. Exact Two-Sided Binomial McNemar Test
Under the null hypothesis $H_0: p_{\text{discordant}} = 0.5$ with $n = 120$ discordant trials:
$$b \sim \text{Binomial}(120, 0.5), \quad k = 60 \implies p = \mathbf{1.000000}$$

### 11.3 Resolving Prior Literature Conflation
Prior working drafts conflated the Edwards continuity-corrected statistic ($\chi^2 \approx 0.00833$) with the exact binomial p-value ($p = 1.0000$). We clarify:
* Under the chi-square distribution with $\text{df}=1$, $\chi^2 = 0.008333$ has survival probability $p = 0.927264$.
* The exact binomial test yields $p = 1.000000$ without generating a chi-square statistic.

### 11.4 Why Non-Significance Does Not Mean Equivalence
A critical scientific principle must be emphasized: **A p-value of $p \ge 0.927$ does NOT indicate that System A and System B are equivalent.**

McNemar's test evaluates solely whether the *total count of marginal errors* differs between systems ($b \ne c$). When $b = 60$ and $c = 60$, marginal error counts are identical ($140/200 = 70.0\%$ accuracy for both). However, the two systems commit **qualitatively orthogonal errors**:
* **System A Errors:** 100% Type I errors (60 False Positives, 0 False Negatives). System A hallucinates relationships where none exist.
* **System B Errors:** 100% Type II errors (0 False Positives, 60 False Negatives). System B abstains whenever evidence is incomplete.

In high-stakes investigative intelligence, asserting unsupported co-offending claims carries substantially greater operational and ethical risk than withholding judgment pending corroborating evidence. The systems inhabit fundamentally different operational profiles.

---

## 12. Discussion

### 12.1 The Value of the Verification Gate
The experimental results demonstrate that symbolic hypothesis verification provides an absolute shield against false-positive hallucination:
* Across 100 negative test cases containing sophisticated distractors, unlinked police records, and misleading CDR logs, System B achieved **$0.0\%$ False Positive Rate** ($0/100$ FPs, $100.0\%$ Specificity).
* System B achieved **$100.0\%$ evidentiary soundness** across all asserted positive claims. Every positive prediction was verified by a cleared residential burglary incident report within the six-month evaluation window.

### 12.2 Deconstructing the Recall Collapse
Why did System B's recall drop to $40.0\%$ ($40/100$ TPs)? Analyzing the 60 false negatives reveals two distinct causes:
1. **Justified Evidentiary Abstention ($N = 20$ in `missing_evidence`):**<br>
   In `missing_evidence`, primary crime reports were intentionally withheld by protocol. System A predicted positive based on CDR call logs alone. System B's verifier correctly recognized that phone logs do not prove burglary co-offending and returned `Insufficient Evidence`. Here, System B's "error" on the benchmark was the **only evidentially sound decision**.
2. **The Single-Turn Retrieval Bottleneck ($N = 40$ in `alias_ambiguity` and `mixed_difficulty`):**<br>
   In alias-ambiguous cases, primary burglary reports and alias resolution field interviews were both present in the corpus. However, System B issued a single initial retrieval query formatted as `query = f"{u} {v}"`. In cases where entity $v$ was known only as 'The Lynx', the initial query retrieved the burglary report but failed to rank the separate field interview in the top-5 results. Because the alias chain was broken, the verifier correctly declined to certify the hypothesis.
   - **Takeaway:** The recall bottleneck lies in the **retriever**, not the verifier. The verifier performed its duty: it refused to guess.

---

## 13. Threats to Validity and Limitations

### 13.1 Threats to Internal Validity
* **Single-Turn Retrieval Bias:** Evaluating systems in a static, single-turn retrieval regime unfairly penalizes verification when multi-hop evidence assembly is required.
* **Regex Pattern Fragility:** While `HypothesisVerifier` is deterministic, its extraction rules rely on curated regex patterns. Phrasal variations in narrative generation can lead to extraction failures.

### 13.2 Threats to External Validity
* **Synthetic Evidence Realism:** Although calibrated against empirical police network distributions, synthetic incident reports cannot replicate the linguistic idiosyncrasies, handwriting artifacts, and dialect variations of authentic police records.
* **Narrow Temporal and Jurisdictional Scope:** The benchmark evaluates a single crime category (burglary) within a six-month window in a single national jurisdiction. Generalizability to narcotics networks, financial fraud, or violent syndicates remains unvalidated.
* **Sample Size:** While 200 cases is substantial for controlled multi-condition evaluation, larger corpora are required to assess extreme tail distributions.

---

## 14. Ethical Considerations and Responsible Use

### 14.1 Operational Disclaimer
> [!CAUTION]<br>
> **SPYDER is a research prototype for evaluating evidence verification architectures. It is NOT an operational law enforcement tool, does NOT predict criminality, does NOT prove legal guilt, and must NEVER be used to justify real-world surveillance, detention, or charging decisions.**

### 14.2 Harm Prevention and Due Process
* **Association is Not Guilt:** Unchecked algorithmic CNA risks criminalizing individuals based on familial, social, or geographic proximity. System A's $60.0\%$ False Positive Rate demonstrates the extreme danger of ungrounded RAG in criminal justice.
* **Human-in-the-Loop Requirement:** Autonomous agents must never make dispositive investigative determinations. Systems must function strictly as transparent decision-support tools that surface source citations for human prosecutorial review.

---

## 15. Conclusion and Future Work

### 15.1 Summary of Contributions
1. **Benchmark Establishment:** We formalize a 200-case frozen, leak-free benchmark for evidence-grounded criminal relationship discovery across five controlled degradation conditions.
2. **Empirical Measurement of Verification:** We demonstrate that explicit symbolic verification eliminates false-positive relationship predictions ($FPR = 0.0\%$, Specificity = $100.0\%$) and provides an **8.9x advantage in rule-audited evidentiary soundness** ($100.0\%$ vs. $11.25\%$, an $88.75$ percentage point increase) on this benchmark over standard RAG.
3. **Exposing Spurious Precision:** We prove that high benchmark precision in generative RAG can be an artifact of lucky guessing on non-qualifying evidence.
4. **Statistical Reconciliation:** We provide exact, non-conflated McNemar formulations and explain why marginal symmetry masks polar-opposite error modes.

### 15.2 Future Work: The Phase 3 Architecture
To resolve the recall bottleneck without compromising evidentiary soundness, future research should develop:
1. **Iterative Multi-Hop Retrieval:** Equipping the agent to reformulate search queries dynamically when an unresolved alias or missing record is identified.
2. **Dense-Sparse Hybrid Retrieval:** Integrating dense vector embeddings with BM25/TF-IDF to overcome exact-token mismatch in alias resolution.
3. **Active Information Requests:** Enabling the agent to generate targeted investigative subpoenas or field requests when evidence is insufficient.

---

## 16. Reproducibility and Artifact Integrity

### 16.1 Repository Layout
```
Creators-SPYDER/
├── docs/                                    # Canonical academic manuscript
├── phase2_corpus/                           # Sanitized retrieval documents, provenance, & tests
├── phase2_retrieval/                        # TF-IDF indexer and search service & tests
├── phase2_verification/                     # Isolated HypothesisVerifier tool & tests
├── phase2_experiment/                       # Runner, System A, System B, evaluator, & tests
├── phase2_public_artifact_hash_manifest.json# Cryptographic hash registry (6 public frozen artifacts)
├── DATASET_NOTICE.md                        # Dataset provenance and licensing terms
├── LICENSE                                  # MIT License (original SPYDER code only)
├── requirements.txt                         # Dependency specifications
└── README.md                                # Quickstart and project overview
```
*(Quarantined ground-truth vault, per-case predictions, and raw dataset slices are held offline outside the public release to ensure blind evaluation and licensing compliance.)*

### 16.2 Cryptographic Verification
The 6 public frozen artifacts match their established SHA-256 baselines exactly:
* `phase2_experiment/test_target_pairs.json`: `125e012b794440c6db8170bb4aa9c385472780bddc1174c6ba7e76096c711cd0`
* `phase2_corpus/test_retrieval_documents.jsonl`: `72d00c6250a73a385fef10792b38fa30aaae8b8a96dff94420e092980caf1349`
* `phase2_corpus/retrieval_documents.jsonl`: `a802aace8dd8c804d03e08252ec3241e23a7a500ed5dac63ccf17aa0f1293ded`
* `phase2_corpus/internal_provenance.jsonl`: `ae29dcd873a3f87f01dff4e5dceb3edd041caf64e21f7065d74114ad2f9287bc`
* `phase2_experiment/outputs/full_test_run_manifest.json`: `56fb9056e33bb637dba35e58074b5c0d6362646fc203cd2f9292152adfa054b7`
* `phase2_experiment/outputs/full_test_scoring_report.json`: `146e479f94f01c4190418893958c4ab343571b025f6a25653d1a9caa9083e316` (aggregate-only)

Quarantined offline assets (test ground truth, test provenance, historical pre-audit score report, and per-case model predictions) are held outside the public release to preserve blind benchmark integrity:
* `phase2_ground_truth_vault/test_manifest.json`: `0f5bdc943f9fb51314efb2b1fec8baa2828772feb040980585d0b18f892f12af`
* `phase2_ground_truth_vault/test_ground_truth.json`: `3f1e9021538be563ea8de015b076ca3a9e2bb75684ae04dcdbd52c7f3e7b8e33`
* `phase2_corpus/test_internal_provenance.jsonl`: `e32a102d6a74469799d2488404b049bd602543ff4dba878d26024ef096f77555`
* `phase2_experiment/outputs/original_full_test_scoring_report.json`: `3fedc24e87e75400a21f8aca21a3b6edb2797121ecfe0ef4706e53d9d72c249c`
* `phase2_experiment/outputs/system_a_full_test_outputs.json`: `5c804673b4dc70b8fbe3aa70024d19100f0ed661e35a141db27353f523bf7e8b`
* `phase2_experiment/outputs/system_b_full_test_outputs.json`: `510ab08293a094ceaf0b161219e6c3da538bdfdc3a4045953e7b846f6874ea31`

### 16.3 Regression Command and Verification Modes
* **Full Internal Benchmark Suite (with Quarantined Vault and Upstream Data):**
  ```bash
  python -m pytest phase2_ground_truth_vault/tests phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests -v
  # Output: 152 passed in ~3s (Exit Code 0)
  ```
* **Fresh Public Clone (Blinded Release without Raw Police Data):**
  ```bash
  python -m pytest phase2_corpus/tests phase2_retrieval/tests phase2_verification/tests phase2_experiment/tests -v
  # Output: 120 passed in ~3s (Exit Code 0)
  ```

---

## 17. References

1. Ahmadi, Z., Nguyen, H. H., Zhang, Z., Bozhkov, D., Kudenko, D., Jofre, M., Calderoni, F., Cohen, N., & Solewicz, Y. (2023). Inductive and transductive link prediction for criminal network analysis. *Journal of Computational Science*, 72, Article 102063. DOI: [10.1016/j.jocs.2023.102063](https://doi.org/10.1016/j.jocs.2023.102063).
2. Asai, A., Sewon, M., Jiang, Z., Chen, X., Zettlemoyer, L., Yih, W.-t., & Hajishirzi, H. (2023). Self-RAG: Learning to retrieve, generate, and critique through self-reflection. *International Conference on Learning Representations (ICLR 2024)*. arXiv: [2310.11511](https://arxiv.org/abs/2310.11511).
3. Barnett, S., Kurniawan, S., Thudumu, S., Brannelly, Z., & Abdelrazek, M. (2024). Seven failure points when engineering a retrieval augmented generation system. *IEEE Software*. DOI: [10.1109/MS.2024.3356611](https://doi.org/10.1109/MS.2024.3356611).
4. Bohnet, B., Collins, V., Gupta, N., et al. (2022). Attributed question answering: Evaluation and modeling for attributed natural language generation. *arXiv preprint*, arXiv: [2212.08037](https://arxiv.org/abs/2212.08037).
5. Calderoni, F. (2012). The structure of drug trafficking mafias: The ‘Ndrangheta and cocaine. *Crime, Law and Social Change*, 58(3), 321–349. DOI: [10.1007/s10611-012-9387-9](https://doi.org/10.1007/s10611-012-9387-9).
6. Cavallaro, L., Ficara, A., De Meo, P., Fiumara, G., Celesti, A., & Catanese, S. (2020). Disrupting resilient criminal networks through data analysis: The case of the Sicilian Mafia. *PLOS ONE*, 15(8), e0236476. DOI: [10.1371/journal.pone.0236476](https://doi.org/10.1371/journal.pone.0236476).
7. Edwards, A. L. (1948). Note on the "correction for continuity" in McNemar's test. *Psychometrika*, 13(3), 185–187. DOI: [10.1007/BF02289261](https://doi.org/10.1007/BF02289261).
8. Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., & Wang, H. (2023). Retrieval-augmented generation for large language models: A survey. *arXiv preprint*, arXiv: [2312.10997](https://arxiv.org/abs/2312.10997).
9. Gou, Z., Shao, Z., Gong, Y., Shen, Y., Yang, Y., Huang, M., Duan, N., & Chen, W. (2023). CRITIC: Large language models can self-correct with tool-interactive critiquing. *International Conference on Learning Representations (ICLR 2024)*. arXiv: [2305.11738](https://arxiv.org/abs/2305.11738).
10. Guu, K., Lee, K., Tung, Z., Pasupat, P., & Chang, M. (2020). Retrieval augmented language model pre-training. *International Conference on Machine Learning (ICML 2020)*, PMLR 119:3929–3938.
11. Honovich, O., Aharoni, R., Herzig, J., et al. (2022). TRUE: Re-evaluating factual consistency evaluation approaches of abstractive summarization. *Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing (EMNLP 2022)*, pp. 3905–3920.
12. Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems (NeurIPS 2020)*, 33, 9459–9474.
13. Rashkin, H., Ruder, S., Zhao, D., et al. (2021). Increasing faithfulness in knowledge-grounded dialogue with controllable features. *Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics (ACL 2021)*, pp. 704–718.
14. Robertson, S. E., & Sparck Jones, K. (1976). Relevance weighting of search terms. *Journal of the American Society for Information Science*, 27(3), 129–146. DOI: [10.1002/asi.4630270302](https://doi.org/10.1002/asi.4630270302).
15. Rosenfeld, R. (1990s). St. Louis Homicide Project: Bipartite Person-Crime Network. *KONECT / Pajek Repository*.
16. Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N., & Scialom, T. (2023). Toolformer: Language models can teach themselves to use tools. *Advances in Neural Information Processing Systems (NeurIPS 2023)*, 36.
17. Sparrow, M. K. (1991). The application of network analysis to criminal intelligence: An assessment of the prospects. *Social Networks*, 13(3), 251–274. DOI: [10.1016/0378-8733(91)90008-8](https://doi.org/10.1016/0378-8733(91)90008-8).
18. Weng, Y., Zhu, M., Xia, F., Li, B., He, S., Liu, K., & Zhao, J. (2023). Large language models are better reasoners with verification. *arXiv preprint*, arXiv: [2212.09561](https://arxiv.org/abs/2212.09561).
19. Wilson, E. B. (1927). Probable inference, the law of population, and the known effect of sample size. *Journal of the American Statistical Association*, 22(158), 209–212. DOI: [10.1080/01621459.1927.10502953](https://doi.org/10.1080/01621459.1927.10502953).
