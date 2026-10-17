"""
Phase 2F Full Benchmark Target Pairs and Ground Truth Construction
Project: Evidence-Grounded Agentic Criminal Network Investigation
Vault: phase2_ground_truth_vault/build_test_benchmark.py

Constructs the 200-case test benchmark ground-truth assets:
1. phase2_ground_truth_vault/test_manifest.json (TestManifest with 200 cases)
2. phase2_ground_truth_vault/test_ground_truth.json (Quarantined vault view)
3. phase2_experiment/test_target_pairs.json (Sanitized unlabelled target pairs)

Strict Invariants:
- Exactly 200 cases (100 positive, 100 negative).
- Exactly 40 cases per condition (20 positive, 20 negative).
- Strictly disjoint from pilot, dev, and reserve partitions.
- Zero cross-split entity or crime leakage.
"""

import os
import sys
import json
import math
import random
from typing import Dict, Any, List, Tuple, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

VAULT_DIR = os.path.join(REPO_ROOT, "phase2_ground_truth_vault")
if VAULT_DIR not in sys.path:
    sys.path.insert(0, VAULT_DIR)

from schemas import GroundTruthCase, TestManifest

RANDOM_SEED = 42
DATA_PATH = os.path.join(REPO_ROOT, "phase1_dataset_audit", "data", "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")
SPLIT_PATH = os.path.join(VAULT_DIR, "split_manifest.json")


def load_dataset_and_split():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = {n["id"]: n for n in data["nodes"]}
    links = data["links"]

    with open(SPLIT_PATH, "r", encoding="utf-8") as f:
        split = json.load(f)

    return nodes, links, split


def build_test_cases() -> Tuple[List[GroundTruthCase], List[Tuple[str, str]]]:
    nodes, links, split = load_dataset_and_split()
    test_info = split["partitions"]["test"]
    test_comps = test_info["components"]
    test_nodes = set(test_info["nodes"])
    test_edges = [tuple(sorted(e)) for e in test_info["edges"]]

    # 1. Extract 100 positive pairs from test components 0..99
    pos_pairs_data = []
    for c_idx in range(100):
        comp = test_comps[c_idx]
        c_set = set(comp)
        c_edges = sorted([e for e in test_edges if e[0] in c_set and e[1] in c_set])
        u, v = c_edges[0]
        # Get shared CIDs
        u_cids = set(nodes[u].get("list_cid", []))
        v_cids = set(nodes[v].get("list_cid", []))
        shared = sorted(list(u_cids & v_cids))
        assert len(shared) > 0, f"Positive pair ({u}, {v}) has no shared CIDs!"
        primary_cid = shared[0]

        # Extract crime details
        details = nodes[u].get("crime_details", {}).get(primary_cid) or nodes[v].get("crime_details", {}).get(primary_cid, {})
        crime_date = details.get("date", "2020-03-15 02:30:00")
        month = crime_date[:7]
        pos_pairs_data.append({
            "pair": (u, v),
            "shared_cids": shared,
            "primary_cid": primary_cid,
            "components": (c_idx, c_idx),
            "spatial_distance": 0.0,
            "temporal_overlap": [month],
            "crime_date": crime_date,
            "coords": (details.get("X", 0.5), details.get("Y", 0.5)),
            "num_offenders": details.get("num_of_offenders", len(comp))
        })

    # 2. Extract node metadata for hard negatives
    node_meta = {}
    for nid in test_nodes:
        n = nodes[nid]
        xs, ys, months = [], [], set()
        for cid, dt in n.get("crime_details", {}).items():
            if "X" in dt and "Y" in dt:
                xs.append(dt["X"])
                ys.append(dt["Y"])
            if "date" in dt and dt["date"]:
                months.add(dt["date"][:7])
        node_meta[nid] = {
            "x": sum(xs) / len(xs) if xs else 0.5,
            "y": sum(ys) / len(ys) if ys else 0.5,
            "months": months,
            "cids": set(n.get("list_cid", []))
        }

    node_to_comp = {}
    for c_idx, comp in enumerate(test_comps):
        for nid in comp:
            node_to_comp[nid] = c_idx

    # Candidate hard negatives
    candidates = []
    test_node_list = sorted(list(test_nodes))
    for i in range(len(test_node_list)):
        u = test_node_list[i]
        for j in range(i + 1, len(test_node_list)):
            v = test_node_list[j]
            if node_to_comp[u] == node_to_comp[v]:
                continue
            common_months = node_meta[u]["months"] & node_meta[v]["months"]
            if not common_months:
                continue
            if node_meta[u]["cids"] & node_meta[v]["cids"]:
                continue
            dist = math.hypot(node_meta[u]["x"] - node_meta[v]["x"], node_meta[u]["y"] - node_meta[v]["y"])
            candidates.append((dist, u, v, sorted(list(common_months)), node_to_comp[u], node_to_comp[v]))

    candidates.sort(key=lambda x: (x[0], x[1], x[2]))

    # Select 100 hard negatives with unique nodes
    selected_negatives_data = []
    used_nodes = set()
    for dist, u, v, m, c_u, c_v in candidates:
        if u not in used_nodes and v not in used_nodes:
            pair = tuple(sorted([u, v]))
            selected_negatives_data.append({
                "pair": pair,
                "shared_cids": [],
                "components": (min(c_u, c_v), max(c_u, c_v)),
                "spatial_distance": round(dist, 5),
                "temporal_overlap": m,
                "coords_u": (node_meta[pair[0]]["x"], node_meta[pair[0]]["y"]),
                "coords_v": (node_meta[pair[1]]["x"], node_meta[pair[1]]["y"])
            })
            used_nodes.add(u)
            used_nodes.add(v)
            if len(selected_negatives_data) == 100:
                break

    assert len(pos_pairs_data) == 100
    assert len(selected_negatives_data) == 100

    # 3. Assemble 200 cases across 5 conditions (20 positive, 20 negative per condition)
    conditions = [
        "clean_evidence",
        "alias_ambiguity",
        "missing_evidence",
        "distractors",
        "mixed_difficulty"
    ]

    all_cases: List[GroundTruthCase] = []
    case_counter = 1

    for cond_idx, cond in enumerate(conditions):
        pos_chunk = pos_pairs_data[cond_idx * 20 : (cond_idx + 1) * 20]
        neg_chunk = selected_negatives_data[cond_idx * 20 : (cond_idx + 1) * 20]

        # 20 positive cases
        for p in pos_chunk:
            c_id = f"TEST_CASE_{case_counter:03d}"
            case_counter += 1
            u, v = p["pair"]
            cid = p["primary_cid"]
            date_str = p["crime_date"][:10]
            num_off = p["num_offenders"]

            if cond == "clean_evidence":
                rationale = (
                    f"Authentic INP records document {u} and {v} as co-arrestees in residential burglary "
                    f"{cid} on {date_str}. Accomplice group size is {num_off}. "
                    f"Clean evidence contains unambiguous suspect identifiers and corroborating communication logs."
                )
            elif cond == "alias_ambiguity":
                rationale = (
                    f"Authentic INP records document {u} and {v} as accomplices in burglary {cid} on {date_str}. "
                    f"Accomplice group size is {num_off}. Subject {v} is referenced under a street alias moniker "
                    f"requiring agent alias resolution against authentic field intelligence."
                )
            elif cond == "missing_evidence":
                rationale = (
                    f"Documented accomplices in burglary {cid} on {date_str}. Primary joint arrest narrative is "
                    f"withheld from the retrieval corpus. Relationship must be synthesized via circumstantial wiretap logs."
                )
            elif cond == "distractors":
                rationale = (
                    f"Documented co-offenders in burglary {cid} on {date_str}. Retrieval corpus is padded with "
                    f"irrelevant local incident reports from nearby coordinates."
                )
            elif cond == "mixed_difficulty":
                rationale = (
                    f"Documented co-offenders in burglary {cid} on {date_str}. Evidence combines alias usage, "
                    f"distractor noise, and circumstantial wiretap communications."
                )

            gt_case = GroundTruthCase(
                case_id=c_id,
                target_pair=p["pair"],
                label=1,
                condition=cond,
                shared_crime_ids=p["shared_cids"],
                components=p["components"],
                spatial_distance=0.0,
                temporal_overlap=p["temporal_overlap"],
                factual_rationale=rationale,
                epistemic_limitation=f"Label reflects factual joint burglary charge in {cid} within evaluation window."
            )
            all_cases.append(gt_case)

        # 20 negative cases
        for n in neg_chunk:
            c_id = f"TEST_CASE_{case_counter:03d}"
            case_counter += 1
            u, v = n["pair"]
            dist_val = n["spatial_distance"]
            months_str = ", ".join(n["temporal_overlap"])

            if cond == "clean_evidence":
                rationale = (
                    f"{u} (Comp {n['components'][0]}) and {v} (Comp {n['components'][1]}) were both active during "
                    f"{months_str} with minimal spatial separation (distance: {dist_val}), but share ZERO crime incidents. "
                    f"Clean baseline evidence contains independent incident reports demonstrating non-association."
                )
            elif cond == "alias_ambiguity":
                rationale = (
                    f"{u} and {v} operate in geographic proximity during {months_str} with distance {dist_val}, but share "
                    f"ZERO crimes. Unlinked aliases in retrieved evidence describe distinct individuals and must not be conflated."
                )
            elif cond == "missing_evidence":
                rationale = (
                    f"{u} and {v} were active in {months_str} but share ZERO crime incidents. Primary records are omitted "
                    f"for respective independent incidents; circumstantial checks must verify absence of connection."
                )
            elif cond == "distractors":
                rationale = (
                    f"{u} and {v} operate in high spatial proximity (dist: {dist_val}) but share ZERO crime incidents. "
                    f"Corpus is padded with irrelevant incident distractors."
                )
            elif cond == "mixed_difficulty":
                rationale = (
                    f"{u} and {v} were active during {months_str} in adjacent sectors (dist: {dist_val}), but share ZERO crime "
                    f"incidents. Evidence contains unlinked aliases, omitted primary files, and distractors."
                )

            gt_case = GroundTruthCase(
                case_id=c_id,
                target_pair=n["pair"],
                label=0,
                condition=cond,
                shared_crime_ids=[],
                components=n["components"],
                spatial_distance=dist_val,
                temporal_overlap=n["temporal_overlap"],
                factual_rationale=rationale,
                epistemic_limitation="Closed-world negative: no shared burglary record observed in INP dataset."
            )
            all_cases.append(gt_case)

    assert len(all_cases) == 200
    pos_count = sum(1 for c in all_cases if c.label == 1)
    neg_count = sum(1 for c in all_cases if c.label == 0)
    assert pos_count == 100
    assert neg_count == 100

    target_pairs_only = [c.target_pair for c in all_cases]
    return all_cases, target_pairs_only


def save_test_benchmark(output_vault_dir: Optional[str] = None, output_exp_dir: Optional[str] = None):
    all_cases, target_pairs = build_test_cases()
    target_vault_dir = output_vault_dir or VAULT_DIR
    target_exp_dir = output_exp_dir or os.path.join(REPO_ROOT, "phase2_experiment")

    # 1. Save test_manifest.json
    manifest = TestManifest(
        manifest_version="1.0",
        random_seed=RANDOM_SEED,
        source_dataset="israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json",
        total_cases=len(all_cases),
        positive_cases_count=100,
        negative_cases_count=100,
        cases=all_cases
    )

    manifest_path = os.path.join(target_vault_dir, "test_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))
    print(f"Saved: {manifest_path} ({len(all_cases)} cases)")

    # 2. Save test_ground_truth.json (Vault view)
    gt_vault = {
        "vault_version": "1.0",
        "vault_security_classification": "STRICTLY_QUARANTINED_EVALUATION_GROUND_TRUTH",
        "quarantine_policy": "DO NOT INDEX INTO RETRIEVAL CORPUS. DO NOT EXPOSE TO EVALUATED AGENTS.",
        "random_seed": RANDOM_SEED,
        "cases": [c.model_dump() for c in all_cases]
    }
    gt_path = os.path.join(target_vault_dir, "test_ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(gt_vault, f, indent=2)
    print(f"Saved: {gt_path}")

    # 3. Save phase2_experiment/test_target_pairs.json (Sanitized unlabelled input)
    exp_targets_path = os.path.join(target_exp_dir, "test_target_pairs.json")
    unlabelled_payload = {
        "description": "Sanitized unlabelled target entity pairs for SPYDER Phase 2F/3 full 200-case test benchmark.",
        "total_pairs": len(target_pairs),
        "pairs": [list(p) for p in target_pairs]
    }
    with open(exp_targets_path, "w", encoding="utf-8") as f:
        json.dump(unlabelled_payload, f, indent=2)
    print(f"Saved: {exp_targets_path} ({len(target_pairs)} target pairs)")


# Stable public alias
build_test_benchmark = save_test_benchmark


if __name__ == "__main__":
    print("=" * 80)
    print("BUILDING SPYDER 200-CASE TEST BENCHMARK GROUND TRUTH ASSETS")
    print("=" * 80)
    save_test_benchmark()
    print("Done.")
