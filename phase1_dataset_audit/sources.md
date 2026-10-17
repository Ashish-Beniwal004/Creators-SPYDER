# Project Sources, Provenance, and Access Reference

This document catalogs the official research publications, direct download routes, data repositories, licenses, and access procedures for all primary and secondary datasets audited during Phase 1 of the **Evidence-Grounded Agentic Criminal Network Investigation** project.

---

## 1. Primary Recommended Dataset Backbone

### Israel Burglary Offender & Crime Networks (INP / ROXANNE)
* **Original Research Paper:**
  Zahra Ahmadi, Hoang H. Nguyen, Zijian Zhang, Dmytro Bozhkov, Daniel Kudenko, Maria Jofre, Francesco Calderoni, Noa Cohen, and Yosef Solewicz. *"Inductive and Transductive Link Prediction for Criminal Network Analysis."* **Journal of Computational Science**, Vol. 72, Article 102063, September 2023.
  * **DOI:** [10.1016/j.jocs.2023.102063](https://doi.org/10.1016/j.jocs.2023.102063)
  * **EU Project Affiliation:** Horizon 2020 ROXANNE (Real-time network, text, and speaker analytics for combating organized crime), Grant Agreement No. 833635.
* **Official Code and Dataset Repository:**
  * **GitHub:** [https://github.com/erichoang/criminal-network-visualization](https://github.com/erichoang/criminal-network-visualization)
* **Direct Raw Download Links:**
  * **Full Offender Network (15.55 MB):**
    `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_inp_burglary_offender_id_network.json`
  * **Full Crime Network (88.31 MB):**
    `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_inp_burglary_v2_crime_id_network.json`
  * **Recommended 6-Month Evaluation Slice (1.14 MB / 1,165 KB):**
    `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json`
  * **CI/Test 1-Month Slice (206 KB):**
    `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-01-31.json`
* **Dataset License & Terms of Use:**
  * **Software License Distinction:** The upstream GitHub repository software is released under a BSD-3-Clause license (Copyright 2021 Consortium Board ROXANNE).
  * **Redistribution Terms & Restrictions:** The software license does not automatically grant third-party rights to redistribute or re-host the underlying Israel National Police operational dataset or its derived temporal slices. While anonymized under GDPR standards and approved by INP legal counsel for the ROXANNE project, third-party redistribution permission remains unverified. Accordingly, raw dataset files are excluded from redistribution in this repository.
  * **Privacy & Anonymization:** Approved by legal counsel of the Israel National Police; GDPR-compliant; individual offender names anonymized as `OID#xxx`; spatial coordinates min-max scaled; textual case reports parameterized as embedding vectors.
* **Access Method:** Direct public HTTPS download from upstream repository without registration or authentication (see URLs above).

---

## 2. Secondary Real-World Datasets

### Israel LEA Telephone Wiretap Networks (Case 1 & Case 2)
* **Source Repository:** ROXANNE Consortium / Israel National Police.
* **Direct Raw Download Links:**
  * **Case 1 (8.54 KB, 33 speakers, 38 edges):**
    `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_case1_speakers.json`
  * **Case 2 (42.35 KB, 124 speakers, 178 edges):**
    `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/israel_lea_case2_speakers.json`
* **Format:** NDJSON (Newline Delimited JSON).
* **Usage in Project:** Calibrating synthetic call-frequency and degree distributions for synthetic CDR evidence generation.

### Moreno St. Louis Crime Network
* **Original Paper:**
  Richard Rosenfeld. *St. Louis Homicide Project*, 1990s. Hosted by Pajek, KONECT, and UC Irvine Network Data Repository.
* **Direct Raw Download Link:**
  `https://raw.githubusercontent.com/erichoang/criminal-network-visualization/main/datasets/preprocessed/moreno_crime.json`
* **Format:** NDJSON (829 persons, 551 crimes, 3,034 bipartite edges).
* **License:** Public Domain / Academic Research.

### Montagna Operation Sicilian Mafia Network
* **Authors:** Lucia Cavallaro, Annamaria Ficara, Pasquale De Meo, Giacomo Fiumara, Antonio Celesti, and Salvatore Catanese.
* **Paper:** *"Disrupting Resilient Criminal Networks through Data Analysis: The Case of the Sicilian Mafia."* **PLOS ONE**, 2020.
* **Data Repositories:**
  * **Zenodo:** [https://zenodo.org/records/3943343](https://zenodo.org/records/3943343) (DOI: 10.5281/zenodo.3943343)
  * **GitHub:** [https://github.com/lcucav/criminal-nets](https://github.com/lcucav/criminal-nets)
* **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).

### Project Caviar Wiretap Network
* **Author:** Carlo Morselli.
* **Book / Source:** *Inside Criminal Networks*, Springer / Routledge, 2009.
* **Repository:** Mitchell Centre for Social Network Analysis Covert Networks (UCINET).
  * **URL:** [https://sites.google.com/site/ucinetsoftware/datasets/covert-networks](https://sites.google.com/site/ucinetsoftware/datasets/covert-networks)
* **R Package Distribution:** `networkdata` R package by David Schoch (`data("caviar")`).

---

## 3. Financial & Benchmark Datasets

### Elliptic Bitcoin Transaction Dataset
* **Authors:** Mark Weber, Domenic Puzis, et al. (MIT-IBM Watson AI Lab & Elliptic).
* **Paper:** *"Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Crime Detection."* KDD Workshop on Anomaly Detection in Finance, 2019. [arXiv:1908.02591](https://arxiv.org/abs/1908.02591).
* **Repository:** [https://www.kaggle.com/datasets/ellipticco/elliptic-data-set](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set)
* **License:** CC BY-NC-SA 4.0. Requires Kaggle account for direct API/browser download.

### IBM AMLSim (Agent-Based AML Simulator)
* **Author / Organization:** IBM Research.
* **Paper / Documentation:** *"Scalable Agent-Based Simulation of Financial Crime"* (2019).
* **Repository:** [https://github.com/IBM/AMLSim](https://github.com/IBM/AMLSim)
* **License:** Apache License 2.0.

---

## 4. Ineligible / Restricted Datasets (Audited and Documented)

| Dataset | Claimed Origin | Restriction Reason | Access Requirement |
|---|---|---|---|
| **ROXSD (ROXANNE Simulated Dataset)** | Idiap Research Institute / ROXANNE | Not publicly hosted; restricted access to protect simulated operational tradecraft. | Requires signed research agreement with Dr. Petr Motlicek (`petr.motlicek@idiap.ch`). |
| **Montreal Co-Offending Network** | Tremblay & Morselli (SPVM Police Records) | Confidential police administrative files. | Strictly non-distributable under Canadian privacy laws. |
| **Chicago Open Crime Incidents** | City of Chicago Data Portal | Co-offending links and offender identities scrubbed. | Irrelevant for relationship discovery (incident-only). |
