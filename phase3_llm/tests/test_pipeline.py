from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phase3_llm.contracts import ARMS, CaseInput, Decision, Evidence, TargetPair, ToolCall
from phase3_llm.fixtures import FixtureServices, demo_cases, demo_model
from phase3_llm.gemini import GeminiModel, ProviderError
from phase3_llm.model import ModelReply, ModelRequest
from phase3_llm.runner import REPO_ROOT, main, run_experiment
from phase3_llm.services import RepositoryServices, load_target_pairs
from phase3_llm.systems import CallBudget, execute_arm


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.case = demo_cases()[0]
        self.services = FixtureServices()
        self.model = demo_model()
        self.events = []
        self.emit = lambda event, value: self.events.append((event, value))

    def execute(self, arm=ARMS[1], model=None, case=None, verify=None):
        return execute_arm(arm, case or self.case, 0, model or self.model,
                           verify or self.services.verify, self.emit, CallBudget(10))

    def test_baseline_never_invokes_verifier(self):
        output, _ = self.execute(ARMS[0], verify=lambda call: self.fail("Baseline called verifier"))
        self.assertEqual(output["decision"], "Supported")
        self.assertIsNone(output["verification_data"])
        self.assertEqual([x[1]["stage"] for x in self.events if x[0] == "model_request"], ["baseline"])

    def test_verification_round_trip_uses_exact_call_and_final_model_response(self):
        final = {"decision": "Insufficient Evidence", "rationale": "Deliberate model/tool disagreement.",
                 "cited_doc_ids": []}
        self.model._replies[(self.case.pair.ids, "final")] = ModelReply(text=json.dumps(final))
        output, diagnostics = self.execute()
        self.assertEqual(output["decision"], "Insufficient Evidence")
        self.assertEqual(output["verification_data"]["status"], "Supported")
        self.assertTrue(diagnostics["verifier_disagreement"])
        self.assertEqual(self.services.verification_calls, 1)
        self.assertEqual([x[1]["stage"] for x in self.events if x[0] == "model_request"], ["verify", "final"])

    def test_all_four_fixture_paths(self):
        for case in demo_cases():
            for arm in ARMS:
                output, _ = self.execute(arm, case=case)
                self.assertTrue(set(output["cited_doc_ids"]) <= case.doc_ids)
                self.assertEqual(output["is_supported"], output["decision"] == "Supported")

    def test_invalid_tool_calls_are_rejected_before_execution(self):
        valid = ToolCall("verify_hypothesis", {"entity_a": self.case.pair.ids[0],
                          "entity_b": self.case.pair.ids[1], "evidence_ids": list(self.case.doc_ids)}, "call")
        invalid = [replace(valid, name="read_file"), replace(valid, call_id=""),
                   replace(valid, arguments={**valid.arguments, "entity_b": "OID#888888"}),
                   replace(valid, arguments={**valid.arguments, "evidence_ids": ["DOC_IR_deadbeef"]}),
                   replace(valid, arguments={**valid.arguments, "evidence_ids": []}),
                   replace(valid, arguments={**valid.arguments, "evidence_ids": list(self.case.doc_ids) * 2}),
                   replace(valid, arguments={**valid.arguments, "path": "secret"})]
        for call in invalid:
            with self.subTest(call=call):
                self.model._replies[(self.case.pair.ids, "verify")] = ModelReply(tool_calls=(call,))
                with self.assertRaises(ValueError):
                    self.execute(verify=lambda item: self.fail("Rejected tool was executed"))
        self.assertEqual(len([e for e in self.events if e[0] == "tool_rejected"]), len(invalid))

    def test_zero_multiple_and_second_tool_calls_fail(self):
        first = self.model.respond(ModelRequest(self.case, "verify"), self.emit)
        for calls in [(), first.tool_calls * 2]:
            self.model._replies[(self.case.pair.ids, "verify")] = ModelReply(tool_calls=calls)
            with self.assertRaises(ValueError):
                self.execute()
        self.model._replies[(self.case.pair.ids, "verify")] = first
        self.model._replies[(self.case.pair.ids, "final")] = first
        with self.assertRaisesRegex(ValueError, "second tool call"):
            self.execute()

    def test_invalid_final_outputs_fail_instead_of_becoming_insufficient(self):
        good = {"decision": "Supported", "rationale": "Evidence.", "cited_doc_ids": list(self.case.doc_ids)}
        invalid = ["not json", {**good, "decision": "Yes"}, {**good, "rationale": ""},
                   {**good, "cited_doc_ids": []}, {**good, "cited_doc_ids": ["DOC_IR_deadbeef"]},
                   {**good, "label": 1}]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Decision.parse(value, self.case)

    def test_verifier_cannot_return_hidden_fields_or_unrequested_ids(self):
        def bad(call):
            return {**self.services.verify(call), "label": 1}
        with self.assertRaisesRegex(ValueError, "exactly"):
            self.execute(verify=bad)
        def bad_ids(call):
            return {**self.services.verify(call), "cited_evidence_ids": ["DOC_IR_deadbeef"]}
        with self.assertRaisesRegex(ValueError, "supplied"):
            self.execute(verify=bad_ids)

    def test_public_payload_is_allowlisted(self):
        self.assertEqual(set(self.case.public_payload()), {"target_pair", "evidence"})
        self.assertEqual(set(self.case.public_payload()["evidence"][0]), {"doc_id", "doc_type", "text_content", "score"})
        with self.assertRaises(ValueError):
            Evidence.from_dict({**self.case.public_payload()["evidence"][0], "label": 1})

    def test_invalid_pair_and_nonfinite_score_are_rejected(self):
        for pair in [("OID#1", "OID#1"), ("OID#1\n", "OID#2"), (1, "OID#2")]:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                TargetPair(*pair)
        for score in [float("nan"), float("inf"), True, -1, 2]:
            with self.subTest(score=score), self.assertRaises(ValueError):
                replace(self.case.evidence[0], score=score)

    def test_empty_retrieval_is_explicit_controller_output(self):
        case = replace(self.case, evidence=())
        for arm in ARMS:
            output, details = self.execute(arm, case=case)
            self.assertEqual(output["decision"], "Insufficient Evidence")
            self.assertEqual(details["decision_origin"], "controller_empty_retrieval")
        self.assertFalse(any(e[0] == "model_request" for e in self.events))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "run"

    def run_mock(self, **kwargs):
        return run_experiment(pairs=[c.pair for c in demo_cases()], services=kwargs.pop("services", FixtureServices()),
                              model=kwargs.pop("model", demo_model()), output_dir=self.path, **kwargs)

    def test_mock_run_shares_retrieval_and_exports_compatible_outputs(self):
        services = FixtureServices()
        manifest = self.run_mock(services=services)
        self.assertEqual(manifest["completed_executions"], 8)
        self.assertEqual(manifest["attempted_model_calls"], 12)
        self.assertEqual(services.retrieval_calls, 4)
        self.assertEqual(services.verification_calls, 4)
        self.assertFalse(manifest["parameters"]["scientific_results"])
        a, b = [json.loads((self.path / f"{arm}_outputs.json").read_text())["results"] for arm in ARMS]
        for ca, cb in zip(a, b):
            self.assertEqual(ca["retrieved_doc_ids"], cb["retrieved_doc_ids"])
            self.assertEqual(ca["retrieval_scores"], cb["retrieval_scores"])
        from phase3_llm.runner import file_hash
        for name, digest in manifest["artifact_hashes"].items():
            self.assertEqual(file_hash(self.path / name), digest)

    def test_failure_is_retained_and_partial_exports_are_not_written(self):
        model = demo_model()
        model._replies[(demo_cases()[0].pair.ids, "baseline")] = RuntimeError("Simulated provider failure")
        manifest = self.run_mock(model=model)
        self.assertEqual(manifest["failed_executions"], 1)
        self.assertEqual(manifest["completed_executions"], 7)
        self.assertFalse(manifest["exports_available"])
        failed = json.loads((self.path / "errors.jsonl").read_text().splitlines()[0])
        self.assertNotIn("decision", failed)
        self.assertFalse((self.path / f"{ARMS[0]}_outputs.json").exists())

    def test_call_budget_stops_before_extra_request(self):
        manifest = self.run_mock(max_model_calls=1)
        self.assertEqual(manifest["attempted_model_calls"], 1)
        self.assertEqual(manifest["completed_executions"], 1)
        self.assertEqual(manifest["failed_executions"], 1)
        self.assertEqual(manifest["unattempted_executions"], 6)

    def test_existing_and_historical_output_paths_are_protected(self):
        self.run_mock()
        original = (self.path / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_mock()
        self.assertEqual((self.path / "manifest.json").read_bytes(), original)
        with self.assertRaisesRegex(ValueError, "protected"):
            run_experiment(pairs=[demo_cases()[0].pair], services=FixtureServices(), model=demo_model(),
                           output_dir=REPO_ROOT / "phase2_experiment/outputs/new")

    def test_mock_cannot_be_claimed_as_live_experiment(self):
        with self.assertRaises(ValueError):
            self.run_mock(mode="experiment")

    def test_bad_target_pair_manifests_are_rejected(self):
        p = Path(self.tmp.name) / "pairs.json"
        for value in [{"cases": [{"label": 1}]}, {"pairs": [["OID#1", "OID#2"]], "label": 1},
                      {"pairs": [["OID#1", "OID#2"], ["OID#2", "OID#1"]]},
                      {"pairs": [["OID#1", "OID#2"]], "total_pairs": 2}]:
            p.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                load_target_pairs(p)
        p.write_text(json.dumps({"pairs": [["OID#2", "OID#1"]], "total_pairs": 1}))
        self.assertEqual(load_target_pairs(p)[0].ids, ("OID#1", "OID#2"))

    def test_cli_requires_explicit_live_permission_before_model_creation(self):
        with patch("phase3_llm.gemini.GeminiModel", side_effect=AssertionError("Must not construct model")), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as exc:
                main(["--provider", "gemini", "--mode", "smoke"])
        self.assertEqual(exc.exception.code, 2)

    def test_retrieval_failure_is_reported_for_both_arms_without_model_calls(self):
        services = FixtureServices()
        services.retrieve = lambda *args: (_ for _ in ()).throw(RuntimeError("Index unavailable"))
        manifest = self.run_mock(services=services)
        self.assertEqual(manifest["failed_executions"], 8)
        self.assertEqual(manifest["attempted_model_calls"], 0)
        self.assertEqual(len((self.path / "results.jsonl").read_text().splitlines()), 8)

    def test_interruption_preserves_a_manifest_and_existing_trace(self):
        model = demo_model()
        model._replies[(demo_cases()[0].pair.ids, "baseline")] = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_mock(model=model)
        manifest = json.loads((self.path / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "interrupted")
        self.assertFalse(manifest["exports_available"])
        self.assertIn("model_request", (self.path / "traces.jsonl").read_text())


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.case = demo_cases()[0]
        self.requests = []
        self.events = []
        self.responses = []
        def transport(payload, key, timeout):
            self.requests.append(deepcopy(payload))
            return self.responses.pop(0)
        self.model = GeminiModel("private-test-key", transport=transport, request_interval=0)
        self.emit = lambda event, data: self.events.append((event, deepcopy(data)))

    def test_stateless_tool_history_preserves_signatures_and_call_id(self):
        call = {"type": "function_call", "id": "call-123", "name": "verify_hypothesis", "arguments": {
            "entity_a": self.case.pair.ids[0], "entity_b": self.case.pair.ids[1], "evidence_ids": list(self.case.doc_ids)}}
        thought = {"type": "thought", "signature": "opaque-signature", "summary": []}
        self.responses.append({"id": "interaction-1", "status": "requires_action", "steps": [thought, call],
                               "usage": {"total_input_tokens": 20}})
        first = self.model.respond(ModelRequest(self.case, "verify"), self.emit)
        result = FixtureServices().verify(first.tool_calls[0])
        self.responses.append({"status": "completed", "steps": [{"type": "model_output", "content": [
            {"type": "text", "text": json.dumps({"decision": "Supported", "rationale": "Verified.",
                                                  "cited_doc_ids": list(self.case.doc_ids)})}]}]})
        final = self.model.respond(ModelRequest(self.case, "final", first, result), self.emit)
        self.assertEqual(Decision.parse(final.text, self.case).decision, "Supported")
        second = self.requests[1]
        self.assertEqual(second["input"][1:3], [thought, call])
        self.assertEqual(second["input"][3]["call_id"], "call-123")
        self.assertEqual(second["tools"], self.requests[0]["tools"])
        self.assertEqual(second["generation_config"]["tool_choice"], "none")
        self.assertFalse(second["store"])
        self.assertEqual(second["generation_config"]["thinking_level"], "medium")
        self.assertNotIn("temperature", second["generation_config"])
        self.assertNotIn("private-test-key", json.dumps(self.events))

    def test_transport_failure_is_not_retried(self):
        transport = unittest.mock.Mock(side_effect=ProviderError("Simulated HTTP 429"))
        model = GeminiModel("private-test-key", transport=transport, request_interval=0)
        with self.assertRaises(ProviderError):
            model.respond(ModelRequest(self.case, "baseline"), self.emit)
        self.assertEqual(transport.call_count, 1)

    def test_baseline_sends_schema_without_tools(self):
        body = self.model.build_payload(ModelRequest(self.case, "baseline"))
        self.assertIn("response_format", body)
        self.assertNotIn("tools", body)
        self.assertEqual(body["model"], "gemini-3.8-flash")

    def test_incomplete_refused_or_malformed_responses_are_not_decisions(self):
        for response in [{"status": "incomplete", "steps": []}, {"status": "failed", "steps": []},
                         {"steps": "not-a-list"}]:
            self.responses.append(response)
            with self.assertRaises(ProviderError):
                self.model.respond(ModelRequest(self.case, "baseline"), self.emit)

    def test_empty_key_and_invalid_limits_fail_without_network(self):
        for kwargs in [{"api_key": ""}, {"api_key": "x", "thinking": "minimal"},
                       {"api_key": "x", "timeout": float("nan")}, {"api_key": "x", "max_output_tokens": 0}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GeminiModel(**kwargs)


if __name__ == "__main__":
    unittest.main()
