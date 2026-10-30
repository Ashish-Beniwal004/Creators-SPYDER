"""Offline checks of the actual corpus -> runner -> scorer boundary.

Responses are scripted. Passing these checks is not an LLM quality result.
"""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phase2_experiment.score_run import score_run
from phase3_llm.contracts import ToolCall
from phase3_llm.model import ModelReply, ScriptedModel
from phase3_llm.runner import REPO_ROOT, file_hash, run_experiment
from phase3_llm.services import RepositoryServices, load_target_pairs


def repository_model(pairs):
    def baseline(request):
        return ModelReply(text=json.dumps({"decision": "Insufficient Evidence", "rationale": "SCRIPTED boundary check only",
                                           "cited_doc_ids": [d.doc_id for d in request.case.evidence]}))

    def verify(request):
        return ModelReply(tool_calls=(ToolCall("verify_hypothesis", {"entity_a": request.case.pair.ids[0],
                          "entity_b": request.case.pair.ids[1], "evidence_ids": [d.doc_id for d in request.case.evidence]}, "integration-call"),))

    def final(request):
        return ModelReply(text=json.dumps({"decision": request.verification["status"],
                                           "rationale": "SCRIPTED boundary check: " + request.verification["rationale"],
                                           "cited_doc_ids": request.verification["cited_evidence_ids"]}))

    return ScriptedModel({(p.ids, stage): fn for p in pairs for stage, fn in
                          (("baseline", baseline), ("verify", verify), ("final", final))})


class RepositoryIntegrationTests(unittest.TestCase):
    def test_real_pilot_round_trip_and_canonical_pair_join(self):
        corpus = REPO_ROOT / "phase2_corpus/retrieval_documents.jsonl"
        labels = REPO_ROOT / "phase2_ground_truth_vault/pilot_manifest.json"
        provenance = REPO_ROOT / "phase2_corpus/internal_provenance.jsonl"
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            pairs_path = directory / "pairs.json"
            data = json.loads((REPO_ROOT / "phase2_experiment/pilot_target_pairs.json").read_text())
            # A reversed input pair is legal; the runner emits canonical order.
            data["pairs"][0].reverse()
            pairs_path.write_text(json.dumps(data), encoding="utf-8")
            pairs = load_target_pairs(pairs_path)
            metadata = {"version": "frozen-pilot-offline-integration-only", "corpus_sha256": file_hash(corpus),
                        "pairs_sha256": file_hash(pairs_path), "verifier": "repository_HypothesisVerifier"}
            original_open, original_builtin_open = Path.open, open

            def public_open(path, *args, **kwargs):
                if path.resolve() in {labels.resolve(), provenance.resolve()}:
                    self.fail("Hidden audit data accessed before scoring")
                return original_open(path, *args, **kwargs)

            def public_builtin_open(path, *args, **kwargs):
                if isinstance(path, (str, Path)) and Path(path).resolve() in {labels.resolve(), provenance.resolve()}:
                    self.fail("Hidden audit data accessed before scoring")
                return original_builtin_open(path, *args, **kwargs)

            with patch.object(Path, "open", public_open), patch("builtins.open", public_builtin_open), patch("phase3_llm.gemini._post_json", side_effect=AssertionError("Network forbidden")):
                manifest = run_experiment(pairs=pairs, services=RepositoryServices(corpus), model=repository_model(pairs),
                                          output_dir=directory / "run", mode="mock", max_model_calls=30,
                                          dataset_metadata=metadata)
            self.assertEqual(manifest["completed_executions"], 20)
            self.assertEqual(manifest["attempted_model_calls"], 30)
            source = manifest["parameters"]["source"]
            self.assertEqual(source["repository_dependency_hashes"]["phase2_verification/verifier.py"],
                             file_hash(REPO_ROOT / "phase2_verification/verifier.py"))
            self.assertTrue(source["environment"]["python"])
            report = score_run(run_dir=directory / "run", pairs_path=pairs_path, corpus_path=corpus,
                               labels_path=labels, provenance_path=provenance, output_dir=directory / "scores")
            self.assertEqual(report["paired_completed_count"], 10)
            self.assertFalse(report["complete_experiment_run"])
            b = report["arms"]["system_b_rag_verification"]
            self.assertEqual(b["coverage"]["failed"], 0)
            self.assertEqual(b["calls"]["accepted_tool_calls"], 10)
            self.assertEqual(b["calls"]["tool_call_validity_rate"], 1)
            self.assertEqual(report["manual_review"]["system_b_rag_verification"]["rated_executions"], 0)


if __name__ == "__main__":
    unittest.main()
