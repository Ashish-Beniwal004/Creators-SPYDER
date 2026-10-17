"""
Phase 2C Deterministic Evidence Retrieval Layer
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_retrieval/retriever.py

Provides:
- load_and_validate_corpus(): Validates retrieval documents against hardened schema.
- evidence_tokenizer(): Consistent tokenization for canonical entity IDs, aliases, and words.
- EvidenceRetriever: Read-only indexer and search engine using TF-IDF + cosine similarity.
- search_evidence(): Public top-level retrieval interface.
"""

import os
import sys
import json
import re
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure path access to repository root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_ground_truth_vault.schemas import SanitizedRetrievalDocument, validate_retrieval_corpus
from phase2_retrieval.schemas import RetrievalResultItem, RetrievalResponse

# Constants
DEFAULT_CORPUS_PATH = os.path.join(REPO_ROOT, "phase2_corpus", "retrieval_documents.jsonl")
DEFAULT_TOP_K = 5
MAX_TOP_K = 50
APPROVED_EVIDENCE_TYPES = ("incident_report", "call_detail_record")


def evidence_tokenizer(text: str) -> List[str]:
    """
    Deterministic tokenizer tailored for investigative evidence retrieval:
    - Lowercases text for case-insensitive matching.
    - Preserves canonical entity identifiers as atomic units (e.g. 'oid#4418').
    - Emits numeric identifier sub-tokens (e.g. '4418' from 'oid#4418').
    - Emits sub-tokens for hyphenated compound sectors (e.g. 'central', 'east' from 'sector-central-east').
    - Extracts alphanumeric words and monikers (e.g. 'the', 'wire', 'spark', 'locksmith').
    """
    if not text:
        return []
    raw_tokens = re.findall(r"[\w#\-]+", text.lower())
    tokens: List[str] = []
    for t in raw_tokens:
        clean = t.strip("-#")
        if not clean:
            continue
        tokens.append(t)
        # Entity identifier sub-token
        if t.startswith("oid#") and len(t) > 4:
            tokens.append(t[4:])
        # Compound hyphenated term sub-tokens
        if "-" in t:
            for part in t.split("-"):
                if len(part) > 1:
                    tokens.append(part)
    return tokens


def load_and_validate_corpus(corpus_path: str) -> List[SanitizedRetrievalDocument]:
    """
    Loads and rigorously validates an evidence retrieval corpus file.

    Guarantees:
    - Reads ONLY the specified retrieval JSONL file.
    - Rejects malformed JSON and non-object records.
    - Validates every record against SanitizedRetrievalDocument (enforces opaque IDs,
      no unexpected extra fields, no leaked evaluation tokens or original CIDs).
    - Enforces approved evidence types ('incident_report' and 'call_detail_record').
    - Enforces corpus-level uniqueness of document IDs and non-empty collection.
    - Never silently repairs invalid data.
    """
    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Retrieval corpus file not found: {corpus_path}")

    documents: List[SanitizedRetrievalDocument] = []
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                raw_data = json.loads(line_str)
            except Exception as e:
                raise ValueError(f"Corpus validation error on line {line_num}: Malformed JSON - {e}")

            if not isinstance(raw_data, dict):
                raise ValueError(
                    f"Corpus validation error on line {line_num}: Expected JSON object, got {type(raw_data).__name__}"
                )

            # Strict schema validation (rejects extra fields, invalid IDs, leaks)
            try:
                doc = SanitizedRetrievalDocument(**raw_data)
            except Exception as e:
                raise ValueError(f"Corpus validation error on line {line_num}: Schema violation - {e}")

            # Approved evidence type enforcement
            if doc.doc_type not in APPROVED_EVIDENCE_TYPES:
                raise ValueError(
                    f"Corpus validation error on line {line_num}: Disallowed evidence type '{doc.doc_type}'. "
                    f"Approved types: {APPROVED_EVIDENCE_TYPES}"
                )

            documents.append(doc)

    # Corpus-level validation (duplicate document ID rejection, non-empty check)
    validate_retrieval_corpus(documents)
    return documents


class EvidenceRetriever:
    """
    Read-only evidence retrieval service for the SPYDER benchmark.
    Builds a lexical TF-IDF vector index over approved searchable text of validated documents.
    Provides deterministic ranking by cosine similarity with strict tie-breaking.
    """

    def __init__(self, corpus_path: Optional[str] = None):
        self._corpus_path = corpus_path or DEFAULT_CORPUS_PATH
        self._documents: List[SanitizedRetrievalDocument] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._is_indexed = False

        self._build_index()

    def _build_index(self) -> None:
        """Validates the corpus and fits the TF-IDF vectorizer."""
        self._documents = load_and_validate_corpus(self._corpus_path)
        if not self._documents:
            raise ValueError("Cannot initialize EvidenceRetriever on an empty corpus.")

        # Approved searchable field allowlist: text_content ONLY
        corpus_texts = [doc.text_content for doc in self._documents]

        self._vectorizer = TfidfVectorizer(
            tokenizer=evidence_tokenizer,
            token_pattern=None,
            lowercase=True
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus_texts)
        self._is_indexed = True

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def is_indexed(self) -> bool:
        return self._is_indexed

    @property
    def vocabulary(self) -> Dict[str, int]:
        if self._vectorizer is None:
            return {}
        return self._vectorizer.vocabulary_

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[RetrievalResultItem]:
        """
        Executes a lexical retrieval search over the indexed evidence documents.

        Args:
            query: Search query string containing entity IDs, aliases, keywords, or incident descriptions.
            top_k: Number of highest-ranking documents to return (1 <= top_k <= MAX_TOP_K).

        Returns:
            Deterministic list of RetrievalResultItem objects with cosine similarity > 0.
        """
        # Parameter validation
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise TypeError(f"top_k must be an integer, got {type(top_k).__name__}")
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        if top_k > MAX_TOP_K:
            raise ValueError(f"top_k exceeds maximum allowed value ({MAX_TOP_K}), got {top_k}")

        # Safe handling of empty or whitespace queries
        if not query or not isinstance(query, str) or not query.strip():
            return []

        clean_query = query.strip()

        # Vectorize query
        q_vec = self._vectorizer.transform([clean_query])
        if q_vec.nnz == 0:
            # Query terms not in index vocabulary
            return []

        # Compute cosine similarity against all documents
        sims = cosine_similarity(q_vec, self._tfidf_matrix)[0]

        # Filter strictly positive similarity candidates (zero similarity omitted)
        candidates: List[Tuple[float, str, SanitizedRetrievalDocument]] = []
        for idx, score in enumerate(sims):
            if score > 0.0:
                doc = self._documents[idx]
                candidates.append((float(score), doc.doc_id, doc))

        if not candidates:
            return []

        # Deterministic ranking:
        # 1. Primary: Score descending (-score)
        # 2. Secondary tie-breaker: doc_id ascending (alphabetical order)
        candidates.sort(key=lambda item: (-item[0], item[1]))

        # Select top_k
        selected = candidates[:top_k]

        # Convert to strict public presentation schema (zero internal metadata)
        return [
            RetrievalResultItem(
                doc_id=doc.doc_id,
                doc_type=doc.doc_type,
                text_content=doc.text_content,
                score=round(score, 6)
            )
            for score, doc_id, doc in selected
        ]

    def search_response(self, query: str, top_k: int = DEFAULT_TOP_K) -> RetrievalResponse:
        """Structured response envelope wrapper around search."""
        hits = self.search(query=query, top_k=top_k)
        return RetrievalResponse(
            query=query.strip() if isinstance(query, str) else "",
            top_k=top_k,
            total_hits=len(hits),
            results=hits
        )


# Global default singleton retriever
_DEFAULT_RETRIEVER: Optional[EvidenceRetriever] = None


def get_default_retriever() -> EvidenceRetriever:
    """Returns the default EvidenceRetriever singleton, initializing it once if needed."""
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = EvidenceRetriever()
    return _DEFAULT_RETRIEVER


def search_evidence(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    retriever: Optional[EvidenceRetriever] = None,
    corpus_path: Optional[str] = None
) -> List[RetrievalResultItem]:
    """
    Public evidence retrieval function for SPYDER investigative agents.

    Args:
        query: Search query containing entities ('OID#4418'), aliases ('The Wire'),
               incident descriptions ('residential alarm'), or communication types ('VOICE_CALL').
        top_k: Maximum number of relevant evidence documents to return (1 <= top_k <= 50). Defaults to 5.
        retriever: Optional pre-initialized EvidenceRetriever instance.
        corpus_path: Optional path to a specific retrieval corpus file.

    Returns:
        List of RetrievalResultItem objects ordered deterministically by relevance score.
    """
    if retriever is not None:
        return retriever.search(query=query, top_k=top_k)
    if corpus_path is not None:
        return EvidenceRetriever(corpus_path=corpus_path).search(query=query, top_k=top_k)
    return get_default_retriever().search(query=query, top_k=top_k)
