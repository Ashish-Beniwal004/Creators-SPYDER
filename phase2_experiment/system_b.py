"""
Phase 2E System B: RAG + Verification Experimental Arm
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_experiment/system_b.py

Implements System B (RAG + Verification):
1. Uses the identical initial retrieval process and budget as System A.
2. Formulates a hypothesis: "entity_a and entity_b share at least one documented
   solved burglary case within the evaluation window."
3. Invokes verify_hypothesis() using strictly valid retrieved document IDs.
4. Grounds the final decision in the verifier's returned status and cited findings.
5. Records retrieval results, verification data, final decision, rationale, and citations.

Strict Quarantine:
- Never imports or accesses quarantined vault files or provenance.
- Operates strictly on sanitized public retrieval documents and public verification API.
"""

import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

# Ensure repository root in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_retrieval.retriever import search_evidence, DEFAULT_TOP_K
from phase2_verification.verifier import verify_hypothesis
from phase2_experiment.schemas import SystemCaseOutput, TargetPairInput, DOC_ID_REGEX
from phase2_experiment.config import QUERY_TEMPLATE


def run_system_b(
    entity_a: str,
    entity_b: str,
    case_index: int = 0,
    top_k: int = DEFAULT_TOP_K,
    retriever: Optional[Any] = None,
    verifier: Optional[Any] = None,
    corpus_path: Optional[str] = None
) -> SystemCaseOutput:
    """
    Executes System B (RAG + Verification) on a single entity pair.
    """
    # Strict input validation
    pair_input = TargetPairInput(entity_a=entity_a, entity_b=entity_b)
    query = QUERY_TEMPLATE.format(entity_a=pair_input.entity_a, entity_b=pair_input.entity_b)

    # Step 1: Same initial retrieval process as System A
    retrieved_items = search_evidence(query=query, top_k=top_k, retriever=retriever, corpus_path=corpus_path)

    retrieved_doc_ids = [item.doc_id for item in retrieved_items]
    retrieval_scores = {item.doc_id: item.score for item in retrieved_items}

    canonical_pair = tuple(sorted([pair_input.entity_a, pair_input.entity_b]))

    # Step 2 & 3: Handle empty retrieval vs formal hypothesis verification
    if not retrieved_doc_ids:
        # Conservative fallback for empty retrieval
        return SystemCaseOutput(
            case_index=case_index,
            arm="system_b_rag_verification",
            entity_a=pair_input.entity_a,
            entity_b=pair_input.entity_b,
            target_pair=canonical_pair,
            decision="Insufficient Evidence",
            is_supported=False,
            rationale="No evidence documents were retrieved from the corpus for the target pair.",
            retrieval_query=query,
            retrieved_doc_ids=[],
            retrieval_scores={},
            cited_doc_ids=[],
            verification_data={
                "status": "Insufficient Evidence",
                "evidence_class": "insufficient",
                "findings_count": 0,
                "findings": [],
                "verifier_rationale": "Empty retrieval corpus response; no hypothesis verification executed."
            },
            execution_timestamp=datetime.now(timezone.utc).isoformat()
        )

    # Deduplicate and validate retrieved document IDs
    valid_doc_ids: List[str] = []
    seen = set()
    for doc_id in retrieved_doc_ids:
        if not DOC_ID_REGEX.match(doc_id):
            raise ValueError(f"System B encountered invalid retrieved document ID: '{doc_id}'")
        if doc_id not in seen:
            seen.add(doc_id)
            valid_doc_ids.append(doc_id)

    # Step 4: Invoke verify_hypothesis()
    verification_result = verify_hypothesis(
        entity_a=pair_input.entity_a,
        entity_b=pair_input.entity_b,
        evidence_ids=valid_doc_ids,
        verifier=verifier,
        corpus_path=corpus_path
    )

    # Step 5: Produce final decision grounded in verification output
    decision = verification_result.status
    is_supported = (decision == "Supported")
    rationale = verification_result.rationale
    cited_ids = verification_result.cited_evidence_ids

    verification_data = {
        "status": verification_result.status,
        "evidence_class": verification_result.evidence_class,
        "findings_count": len(verification_result.findings),
        "findings": [f.model_dump() for f in verification_result.findings],
        "verifier_rationale": verification_result.rationale
    }

    return SystemCaseOutput(
        case_index=case_index,
        arm="system_b_rag_verification",
        entity_a=pair_input.entity_a,
        entity_b=pair_input.entity_b,
        target_pair=canonical_pair,
        decision=decision,
        is_supported=is_supported,
        rationale=rationale,
        retrieval_query=query,
        retrieved_doc_ids=retrieved_doc_ids,
        retrieval_scores=retrieval_scores,
        cited_doc_ids=cited_ids,
        verification_data=verification_data,
        execution_timestamp=datetime.now(timezone.utc).isoformat()
    )
