"""The bounded comparison: one baseline response versus one verifier round-trip."""

from dataclasses import asdict
from datetime import datetime, timezone
import time

from .contracts import ARMS, CaseInput, Decision, validate_verification
from .model import EventSink, Model, ModelRequest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CallBudgetExceeded(RuntimeError):
    pass


class CallBudget:
    """Counts attempted model requests, including failures, across both arms."""

    def __init__(self, limit: int):
        if type(limit) is not int or limit <= 0:
            raise ValueError("Model-call limit must be a positive integer")
        self.limit = limit
        self.used = 0

    def take(self):
        if self.used >= self.limit:
            raise CallBudgetExceeded("Model-call budget exhausted; no further model request was sent")
        self.used += 1


def _call(model: Model, request: ModelRequest, emit: EventSink, budget: CallBudget):
    budget.take()
    emit("model_request", {"stage": request.stage, "attempt": 1, "request": request.public_payload()})
    started = time.monotonic()
    reply = model.respond(request, emit)
    emit("model_response", {"stage": request.stage, "duration_seconds": round(time.monotonic() - started, 6),
                            "text": reply.text, "tool_calls": [asdict(c) for c in reply.tool_calls]})
    return reply


def execute_arm(arm: str, case: CaseInput, case_index: int, model: Model, verify,
                emit: EventSink, budget: CallBudget) -> tuple[dict, dict]:
    if arm not in ARMS:
        raise ValueError("Unknown experiment arm")
    verification = None
    diagnostics = {"decision_origin": "model", "verifier_disagreement": None, "support_gate": "observe_only"}
    if not case.evidence:
        # Same documented controller behavior for both arms; never presented as an LLM response.
        decision = Decision("Insufficient Evidence", "No evidence was retrieved; controller empty-retrieval response.", [])
        diagnostics["decision_origin"] = "controller_empty_retrieval"
        emit("empty_retrieval", diagnostics)
    elif arm == ARMS[0]:
        reply = _call(model, ModelRequest(case, "baseline"), emit, budget)
        if reply.tool_calls:
            raise ValueError("The baseline attempted a tool call")
        decision = Decision.parse(reply.text, case)
    else:
        first = _call(model, ModelRequest(case, "verify"), emit, budget)
        if len(first.tool_calls) != 1:
            raise ValueError("The verification arm must request exactly one verifier call")
        call = first.tool_calls[0]
        try:
            call.validate(case)
        except (ValueError, TypeError) as exc:
            emit("tool_rejected", {"call": asdict(call), "reason": str(exc)})
            raise
        emit("tool_accepted", {"call": asdict(call)})
        verification = validate_verification(verify(call), call)
        emit("tool_result", {"call_id": call.call_id, "result": verification})
        final = _call(model, ModelRequest(case, "final", first, verification), emit, budget)
        if final.tool_calls:
            raise ValueError("A second tool call is outside the checkpoint budget")
        decision = Decision.parse(final.text, case)
        diagnostics["verifier_disagreement"] = decision.decision != verification["status"]
        emit("verification_comparison", diagnostics)

    # Compatible with the existing SystemCaseOutput shape. Rich metadata stays outside it.
    output = {
        "case_index": case_index, "arm": arm,
        "entity_a": case.pair.ids[0], "entity_b": case.pair.ids[1], "target_pair": list(case.pair.ids),
        "decision": decision.decision, "is_supported": decision.decision == "Supported",
        "rationale": decision.rationale, "retrieval_query": case.query,
        "retrieved_doc_ids": [d.doc_id for d in case.evidence],
        "retrieval_scores": {d.doc_id: d.score for d in case.evidence},
        "cited_doc_ids": decision.cited_doc_ids,
        "verification_data": verification, "execution_timestamp": utc_now(),
    }
    return output, diagnostics
