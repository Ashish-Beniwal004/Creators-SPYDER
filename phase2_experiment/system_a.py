"""
Phase 2E System A: RAG-Only Experimental Arm
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_experiment/system_a.py

Implements System A (RAG-only):
1. Constructs search query from target entity pair.
2. Retrieves evidence using the existing search_evidence() API.
3. Formulates a relationship decision directly from retrieved text content
   WITHOUT invoking verify_hypothesis() or any symbolic verification tools.
4. Records decision, rationale, retrieved document IDs, and retrieval scores.

Strict Quarantine:
- Never imports or accesses quarantined vault files or provenance.
- Operates strictly on sanitized public retrieval documents.
"""

import os
import sys
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

# Ensure repository root in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_retrieval.retriever import search_evidence, DEFAULT_TOP_K
from phase2_retrieval.schemas import RetrievalResultItem
from phase2_experiment.schemas import SystemCaseOutput, TargetPairInput, RelationshipDecision
from phase2_experiment.config import QUERY_TEMPLATE

# Regex for common alias/moniker mentions in police reports
ALIAS_PATTERN = re.compile(r"['\"](The\s+[A-Za-z]+)['\"]|\b(The\s+(?:Wire|Spark|Locksmith|Driver))\b", re.IGNORECASE)


def extract_mentioned_entities(text: str) -> List[str]:
    """Extracts canonical OID identifiers from document text."""
    return sorted(list(set(re.findall(r"\bOID#\d+\b", text))))


def extract_mentioned_aliases(text: str) -> List[str]:
    """Extracts street aliases or monikers from document text."""
    matches = ALIAS_PATTERN.findall(text)
    aliases = set()
    for m in matches:
        if isinstance(m, tuple):
            for part in m:
                if part:
                    aliases.add(part.title())
        elif isinstance(m, str) and m:
            aliases.add(m.title())
    return sorted(list(aliases))


def evaluate_rag_relationship(
    entity_a: str,
    entity_b: str,
    retrieved_items: List[RetrievalResultItem]
) -> Tuple[RelationshipDecision, str, List[str]]:
    """
    RAG-only decision heuristic:
    Inspects retrieved textual chunks to decide if Entity A and Entity B are related:
    - Direct co-occurrence in incident report -> Supported.
    - Direct communication in CDR -> Supported (RAG treats communication as evidence of relationship).
    - Incident mentions one entity with an accomplice alias retrieved alongside other entity -> Supported.
    - Independent mentions or empty hits -> Insufficient Evidence.
    """
    if not retrieved_items:
        return (
            "Insufficient Evidence",
            "No evidence documents were retrieved from the corpus for the target pair.",
            []
        )

    # 1. Check for single-document co-occurrence of both entities
    for item in retrieved_items:
        entities = extract_mentioned_entities(item.text_content)
        if entity_a in entities and entity_b in entities:
            if item.doc_type == "incident_report":
                return (
                    "Supported",
                    f"RAG-only direct extraction: Incident report {item.doc_id} documents both {entity_a} "
                    f"and {entity_b} in a joint incident context.",
                    [item.doc_id]
                )
            elif item.doc_type == "call_detail_record":
                return (
                    "Supported",
                    f"RAG-only communication inference: Call detail record {item.doc_id} documents direct "
                    f"telecommunication between {entity_a} and {entity_b}.",
                    [item.doc_id]
                )

    # 2. Check for multi-document communication (e.g. CDR between the pair)
    cdr_docs = [
        item for item in retrieved_items
        if item.doc_type == "call_detail_record" and entity_a in extract_mentioned_entities(item.text_content) and entity_b in extract_mentioned_entities(item.text_content)
    ]
    if cdr_docs:
        cited_ids = [d.doc_id for d in cdr_docs]
        return (
            "Supported",
            f"RAG-only communication inference: Wiretap call detail records ({', '.join(cited_ids)}) "
            f"demonstrate direct telecommunication between {entity_a} and {entity_b}.",
            cited_ids
        )

    # 3. Check for alias-mediated joint mention (naive RAG alias assumption)
    # If a retrieved incident report mentions entity_a and an accomplice alias, and another retrieved
    # document mentions entity_b (or vice versa), naive RAG assumes the alias links to the partner.
    for item in retrieved_items:
        if item.doc_type == "incident_report":
            entities = extract_mentioned_entities(item.text_content)
            aliases = extract_mentioned_aliases(item.text_content)
            if (entity_a in entities or entity_b in entities) and aliases:
                partner = entity_b if entity_a in entities else entity_a
                # Check if the other partner is also present in the retrieved set
                partner_in_retrieved = any(
                    partner in extract_mentioned_entities(other.text_content)
                    for other in retrieved_items
                )
                if partner_in_retrieved:
                    alias_name = aliases[0]
                    return (
                        "Supported",
                        f"RAG-only alias inference: Incident report {item.doc_id} documents co-offending with "
                        f"accomplice '{alias_name}', inferred to be {partner} within the retrieved evidence context.",
                        [item.doc_id]
                    )

    # 4. Default conservative decision: independent activity only
    mentioned_docs = [
        item.doc_id for item in retrieved_items
        if entity_a in extract_mentioned_entities(item.text_content) or entity_b in extract_mentioned_entities(item.text_content)
    ]
    return (
        "Insufficient Evidence",
        f"Retrieved evidence documents establish only independent activity for {entity_a} and {entity_b}. "
        f"No joint incident co-participation or direct communication was found linking the two subjects.",
        mentioned_docs
    )


def run_system_a(
    entity_a: str,
    entity_b: str,
    case_index: int = 0,
    top_k: int = DEFAULT_TOP_K,
    retriever: Optional[Any] = None,
    corpus_path: Optional[str] = None
) -> SystemCaseOutput:
    """
    Executes System A (RAG-only) on a single entity pair.
    """
    # Strict input validation
    pair_input = TargetPairInput(entity_a=entity_a, entity_b=entity_b)
    query = QUERY_TEMPLATE.format(entity_a=pair_input.entity_a, entity_b=pair_input.entity_b)

    # Step 1 & 2: Retrieve evidence via public API
    retrieved_items = search_evidence(query=query, top_k=top_k, retriever=retriever, corpus_path=corpus_path)

    # Collect retrieved IDs and scores
    retrieved_doc_ids = [item.doc_id for item in retrieved_items]
    retrieval_scores = {item.doc_id: item.score for item in retrieved_items}

    # Step 3: Make relationship decision without verify_hypothesis()
    decision, rationale, cited_ids = evaluate_rag_relationship(
        entity_a=pair_input.entity_a,
        entity_b=pair_input.entity_b,
        retrieved_items=retrieved_items
    )

    # Canonical sorted pair tuple
    canonical_pair = tuple(sorted([pair_input.entity_a, pair_input.entity_b]))

    # Step 4: Record structured case output
    return SystemCaseOutput(
        case_index=case_index,
        arm="system_a_rag_only",
        entity_a=pair_input.entity_a,
        entity_b=pair_input.entity_b,
        target_pair=canonical_pair,
        decision=decision,
        is_supported=(decision == "Supported"),
        rationale=rationale,
        retrieval_query=query,
        retrieved_doc_ids=retrieved_doc_ids,
        retrieval_scores=retrieval_scores,
        cited_doc_ids=cited_ids,
        verification_data=None,
        execution_timestamp=datetime.now(timezone.utc).isoformat()
    )
