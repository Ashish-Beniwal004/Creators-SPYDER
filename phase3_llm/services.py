"""Explicit public-data adapters. Legacy dependencies are loaded only when requested."""

import json
from pathlib import Path

from .contracts import CaseInput, Evidence, TargetPair, ToolCall


def load_target_pairs(path: Path) -> list[TargetPair]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "pairs" not in data:
        raise ValueError("Use an unlabelled target-pairs file containing 'pairs', not a case manifest")
    if set(data) - {"pairs", "description", "total_pairs"}:
        raise ValueError("Unexpected fields in unlabelled target-pairs file")
    if not isinstance(data["pairs"], list) or not data["pairs"]:
        raise ValueError("Target-pairs list must be nonempty")
    pairs = []
    for item in data["pairs"]:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("Each target pair must contain exactly two identifiers")
        pairs.append(TargetPair(*item))
    if len({p.ids for p in pairs}) != len(pairs):
        raise ValueError("Duplicate target pairs are not permitted")
    if "total_pairs" in data and (type(data["total_pairs"]) is not int or data["total_pairs"] != len(pairs)):
        raise ValueError("total_pairs does not match the pair list")
    return pairs


class RepositoryServices:
    def __init__(self, corpus_path: Path):
        try:
            from phase2_retrieval.retriever import EvidenceRetriever
            from phase2_verification.verifier import HypothesisVerifier
        except ImportError as exc:
            raise RuntimeError("Repository integration requires the existing requirements.txt environment") from exc
        self.retriever = EvidenceRetriever(corpus_path=str(corpus_path))
        self.verifier = HypothesisVerifier(corpus_path=str(corpus_path))

    def retrieve(self, pair: TargetPair, top_k: int) -> CaseInput:
        query = " ".join(pair.ids)
        hits = self.retriever.search(query=query, top_k=top_k)
        return CaseInput(pair, query, tuple(Evidence.from_dict(hit.model_dump()) for hit in hits))

    def verify(self, call: ToolCall) -> dict:
        response = self.verifier.verify(**call.arguments).model_dump()
        if TargetPair(response["entity_a"], response["entity_b"]).ids != TargetPair(
            call.arguments["entity_a"], call.arguments["entity_b"]
        ).ids:
            raise ValueError("Verifier returned a different target pair")
        # Only the documented public result is passed back to the model.
        return {k: response[k] for k in ("status", "evidence_class", "cited_evidence_ids", "rationale", "findings")}
