"""Two disjoint quota windows must remain one declared, fully accounted cohort."""

import json

import pytest

from phase2_experiment.checkpoint import prepare, score_campaign
from phase2_experiment.score_run import file_hash
from phase3_llm.runner import run_experiment
from phase3_llm.services import RepositoryServices, load_target_pairs
from phase3_llm.tests.test_repository_integration import repository_model


def make_campaign(tmp_path):
    directory = tmp_path / "campaign"
    campaign = prepare(directory)
    from phase2_experiment.checkpoint import ROOT
    corpus = ROOT / "phase2_corpus/retrieval_documents.jsonl"
    services = RepositoryServices(corpus)
    runs = {}
    for group in campaign["groups"]:
        pairs_path = directory / campaign["groups"][group]["pairs_file"]
        pairs = load_target_pairs(pairs_path)
        runs[group] = directory / (group + "_offline_run")
        run_experiment(pairs=pairs, services=services, model=repository_model(pairs), output_dir=runs[group],
                       mode="mock", max_model_calls=3 * len(pairs),
                       dataset_metadata={"version": "frozen-pilot-offline-test-only", "corpus_sha256": file_hash(corpus),
                                         "pairs_sha256": file_hash(pairs_path)})
    return directory, runs


def test_two_blocks_score_without_duplicate_cases_or_fake_scientific_results(tmp_path):
    directory, runs = make_campaign(tmp_path)
    out = tmp_path / "scores"
    report = score_campaign(directory=directory, runs=runs, output_dir=out)
    assert report["paired_completed_count"] == 10
    assert not report["complete_experiment_run"]
    assert report["arms"]["system_b_rag_verification"]["coverage"]["completed"] == 10
    assert report["arms"]["system_b_rag_verification"]["binary_metrics_completed_only"]["true_positives"] == 4
    assert report["manual_review"]["system_a_rag_only"]["rated_executions"] == 0
    assert len((out / "review_template.csv").read_text().splitlines()) >= 21
    with pytest.raises(ValueError, match="new campaign scoring directory"):
        score_campaign(directory=directory, runs=runs, output_dir=out)


def test_different_models_between_windows_are_rejected(tmp_path):
    directory, runs = make_campaign(tmp_path)
    path = runs["group_2"] / "config.json"
    config = json.loads(path.read_text())
    config["model"]["model"] = "changed-after-seeing-results"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="Settings/code/environment differ"):
        score_campaign(directory=directory, runs=runs, output_dir=tmp_path / "scores")
    assert not (tmp_path / "scores").exists()
