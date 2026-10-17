"""
Unit test for Seed Reproducibility
"""

import os
import json
import pytest

VAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_seed_reproducibility():
    """Verify that regenerating with seed 42 produces identical pilot and split manifests."""
    raw_data_path = os.path.join(os.path.dirname(VAULT_DIR), "phase1_dataset_audit", "data", "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")
    if not os.path.exists(raw_data_path):
        pytest.skip(
            "Raw Israel National Police source dataset missing from repository "
            "(excluded from public git tree due to unverified redistribution permission). "
            "Seed regeneration requires authorized upstream data access."
        )

    from freeze_pilot import (
        load_and_partition_graph,
        compute_node_metadata,
        build_split_manifest,
        build_pilot_cases,
        RANDOM_SEED
    )

    assert RANDOM_SEED == 42

    graph_data = load_and_partition_graph()
    node_meta = compute_node_metadata(graph_data)
    recreated_split = build_split_manifest(graph_data)
    recreated_cases = build_pilot_cases(graph_data, node_meta)

    # Compare with existing files on disk
    with open(os.path.join(VAULT_DIR, "split_manifest.json"), "r", encoding="utf-8") as f:
        existing_split = json.load(f)

    with open(os.path.join(VAULT_DIR, "pilot_manifest.json"), "r", encoding="utf-8") as f:
        existing_pilot = json.load(f)

    assert recreated_split["partitions"]["pilot"]["nodes"] == existing_split["partitions"]["pilot"]["nodes"]
    assert recreated_split["partitions"]["dev"]["nodes"] == existing_split["partitions"]["dev"]["nodes"]
    assert recreated_split["partitions"]["test"]["nodes"] == existing_split["partitions"]["test"]["nodes"]

    recreated_cases_json = [c.model_dump(mode="json") for c in recreated_cases]
    assert recreated_cases_json == existing_pilot["cases"]
