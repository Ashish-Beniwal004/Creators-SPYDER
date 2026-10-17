"""
Phase 2A.1 Consistency Audit Tests
Verifies:
1. Approved evidence types (only PoliceIncidentReport and CallDetailRecord; no pawn logs).
2. Negative-pair difficulty metrics and source verification.
3. Condition operationalization and absence of label/rationale leakage.
4. Evidential validity (no artificial negative assertions in retrieval text).
"""

import os
import json
import math
import pytest

VAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(os.path.dirname(VAULT_DIR), "phase1_dataset_audit", "data", "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")


@pytest.fixture(scope="module")
def vault_files():
    with open(os.path.join(VAULT_DIR, "ground_truth.json"), "r", encoding="utf-8") as f:
        gt = json.load(f)
    with open(os.path.join(VAULT_DIR, "pilot_manifest.json"), "r", encoding="utf-8") as f:
        pilot = json.load(f)
    with open(os.path.join(VAULT_DIR, "pilot_evidence_sample.json"), "r", encoding="utf-8") as f:
        sample = json.load(f)
    return {"gt": gt, "pilot": pilot, "sample": sample}


@pytest.fixture(scope="module")
def source_data():
    if not os.path.exists(DATA_PATH):
        pytest.skip(
            f"Raw Israel National Police source dataset missing: {DATA_PATH}. "
            "Data redistribution permission unverified; download from upstream URL in sources.md."
        )
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    node_meta = {}
    node_cids = {}
    for n in data["nodes"]:
        nid = n["id"]
        cids = set(n.get("list_cid", []))
        xs, ys, months = [], [], set()
        for cid, dt in n.get("crime_details", {}).items():
            cids.add(cid)
            if "X" in dt and "Y" in dt:
                xs.append(dt["X"])
                ys.append(dt["Y"])
            if "date" in dt and dt["date"]:
                months.add(dt["date"][:7])
        node_meta[nid] = {
            "x": sum(xs)/len(xs) if xs else 0.5,
            "y": sum(ys)/len(ys) if ys else 0.5,
            "months": sorted(list(months))
        }
        node_cids[nid] = cids
    return {"node_meta": node_meta, "node_cids": node_cids}


def test_approved_evidence_scope_no_pawn_or_unsupported_types(vault_files):
    """Verify that all rationales and schemas reference ONLY approved evidence (Incident Reports & CDRs)."""
    gt = vault_files["gt"]
    pilot = vault_files["pilot"]

    disallowed_keywords = ["pawn", "fencing transaction", "bank statement", "wire transfer", "financial ledger"]

    for case in gt["cases"]:
        rationale = case["factual_rationale"].lower()
        for bad_kw in disallowed_keywords:
            assert bad_kw not in rationale, (
                f"Case {case['case_id']} rationale contains disallowed evidence keyword '{bad_kw}'! "
                "Scope is restricted to police incident reports and call-detail records only."
            )

    for case in pilot["cases"]:
        rationale = case["factual_rationale"].lower()
        for bad_kw in disallowed_keywords:
            assert bad_kw not in rationale, (
                f"Pilot case {case['case_id']} contains disallowed keyword '{bad_kw}'!"
            )


def test_negative_pair_distance_and_month_verification(vault_files, source_data):
    """
    Audit each negative pilot pair directly against source data.
    Verifies that zero shared CIDs exist and validates recorded distance.
    """
    pilot = vault_files["pilot"]
    node_meta = source_data["node_meta"]
    node_cids = source_data["node_cids"]

    neg_cases = [c for c in pilot["cases"] if c["label"] == 0]
    assert len(neg_cases) == 5

    for c in neg_cases:
        u, v = c["target_pair"]
        assert u in node_meta
        assert v in node_meta

        # 1. Zero shared CIDs in source data
        shared = node_cids[u] & node_cids[v]
        assert len(shared) == 0, f"Negative pair ({u}, {v}) unexpectedly shares CIDs: {shared}"

        # 2. Compute exact distance from source data
        dist = math.hypot(node_meta[u]["x"] - node_meta[v]["x"], node_meta[u]["y"] - node_meta[v]["y"])
        assert abs(dist - c["spatial_distance"]) < 1e-4, (
            f"Case {c['case_id']}: recorded distance {c['spatial_distance']} differs from "
            f"computed distance {dist:.5f}"
        )

        # 3. Check months
        common_months = set(node_meta[u]["months"]) & set(node_meta[v]["months"])
        assert sorted(list(common_months)) == sorted(c["temporal_overlap"])


def test_condition_operationalization(vault_files):
    """Verify that every condition is properly documented and operationalized in case metadata."""
    gt = vault_files["gt"]
    cases_by_cond = {c["condition"]: [] for c in gt["cases"]}
    for c in gt["cases"]:
        cases_by_cond[c["condition"]].append(c)

    # Clean Evidence
    clean = cases_by_cond["clean_evidence"]
    assert len(clean) == 2
    assert any("clean" in c["factual_rationale"].lower() for c in clean)

    # Alias Ambiguity
    alias = cases_by_cond["alias_ambiguity"]
    assert len(alias) == 2
    assert any("alias" in c["factual_rationale"].lower() for c in alias)

    # Missing Evidence
    missing = cases_by_cond["missing_evidence"]
    assert len(missing) == 2
    assert any("withheld" in c["factual_rationale"].lower() or "omitted" in c["factual_rationale"].lower() for c in missing)

    # Distractors
    distractors = cases_by_cond["distractors"]
    assert len(distractors) == 2
    assert any("distractor" in c["factual_rationale"].lower() for c in distractors)

    # Mixed Difficulty
    mixed = cases_by_cond["mixed_difficulty"]
    assert len(mixed) == 2
    assert any("combines" in c["factual_rationale"].lower() or "degraded" in c["factual_rationale"].lower() for c in mixed)


def test_retrieval_facing_evidence_no_leakage_or_artificial_negation(vault_files):
    """
    Verify that retrieval-facing evidence chunks contain:
    1. No ground-truth labels or hidden conditions.
    2. No artificial assertions of non-relationship for negative pairs.
    """
    sample = vault_files["sample"]
    retrieval_docs = sample["sanitized_retrieval_corpus_sample"]

    forbidden_text = [
        "ground truth", "label: 1", "label: 0", "is_co_offender",
        "never communicated", "no relationship", "definitely innocent",
        "proven negative", "condition:"
    ]

    for doc in retrieval_docs:
        text = doc["text_content"].lower()
        for bad_str in forbidden_text:
            assert bad_str not in text, f"Leakage/artificial text violation in doc {doc['doc_id']}: '{bad_str}' found!"
        # Metadata check
        for k in doc["metadata"].keys():
            assert k.lower() not in ["label", "condition", "is_co_offender", "rationale", "target_pair"]
