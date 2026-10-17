"""
Unit tests for Component-Level Split Isolation and Leakage Prevention
"""

import os
import json
import pytest

VAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def split_manifest():
    manifest_path = os.path.join(VAULT_DIR, "split_manifest.json")
    assert os.path.exists(manifest_path), f"Missing {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pilot_manifest():
    p_path = os.path.join(VAULT_DIR, "pilot_manifest.json")
    assert os.path.exists(p_path), f"Missing {p_path}"
    with open(p_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_split_disjointness(split_manifest):
    """Verify strictly zero entity, edge, or crime case overlap between partitions."""
    partitions = split_manifest["partitions"]

    pilot_nodes = set(partitions["pilot"]["nodes"])
    dev_nodes = set(partitions["dev"]["nodes"])
    test_nodes = set(partitions["test"]["nodes"])
    reserve_nodes = set(partitions["reserve"]["nodes"])

    # Node disjointness
    assert len(pilot_nodes & dev_nodes) == 0, "Leakage: Pilot and Dev share nodes!"
    assert len(pilot_nodes & test_nodes) == 0, "Leakage: Pilot and Test share nodes!"
    assert len(dev_nodes & test_nodes) == 0, "Leakage: Dev and Test share nodes!"
    assert len(pilot_nodes & reserve_nodes) == 0, "Leakage: Pilot and Reserve share nodes!"

    # Edge disjointness
    pilot_edges = {tuple(sorted(e)) for e in partitions["pilot"]["edges"]}
    dev_edges = {tuple(sorted(e)) for e in partitions["dev"]["edges"]}
    test_edges = {tuple(sorted(e)) for e in partitions["test"]["edges"]}

    assert len(pilot_edges & dev_edges) == 0, "Leakage: Pilot and Dev share edges!"
    assert len(pilot_edges & test_edges) == 0, "Leakage: Pilot and Test share edges!"
    assert len(dev_edges & test_edges) == 0, "Leakage: Dev and Test share edges!"

    # CID disjointness
    pilot_cids = set(partitions["pilot"]["distinct_cids"])
    dev_cids = set(partitions["dev"]["distinct_cids"])
    test_cids = set(partitions["test"]["distinct_cids"])

    assert len(pilot_cids & dev_cids) == 0, "Leakage: Pilot and Dev share crime cases (CIDs)!"
    assert len(pilot_cids & test_cids) == 0, "Leakage: Pilot and Test share crime cases (CIDs)!"
    assert len(dev_cids & test_cids) == 0, "Leakage: Dev and Test share crime cases (CIDs)!"


def test_pilot_cases_contained_in_pilot_partition(split_manifest, pilot_manifest):
    """Verify that every pilot target entity and crime case is strictly within the pilot partition."""
    pilot_nodes = set(split_manifest["partitions"]["pilot"]["nodes"])
    dev_nodes = set(split_manifest["partitions"]["dev"]["nodes"])
    test_nodes = set(split_manifest["partitions"]["test"]["nodes"])

    for c in pilot_manifest["cases"]:
        u, v = c["target_pair"]
        assert u in pilot_nodes, f"Entity {u} is not in pilot partition!"
        assert v in pilot_nodes, f"Entity {v} is not in pilot partition!"
        assert u not in dev_nodes, f"Entity {u} leaks into dev partition!"
        assert v not in dev_nodes, f"Entity {v} leaks into dev partition!"
        assert u not in test_nodes, f"Entity {u} leaks into test partition!"
        assert v not in test_nodes, f"Entity {v} leaks into test partition!"
