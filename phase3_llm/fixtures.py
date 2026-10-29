"""Four fictional smoke cases and scripted responses, not experimental predictions."""

from copy import deepcopy
import json

from .contracts import CaseInput, Evidence, TargetPair, ToolCall
from .model import ModelReply, ScriptedModel


def _report(doc_id: str, suspects: str, narrative: str) -> Evidence:
    return Evidence(doc_id, "incident_report", (
        f"INCIDENT REPORT [{doc_id}] - CASE INC-2020-9001\n"
        "Date: 2020-03-15 02:00:00 | Sector: Sector-North\n"
        "Entry Method: Forced rear door\nStolen Items: Laptop\n"
        f"Suspects/Persons of Interest: {suspects}\n\nNARRATIVE SUMMARY:\n{narrative}"
    ), 0.9)


def demo_cases() -> list[CaseInput]:
    """Fixture IDs are fictional and independent of the repository benchmark."""
    pairs = [TargetPair(f"OID#{900001 + i * 2}", f"OID#{900002 + i * 2}") for i in range(4)]
    documents = [
        (_report("DOC_IR_90000001", "OID#900001, OID#900002",
                 "Both suspects jointly committed the burglary and were apprehended with stolen property. Case cleared by arrest."),),
        (_report("DOC_IR_90000002", "OID#900003, The Lantern",
                 "OID#900003 and accomplice 'The Lantern' jointly committed the burglary. Both were detained; case cleared by arrest."),
         _report("DOC_IR_90000003", "OID#900004",
                 "Field interview: OID#900004 uses the active street moniker 'The Lantern'.")),
        (_report("DOC_IR_90000004", "OID#900005",
                 "OID#900005 was arrested for a burglary at this address."),
         _report("DOC_IR_90000005", "OID#900006",
                 "OID#900006 was interviewed about activity at a different address.")),
        (Evidence("CDR_90000006", "call_detail_record",
                  "COMMUNICATION INTERCEPT LOG [CDR_90000006]\n"
                  "Timestamp: 2020-03-15 01:00:00 | Type: VOICE_CALL\n"
                  "Caller: OID#900007 -> Callee: OID#900008\nDuration: 120s | Originating Sector: Sector-North", 0.9),),
    ]
    return [CaseInput(pair, " ".join(pair.ids), docs) for pair, docs in zip(pairs, documents)]


class FixtureServices:
    """Scripted verifier for API/control-flow smoke tests only, not an evidence engine."""

    def __init__(self):
        self.cases = {case.pair.ids: case for case in demo_cases()}
        self._supported_pairs = set(list(self.cases)[:2])
        self.retrieval_calls = 0
        self.verification_calls = 0

    def retrieve(self, pair: TargetPair, top_k: int) -> CaseInput:
        self.retrieval_calls += 1
        case = self.cases[pair.ids]
        return CaseInput(pair, case.query, case.evidence[:top_k])

    def verify(self, call: ToolCall) -> dict:
        self.verification_calls += 1
        pair = TargetPair(call.arguments["entity_a"], call.arguments["entity_b"]).ids
        case = self.cases[pair]
        complete = set(call.arguments["evidence_ids"]) == case.doc_ids
        supported = pair in self._supported_pairs and complete
        return {
            "status": "Supported" if supported else "Insufficient Evidence",
            "evidence_class": "direct" if supported else "insufficient",
            "cited_evidence_ids": list(call.arguments["evidence_ids"]),
            "rationale": "SCRIPTED FIXTURE: qualifying joint incident." if supported else "SCRIPTED FIXTURE: no complete qualifying support chain.",
            "findings": [],
        }


def demo_model() -> ScriptedModel:
    scripts = {}
    for index, case in enumerate(demo_cases()):
        def baseline(request, supported=index < 2):
            decision = {"decision": "Supported" if supported else "Insufficient Evidence",
                        "rationale": "SCRIPTED MOCK RESPONSE: this is a software smoke test, not LLM inference.",
                        "cited_doc_ids": [d.doc_id for d in request.case.evidence]}
            return ModelReply(text=json.dumps(decision), raw=deepcopy(decision))

        def verify(request):
            call = ToolCall("verify_hypothesis", {
                "entity_a": request.case.pair.ids[0], "entity_b": request.case.pair.ids[1],
                "evidence_ids": [d.doc_id for d in request.case.evidence],
            }, "mock_verification_call")
            return ModelReply(tool_calls=(call,), raw={"name": call.name, "arguments": call.arguments})

        def final(request):
            decision = {"decision": request.verification["status"],
                        "rationale": "SCRIPTED MOCK RESPONSE: " + request.verification["rationale"],
                        "cited_doc_ids": request.verification["cited_evidence_ids"]}
            return ModelReply(text=json.dumps(decision), raw=deepcopy(decision))

        for stage, response in (("baseline", baseline), ("verify", verify), ("final", final)):
            scripts[(case.pair.ids, stage)] = response
    return ScriptedModel(scripts)
