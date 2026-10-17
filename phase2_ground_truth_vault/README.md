# Phase 2 Ground-Truth Vault

**Security Classification:** QUARANTINED EVALUATION GROUND TRUTH
**Project:** Evidence-Grounded Agentic Criminal Network Investigation
**Status:** Frozen & Validated
**Date:** October 2026

---

## 1. Vault Purpose & Security Perimeter

This vault contains the immutable, ground-truth evaluation answers, split manifests, and evidence schemas for the 10-case pilot and broader benchmark.

### CRITICAL QUARANTINE RULES:
1. **NEVER INDEX INTO RETRIEVAL SEARCH SPACE:**
   Files in this directory (specifically `ground_truth.json` and `pilot_manifest.json`) contain factual co-offending labels ($y \in \{0, 1\}$), causal crime incident IDs, and investigative rationales. Under no circumstances may any file from this directory be ingested into BM25, dense vector stores, or prompt retrieval indices.
2. **STRICTLY EXCLUDED FROM EVALUATED AGENTS:**
   Neither the baseline RAG system nor the agentic verification system may read, search, or query this directory during evaluation inference.
3. **VERSION CONTROL & ARCHIVAL:**
   - Manifests and schemas (`split_manifest.json`, `pilot_manifest.json`, `ground_truth.json`, `schemas.py`) are version-controlled to ensure complete academic reproducibility.
   - Evaluation test logs and scratch files are ignored via `.gitignore`.
