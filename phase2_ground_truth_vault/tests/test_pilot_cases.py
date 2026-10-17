"""
Unit tests for 10-Case Pilot Case Definition, Label Validity, and Condition Balance
"""

import os
import json
import pytest

VAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(os.path.dirname(VAULT_DIR), "phase1_dataset_audit", "data", "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")

PLANNED_CONDITIONS = {
    "clean_evidence",
    "alias_ambiguity",
    "missing_evidence",
    "distractors",
    "mixed_difficulty"
}


@pytest.fixture(scope="module")
def pilot_data():
    manifest_path = os.path.join(VAULT_DIR, "pilot_manifest.json")
    assert os.path.exists(manifest_path), f"Missing {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ground_truth_data():
    gt_path = os.path.join(VAULT_DIR, "ground_truth.json")
    assert os.path.exists(gt_path), f"Missing {gt_path}"
    with open(gt_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def source_graph():
    if not os.path.exists(DATA_PATH):
        pytest.skip(
            f"Raw Israel National Police source dataset missing: {DATA_PATH}. "
            "Data redistribution permission unverified; download from upstream URL in sources.md."
        )
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build node -> cids map
    node_cids = {}
    for n in data["nodes"]:
        cids = set(n.get("list_cid", []))
        cids.update(n.get("crime_details", {}).keys())
        node_cids[n["id"]] = cids

    # Build undirected links set
    edges = set()
    for l in data["links"]:
        edges.add(tuple(sorted([l["source"], l["target"]])))

    return {"node_cids": node_cids, "edges": edges}


def test_pilot_case_count_and_balance(pilot_data):
    """Test exactly 10 cases, balanced 5 positive and 5 negative."""
    cases = pilot_data["cases"]
    assert len(cases) == 10, f"Expected 10 cases, got {len(cases)}"

    pos = [c for c in cases if c["label"] == 1]
    neg = [c for c in cases if c["label"] == 0]

    assert len(pos) == 5, f"Expected 5 positive cases, got {len(pos)}"
    assert len(neg) == 5, f"Expected 5 negative cases, got {len(neg)}"
    assert pilot_data["total_cases"] == 10
    assert pilot_data["positive_cases_count"] == 5
    assert pilot_data["negative_cases_count"] == 5


def test_condition_assignments(pilot_data):
    """Test that all 5 conditions are covered with exactly 1 positive and 1 negative case each."""
    cases = pilot_data["cases"]
    condition_counts = {}
    for cond in PLANNED_CONDITIONS:
        condition_counts[cond] = {"pos": 0, "neg": 0}

    for c in cases:
        cond = c["condition"]
        assert cond in PLANNED_CONDITIONS, f"Unknown condition: {cond}"
        if c["label"] == 1:
            condition_counts[cond]["pos"] += 1
        else:
            condition_counts[cond]["neg"] += 1

    for cond, counts in condition_counts.items():
        assert counts["pos"] == 1, f"Condition '{cond}' has {counts['pos']} positive cases (expected 1)"
        assert counts["neg"] == 1, f"Condition '{cond}' has {counts['neg']} negative cases (expected 1)"


def test_ground_truth_labels_match_source_data(pilot_data, source_graph):
    """Verify that every positive pair is a true co-offender and negative pair has zero shared CIDs."""
    node_cids = source_graph["node_cids"]
    edges = source_graph["edges"]

    for c in pilot_data["cases"]:
        u, v = c["target_pair"]
        pair_key = tuple(sorted([u, v]))
        label = c["label"]

        assert u in node_cids, f"Entity {u} not found in source dataset"
        assert v in node_cids, f"Entity {v} not found in source dataset"

        shared_cids = node_cids[u] & node_cids[v]

        if label == 1:
            assert pair_key in edges, f"Positive pair {pair_key} is not in source graph edges!"
            assert len(shared_cids) > 0, f"Positive pair {pair_key} has no shared CIDs!"
            # check declared shared crime IDs match source
            for declared_cid in c["shared_crime_ids"]:
                assert declared_cid in shared_cids, f"Declared CID {declared_cid} not shared by {pair_key}"
        else:
            assert pair_key not in edges, f"Negative pair {pair_key} is unexpectedly an edge in source graph!"
            assert len(shared_cids) == 0, f"Negative pair {pair_key} shares CIDs: {shared_cids}!"
            assert len(c["shared_crime_ids"]) == 0, f"Negative pair declared shared CIDs: {c['shared_crime_ids']}"


def test_ground_truth_vault_synchronization(pilot_data, ground_truth_data):
    """Verify ground_truth.json matches pilot_manifest.json."""
    p_cases = {c["case_id"]: c for c in pilot_data["cases"]}
    gt_cases = {c["case_id"]: c for c in ground_truth_data["cases"]}

    assert set(p_cases.keys()) == set(gt_cases.keys())
    for cid, p_case in p_cases.items():
        gt_case = gt_cases[cid]
        assert p_case["target_pair"] == gt_case["target_pair"]
        assert p_case["label"] == gt_case["label"]
        assert p_case["condition"] == gt_case["condition"]
        assert p_case["shared_crime_ids"] == gt_case["shared_crime_ids"]
