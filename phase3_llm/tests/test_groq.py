"""Groq wire-format, quota and real-service boundaries; no API credentials/network."""

from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from phase3_llm.contracts import ARMS, Decision
from phase3_llm.fixtures import FixtureServices, demo_cases
from phase3_llm.groq import GroqModel, _post_json
from phase3_llm.model import ModelRequest, ProviderError
from phase3_llm.runner import main, run_experiment, file_hash
from phase3_llm.services import RepositoryServices, load_target_pairs
from phase3_llm.quota import TokenLedger


class Clock:
    def __init__(self):
        self.value = time.time()
        self.waits = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.value += seconds


def completion(message, finish="stop", tokens=1000):
    return {"model": "openai/gpt-oss-120b", "system_fingerprint": "offline-test",
            "choices": [{"index": 0, "finish_reason": finish, "message": message}],
            "usage": {"prompt_tokens": tokens - 200, "completion_tokens": 200, "total_tokens": tokens,
                      "completion_tokens_details": {"reasoning_tokens": 100}}}


class GroqTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "ledger.jsonl"
        self.clock = Clock()
        self.responses, self.requests, self.events = [], [], []
        self.case = demo_cases()[0]

    def transport(self, payload, key, timeout):
        self.requests.append(deepcopy(payload))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)

    def model(self, **kwargs):
        return GroqModel("private-offline-key", ledger_path=self.ledger, transport=kwargs.pop("transport", self.transport),
                         clock=self.clock.now, sleep=self.clock.sleep, **kwargs)

    def emit(self, event, data):
        self.events.append((event, deepcopy(data)))

    def tool_message(self):
        return {"role": "assistant", "content": None, "reasoning": "must not be replayed",
                "tool_calls": [{"id": "call-1", "type": "function", "function": {
                    "name": "verify_hypothesis", "arguments": json.dumps({"entity_a": self.case.pair.ids[0],
                    "entity_b": self.case.pair.ids[1], "evidence_ids": sorted(self.case.doc_ids)})}}]}

    def test_tool_then_strict_json_preserves_exact_call_id_and_result(self):
        self.responses = [completion(self.tool_message(), "tool_calls"),
                          completion({"role": "assistant", "content": json.dumps({"decision": "Supported", "rationale": "Verified.",
                                                                                   "cited_doc_ids": sorted(self.case.doc_ids)})})]
        model = self.model()
        first = model.respond(ModelRequest(self.case, "verify"), self.emit)
        first.tool_calls[0].validate(self.case)
        result = FixtureServices().verify(first.tool_calls[0])
        final = model.respond(ModelRequest(self.case, "final", first, result), self.emit)
        self.assertEqual(Decision.parse(final.text, self.case).decision, "Supported")
        initial, followup = self.requests
        self.assertEqual(initial["tool_choice"]["function"]["name"], "verify_hypothesis")
        self.assertFalse(initial["parallel_tool_calls"])
        self.assertNotIn("response_format", initial)
        self.assertNotIn("tools", followup)
        self.assertTrue(followup["response_format"]["json_schema"]["strict"])
        self.assertEqual(followup["messages"][-2]["tool_call_id"], "call-1")
        self.assertEqual(json.loads(followup["messages"][-2]["content"]), result)
        self.assertNotIn("reasoning", followup["messages"][-3])
        self.assertEqual(followup["reasoning_effort"], "medium")
        self.assertFalse(followup["include_reasoning"])
        self.assertNotIn("reasoning_format", followup)
        self.assertGreaterEqual(sum(self.clock.waits), 90)
        self.assertEqual(model.ledger.run_charged, 2000)
        self.assertNotIn("private-offline-key", json.dumps(self.events))

    def test_baseline_has_schema_no_tools_and_no_builtin_search(self):
        payload = self.model().build_payload(ModelRequest(self.case, "baseline"))
        self.assertEqual(payload["model"], "openai/gpt-oss-120b")
        self.assertNotIn("tools", payload)
        self.assertFalse(payload["stream"])
        self.assertNotIn("store", payload)  # unsupported parameter on Groq Chat
        self.assertEqual(payload["max_completion_tokens"], 4096)

    def test_http_error_redacts_key_and_does_not_retry(self):
        error = HTTPError("https://api.groq.com/", 429, "quota", {"retry-after": "60"},
                          io.BytesIO(json.dumps({"error": {"message": "bad private-offline-key"}}).encode()))
        opener = unittest.mock.Mock()
        opener.open.side_effect = error
        with patch("phase3_llm.groq.request.build_opener", return_value=opener):
            with self.assertRaises(ProviderError) as caught:
                _post_json({}, "private-offline-key", 30)
        self.assertNotIn("private-offline-key", str(caught.exception))
        self.assertIn("429", str(caught.exception))
        self.assertIn("Retry-After=60", str(caught.exception))
        self.assertEqual(opener.open.call_count, 1)
        sent_request = opener.open.call_args.args[0]
        self.assertEqual(sent_request.get_header("User-agent"), "SPYDER-Research/0.1")

    def test_timeout_reservation_survives_new_model_instance(self):
        self.responses = [ProviderError("simulated timeout")]
        with self.assertRaises(ProviderError):
            self.model().respond(ModelRequest(self.case, "baseline"), self.emit)
        records = self.model().ledger._records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["tokens"], 8000)
        self.assertFalse(self.ledger.with_name("ledger.jsonl.lock").exists())

    def test_run_budget_denies_extra_http_request(self):
        self.responses = [ProviderError("unknown usage"), ProviderError("unknown usage")]
        model = self.model(max_total_tokens=16000)
        for _ in range(2):
            with self.assertRaises(ProviderError):
                model.respond(ModelRequest(self.case, "baseline"), self.emit)
        with self.assertRaisesRegex(ProviderError, "budget exhausted"):
            model.respond(ModelRequest(self.case, "baseline"), self.emit)
        self.assertEqual(len(self.requests), 2)

    def test_rolling_window_budget_and_malformed_ledger_fail_closed(self):
        self.ledger.write_text(json.dumps({"event": "reserve", "id": "earlier", "timestamp": self.clock.now() - 100}) + "\n"
                               + json.dumps({"event": "usage", "id": "earlier", "tokens": 176000}) + "\n")
        with self.assertRaisesRegex(ProviderError, "budget exhausted"):
            self.model().respond(ModelRequest(self.case, "baseline"), self.emit)
        self.ledger.write_text("invalid json\n")
        with self.assertRaisesRegex(ProviderError, "cannot be validated"):
            self.model().respond(ModelRequest(self.case, "baseline"), self.emit)
        self.assertFalse(self.requests)

    def test_large_request_is_not_silently_truncated(self):
        from dataclasses import replace
        case = replace(self.case, evidence=(replace(self.case.evidence[0], text_content="x" * 30000),))
        with self.assertRaisesRegex(ProviderError, "no request sent or evidence truncated"):
            self.model().respond(ModelRequest(case, "baseline"), self.emit)
        self.assertFalse(self.requests)

    def test_invalid_usage_or_finish_cannot_become_a_decision(self):
        good = completion({"role": "assistant", "content": "{}"})
        for response in [dict(good, usage=None), dict(good, usage={}),
                         completion({"role": "assistant", "content": "{}"}, "length"),
                         completion({"role": "assistant", "content": None, "refusal": "refused"})]:
            self.responses.append(response)
            with self.assertRaises(ProviderError):
                self.model().respond(ModelRequest(self.case, "baseline"), self.emit)

    def test_empty_key_and_invalid_settings_do_not_create_ledger(self):
        for kwargs in [{"api_key": ""}, {"api_key": "x", "model": "other"}, {"api_key": "x", "thinking": "none"},
                       {"api_key": "x", "timeout": float("nan")}, {"api_key": "x", "request_interval": -1}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GroqModel(ledger_path=self.ledger, **kwargs)
        self.assertFalse(self.ledger.exists())

    def test_groq_cli_uses_its_key_and_defaults_without_touching_gemini(self):
        from phase3_llm.fixtures import demo_model
        scripted = demo_model()
        fake = type("FakeLive", (), {"metadata": property(lambda self: {"provider": "offline_test_double"}),
                                      "respond": lambda self, req, emit: scripted.respond(req, emit)})()
        key = self.root / "key"
        key.write_text("groq-file-test-key\n")
        with patch("phase3_llm.groq.GroqModel", return_value=fake) as adapter, \
                patch("phase3_llm.gemini.GeminiModel", side_effect=AssertionError("Gemini must not be used")), \
                patch("sys.stdout", new_callable=io.StringIO):
            result = main(["--provider", "groq", "--mode", "smoke", "--allow-live", "--api-key-file", str(key),
                           "--output-dir", str(self.root / "run"), "--max-model-calls", "3"])
        self.assertEqual(result, 0)
        self.assertEqual(adapter.call_args.args[0], "groq-file-test-key")
        self.assertEqual(adapter.call_args.kwargs["model"], "openai/gpt-oss-120b")
        self.assertEqual(adapter.call_args.kwargs["request_interval"], 90)
        with patch("phase3_llm.groq.GroqModel", side_effect=AssertionError("No construction")), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit):
                main(["--provider", "groq", "--mode", "smoke"])


class GroqRepositoryTests(unittest.TestCase):
    def test_all_ten_pairs_through_adapter_services_and_native_scorer(self):
        from phase2_experiment.score_run import score_run
        from phase3_llm.runner import REPO_ROOT
        corpus = REPO_ROOT / "phase2_corpus/retrieval_documents.jsonl"
        pairs_path = REPO_ROOT / "phase2_experiment/pilot_target_pairs.json"
        pairs = load_target_pairs(pairs_path)
        clock = Clock()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            def transport(body, key, timeout):
                if "tools" in body:
                    case = json.loads(body["messages"][1]["content"].split("\n\n", 1)[1])
                    call = {"id": "call-test", "type": "function", "function": {"name": "verify_hypothesis", "arguments": json.dumps({
                        "entity_a": case["target_pair"][0], "entity_b": case["target_pair"][1],
                        "evidence_ids": [d["doc_id"] for d in case["evidence"]]})}}
                    return completion({"role": "assistant", "content": None, "tool_calls": [call]}, "tool_calls")
                tool_result = next((json.loads(m["content"]) for m in body["messages"] if m["role"] == "tool"), None)
                decision = {"decision": tool_result["status"] if tool_result else "Insufficient Evidence",
                            "rationale": "OFFLINE FAKE TRANSPORT ONLY", "cited_doc_ids": tool_result["cited_evidence_ids"] if tool_result else []}
                return completion({"role": "assistant", "content": json.dumps(decision)})

            model = GroqModel("fake-no-network-key", transport=transport, ledger_path=tmp / "quota.jsonl", clock=clock.now, sleep=clock.sleep)
            manifest = run_experiment(pairs=pairs, services=RepositoryServices(corpus), model=model, mode="smoke",
                                      max_model_calls=30, output_dir=tmp / "run", dataset_metadata={
                                          "version": "frozen-pilot-offline-adapter-check", "corpus_sha256": file_hash(corpus), "pairs_sha256": file_hash(pairs_path)})
            self.assertEqual(manifest["completed_executions"], 20)
            self.assertEqual(manifest["provider_requests_sent"], 30)
            report = score_run(run_dir=tmp / "run", labels_path=REPO_ROOT / "phase2_ground_truth_vault/pilot_manifest.json",
                               pairs_path=pairs_path, corpus_path=corpus, output_dir=tmp / "scores")
            self.assertEqual(report["paired_completed_count"], 10)
            self.assertEqual(report["model"]["provider"], "groq")
            self.assertFalse(report["complete_experiment_run"])
            self.assertEqual(report["arms"][ARMS[1]]["provider_reported_usage"]["total_tokens"], 20000)
            self.assertEqual(model.ledger.run_charged, 30000)


if __name__ == "__main__":
    unittest.main()
