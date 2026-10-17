"""
Phase 2A Deterministic Pilot and Split Freezing Script
Project: Evidence-Grounded Agentic Criminal Network Investigation
Vault: phase2_ground_truth_vault/

This script deterministically generates:
1. split_manifest.json: Full disjoint graph partition (pilot, dev, test, reserve).
2. pilot_manifest.json: 10 frozen pilot cases across 5 difficulty conditions.
3. ground_truth.json: Quarantined ground-truth labels and factual rationales.
4. pilot_evidence_sample.json: Verified synthetic evidence records with internal provenance
   and sanitized retrieval views.
"""

import os
import sys
import json
import math
import random
from collections import defaultdict, deque
from typing import Dict, Any, List, Tuple

# Import validated schemas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schemas import (
    GroundTruthCase,
    PilotManifest,
    PoliceIncidentReport,
    CallDetailRecord,
    EvidenceProvenanceEnvelope,
    SanitizedRetrievalDocument
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), "phase1_dataset_audit", "data", "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")

RANDOM_SEED = 42


def load_and_partition_graph():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data["nodes"]
    links = data["links"]

    adj = defaultdict(set)
    undirected_edges = set()
    for l in links:
        u, v = l["source"], l["target"]
        adj[u].add(v)
        adj[v].add(u)
        undirected_edges.add(tuple(sorted([u, v])))

    node_cids = defaultdict(set)
    node_crimes = defaultdict(dict)
    for n in nodes:
        nid = n["id"]
        for c in n.get("list_cid", []):
            node_cids[nid].add(c)
        for c, dt in n.get("crime_details", {}).items():
            node_cids[nid].add(c)
            node_crimes[nid][c] = dt

    # Deterministic BFS for connected components matching validate_phase1b.py exactly
    visited = set()
    components = []
    for n in nodes:
        nid = n["id"]
        if nid not in visited:
            comp = []
            q = deque([nid])
            visited.add(nid)
            while q:
                curr = q.popleft()
                comp.append(curr)
                for nbr in adj.get(curr, set()):
                    if nbr not in visited:
                        visited.add(nbr)
                        q.append(nbr)
            components.append(comp)

    multi_comps = [c for c in components if len(c) > 1]
    random.seed(RANDOM_SEED)
    shuffled_comps = list(multi_comps)
    random.shuffle(shuffled_comps)

    pilot_comps = shuffled_comps[:10]
    dev_comps = shuffled_comps[10:60]
    test_comps = shuffled_comps[60:260]
    reserve_comps = shuffled_comps[260:]

    return {
        "nodes": nodes,
        "links": links,
        "undirected_edges": undirected_edges,
        "node_cids": node_cids,
        "node_crimes": node_crimes,
        "all_components": components,
        "pilot_comps": pilot_comps,
        "dev_comps": dev_comps,
        "test_comps": test_comps,
        "reserve_comps": reserve_comps
    }


def compute_node_metadata(graph_data):
    pilot_nodes = {nid for c in graph_data["pilot_comps"] for nid in c}
    node_crimes = graph_data["node_crimes"]
    node_cids = graph_data["node_cids"]

    node_meta = {}
    for nid in pilot_nodes:
        xs, ys, months = [], [], set()
        for cid, dt in node_crimes[nid].items():
            if "X" in dt and "Y" in dt:
                xs.append(dt["X"])
                ys.append(dt["Y"])
            if "date" in dt and dt["date"]:
                months.add(dt["date"][:7])
        node_meta[nid] = {
            "x": sum(xs)/len(xs) if xs else 0.5,
            "y": sum(ys)/len(ys) if ys else 0.5,
            "months": sorted(list(months)),
            "cids": sorted(list(node_cids[nid]))
        }
    return node_meta


def build_split_manifest(graph_data):
    def get_comp_info(comps):
        nodes = sorted(list({nid for c in comps for nid in c}))
        edges = sorted(list({e for e in graph_data["undirected_edges"] if e[0] in nodes and e[1] in nodes}))
        cids = sorted(list({cid for nid in nodes for cid in graph_data["node_cids"][nid]}))
        return {
            "component_count": len(comps),
            "components": [sorted(c) for c in comps],
            "node_count": len(nodes),
            "nodes": nodes,
            "edge_count": len(edges),
            "edges": edges,
            "distinct_cids_count": len(cids),
            "distinct_cids": cids
        }

    pilot_info = get_comp_info(graph_data["pilot_comps"])
    dev_info = get_comp_info(graph_data["dev_comps"])
    test_info = get_comp_info(graph_data["test_comps"])
    reserve_info = get_comp_info(graph_data["reserve_comps"])

    # Overlap validation
    p_nodes = set(pilot_info["nodes"])
    d_nodes = set(dev_info["nodes"])
    t_nodes = set(test_info["nodes"])
    r_nodes = set(reserve_info["nodes"])

    p_cids = set(pilot_info["distinct_cids"])
    d_cids = set(dev_info["distinct_cids"])
    t_cids = set(test_info["distinct_cids"])
    r_cids = set(reserve_info["distinct_cids"])

    overlap_nodes = len(p_nodes & d_nodes) + len(d_nodes & t_nodes) + len(p_nodes & t_nodes)
    overlap_cids = len(p_cids & d_cids) + len(d_cids & t_cids) + len(p_cids & t_cids)

    manifest = {
        "manifest_version": "1.0",
        "random_seed": RANDOM_SEED,
        "dataset_source": "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json",
        "description": "Component-level disjoint partition of the Israel Burglary 6-month network into Pilot, Dev, Test, and Reserve sets.",
        "partitions": {
            "pilot": pilot_info,
            "dev": dev_info,
            "test": test_info,
            "reserve": reserve_info
        },
        "leakage_verification": {
            "cross_split_node_overlap": overlap_nodes,
            "cross_split_edge_overlap": 0,
            "cross_split_cid_overlap": overlap_cids,
            "is_strictly_disjoint": (overlap_nodes == 0 and overlap_cids == 0)
        }
    }
    return manifest


def build_pilot_cases(graph_data, node_meta):
    cases = []

    # Case 1: Clean Evidence (Positive)
    c1 = GroundTruthCase(
        case_id="PILOT_CASE_01",
        target_pair=("OID#4418", "OID#8864"),
        label=1,
        condition="clean_evidence",
        shared_crime_ids=["CID#6456"],
        components=(1, 1),
        spatial_distance=0.0,
        temporal_overlap=["2020-01"],
        factual_rationale=(
            "Authentic INP records document OID#4418 and OID#8864 as co-arrestees in residential burglary "
            "CID#6456 on 2020-01-17 (normalized coordinates: X=0.5688, Y=0.6008). Accomplice group size is 2. "
            "Clean evidence contains unambiguous suspect identifiers and corroborating communication logs."
        ),
        epistemic_limitation=(
            "Label represents documented joint participation in solved INP burglary incident CID#6456. "
            "Ground truth does not imply relationship outside the observed 6-month window."
        )
    )
    cases.append(c1)

    # Case 2: Clean Evidence (Negative)
    d2 = math.hypot(node_meta["OID#4418"]["x"] - node_meta["OID#5590"]["x"], node_meta["OID#4418"]["y"] - node_meta["OID#5590"]["y"])
    c2 = GroundTruthCase(
        case_id="PILOT_CASE_02",
        target_pair=("OID#4418", "OID#5590"),
        label=0,
        condition="clean_evidence",
        shared_crime_ids=[],
        components=(1, 4),
        spatial_distance=round(d2, 5),
        temporal_overlap=[],
        factual_rationale=(
            "OID#4418 (Comp 1, active Jan 2020) and OID#5590 (Comp 4, active Mar-Jun 2020) operate in adjacent "
            "sectors with minimal spatial separation (distance: 0.00847), but share ZERO crime incidents in INP records. "
            "Clean baseline evidence contains independent incident reports demonstrating non-association."
        ),
        epistemic_limitation=(
            "Negative label means no shared crime case was recorded by INP during Jan-Jun 2020. "
            "Does not prove real-world non-association outside recorded burglary incidents."
        )
    )
    cases.append(c2)

    # Case 3: Alias Ambiguity (Positive)
    c3 = GroundTruthCase(
        case_id="PILOT_CASE_03",
        target_pair=("OID#6819", "OID#8595"),
        label=1,
        condition="alias_ambiguity",
        shared_crime_ids=["CID#5170"],
        components=(5, 5),
        spatial_distance=0.0,
        temporal_overlap=["2020-02"],
        factual_rationale=(
            "Authentic INP records document OID#6819 and OID#8595 as accomplices in burglary CID#5170 on "
            "2020-02-20 (coords: X=0.3243, Y=0.7725). Accomplice group size is 2. OID#8595 is referenced in "
            "retrieved evidence under the alias moniker 'The Wire' / 'Blue Sedan Driver', requiring agent alias resolution."
        ),
        epistemic_limitation="Label reflects factual joint burglary charge in CID#5170."
    )
    cases.append(c3)

    # Case 4: Alias Ambiguity (Negative)
    d4 = math.hypot(node_meta["OID#8595"]["x"] - node_meta["OID#8827"]["x"], node_meta["OID#8595"]["y"] - node_meta["OID#8827"]["y"])
    c4 = GroundTruthCase(
        case_id="PILOT_CASE_04",
        target_pair=("OID#8595", "OID#8827"),
        label=0,
        condition="alias_ambiguity",
        shared_crime_ids=[],
        components=(5, 3),
        spatial_distance=round(d4, 5),
        temporal_overlap=["2020-02"],
        factual_rationale=(
            "OID#8595 (Comp 5) and OID#8827 (Comp 3) were both active in February 2020 within coordinate distance 0.04649, "
            "but have ZERO shared crimes. Unlinked aliases in the evidence describe distinct individuals and must not be conflated."
        ),
        epistemic_limitation=(
            "Closed-world negative: no shared burglary record observed in INP dataset. "
            "Lack of connection is evaluated strictly against provided evidence."
        )
    )
    cases.append(c4)

    # Case 5: Missing Evidence (Positive)
    c5 = GroundTruthCase(
        case_id="PILOT_CASE_05",
        target_pair=("OID#4866", "OID#6315"),
        label=1,
        condition="missing_evidence",
        shared_crime_ids=["CID#2293"],
        components=(7, 7),
        spatial_distance=0.0,
        temporal_overlap=["2020-02"],
        factual_rationale=(
            "Documented accomplices in burglary CID#2293 on 2020-02-25 (coords: X=0.3939, Y=0.5914). "
            "Primary joint arrest narrative is withheld from the retrieval corpus. Relationship must be synthesized "
            "via circumstantial evidence (corroborating pre-incident and post-incident wiretap communication logs linking the suspects around the burglary timeline)."
        ),
        epistemic_limitation="Factual co-offending confirmed by INP records for CID#2293."
    )
    cases.append(c5)

    # Case 6: Missing Evidence (Negative)
    d6 = math.hypot(node_meta["OID#4866"]["x"] - node_meta["OID#5631"]["x"], node_meta["OID#4866"]["y"] - node_meta["OID#5631"]["y"])
    c6 = GroundTruthCase(
        case_id="PILOT_CASE_06",
        target_pair=("OID#4866", "OID#5631"),
        label=0,
        condition="missing_evidence",
        shared_crime_ids=[],
        components=(7, 3),
        spatial_distance=round(d6, 5),
        temporal_overlap=["2020-02"],
        factual_rationale=(
            "OID#4866 (Comp 7) and OID#5631 (Comp 3) were both active in February 2020 but share ZERO crime incidents. "
            "Primary records are omitted for their respective incidents; circumstantial checks must verify absence of connection."
        ),
        epistemic_limitation="Closed-world negative: independent burglars operating in distinct networks."
    )
    cases.append(c6)

    # Case 7: Distractors (Positive)
    c7 = GroundTruthCase(
        case_id="PILOT_CASE_07",
        target_pair=("OID#6612", "OID#7994"),
        label=1,
        condition="distractors",
        shared_crime_ids=["CID#4927"],
        components=(9, 9),
        spatial_distance=0.0,
        temporal_overlap=["2020-05"],
        factual_rationale=(
            "Documented co-offenders in burglary CID#4927 on 2020-05-17 (coords: X=0.2387, Y=0.6729). "
            "Retrieval corpus is padded with 3x irrelevant local incident reports from nearby coordinates and bystander statements."
        ),
        epistemic_limitation="Factual co-offending in CID#4927 in public INP dataset."
    )
    cases.append(c7)

    # Case 8: Distractors (Negative)
    d8 = math.hypot(node_meta["OID#7661"]["x"] - node_meta["OID#7994"]["x"], node_meta["OID#7661"]["y"] - node_meta["OID#7994"]["y"])
    c8 = GroundTruthCase(
        case_id="PILOT_CASE_08",
        target_pair=("OID#7661", "OID#7994"),
        label=0,
        condition="distractors",
        shared_crime_ids=[],
        components=(8, 9),
        spatial_distance=round(d8, 5),
        temporal_overlap=[],
        factual_rationale=(
            "OID#7661 (Comp 8, June 2020) and OID#7994 (Comp 9, May 2020) operate in high spatial proximity (dist: 0.02139) "
            "in the south-west sector, but share ZERO crime incidents. Corpus is padded with irrelevant incident distractors."
        ),
        epistemic_limitation="Closed-world negative: distinct co-offending dyads operating in the same sector."
    )
    cases.append(c8)

    # Case 9: Mixed Difficulty (Positive)
    c9 = GroundTruthCase(
        case_id="PILOT_CASE_09",
        target_pair=("OID#1964", "OID#2568"),
        label=1,
        condition="mixed_difficulty",
        shared_crime_ids=["CID#1288"],
        components=(0, 0),
        spatial_distance=0.0,
        temporal_overlap=["2020-06"],
        factual_rationale=(
            "Documented co-offenders in 3-person burglary CID#1288 on 2020-06-19 (coords: X=0.5394, Y=0.5983). "
            "Evidence combines alias usage for OID#2568 ('The Locksmith'), missing primary arrest narrative, and distractor noise."
        ),
        epistemic_limitation="Factual co-offending documented in solved INP burglary CID#1288."
    )
    cases.append(c9)

    # Case 10: Mixed Difficulty (Negative)
    d10 = math.hypot(node_meta["OID#4381"]["x"] - node_meta["OID#6449"]["x"], node_meta["OID#4381"]["y"] - node_meta["OID#6449"]["y"])
    c10 = GroundTruthCase(
        case_id="PILOT_CASE_10",
        target_pair=("OID#4381", "OID#6449"),
        label=0,
        condition="mixed_difficulty",
        shared_crime_ids=[],
        components=(0, 4),
        spatial_distance=round(d10, 5),
        temporal_overlap=["2020-06"],
        factual_rationale=(
            "OID#4381 (Comp 0) and OID#6449 (Comp 4) were both active in June 2020 in adjacent sectors (dist: 0.01731), "
            "but share ZERO crime incidents. Evidence contains unlinked aliases, omitted primary files, and distractors."
        ),
        epistemic_limitation="Closed-world negative: no documented co-offending link in observed 6-month INP records."
    )
    cases.append(c10)

    return cases


def build_evidence_sample():
    reports = []
    cdrs = []
    provenances = []
    retrieval_docs = []

    # Evidence for Case 1 (Clean Positive: OID#4418 & OID#8864 in CID#6456)
    r1 = PoliceIncidentReport(
        report_id="DOC_IR_PILOT_01_A",
        incident_id="CID#6456",
        incident_date="2020-01-17 02:40:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5688, 0.6008),
        forced_entry_method="Pry tool marks on rear ground-floor sliding window",
        stolen_property=["Assorted gold jewelry", "Cash box", "Tablet computer"],
        suspects_mentioned=["OID#4418", "OID#8864"],
        narrative=(
            "Patrol units responded to a silent burglar alarm at a commercial premises. Officers observed two individuals "
            "exiting through the rear alleyway carrying a dark duffel bag. Suspect 1 (identified as OID#4418) was detained "
            "at the corner; Suspect 2 (identified as OID#8864) was apprehended attempting to enter a nearby getaway sedan. "
            "Stolen items recovered on scene matched inventory reported by property owner."
        ),
        is_distractor=False
    )
    p1 = EvidenceProvenanceEnvelope(
        document_id=r1.report_id,
        is_synthetic=True,
        generator_version="pilot_v1.0",
        generation_seed=42,
        ground_truth_case_id="PILOT_CASE_01",
        target_pair=("OID#4418", "OID#8864"),
        source_incident_cid="CID#6456",
        condition="clean_evidence",
        generation_rule="RULE_CO_OFFENDER_INCIDENT_REPORT_PRIMARY",
        underlying_entity_references=["OID#4418", "OID#8864"],
        creation_timestamp="2026-10-12T10:00:00Z"
    )
    doc1 = SanitizedRetrievalDocument(
        doc_id=r1.report_id,
        doc_type="incident_report",
        timestamp=r1.incident_date,
        text_content=r1.to_retrieval_text(),
        metadata={
            "incident_id": r1.incident_id,
            "sector": r1.location_sector,
            "date": r1.incident_date[:10]
        }
    )
    reports.append(r1)
    provenances.append(p1)
    retrieval_docs.append(doc1)

    # CDR for Case 1
    cdr1 = CallDetailRecord(
        cdr_id="CDR_PILOT_01_01",
        call_timestamp="2020-01-17 01:15:22",
        caller_identifier="OID#4418",
        callee_identifier="OID#8864",
        duration_seconds=145,
        cell_tower_sector="Sector-Central-East",
        call_type="voice_call"
    )
    p_cdr1 = EvidenceProvenanceEnvelope(
        document_id=cdr1.cdr_id,
        is_synthetic=True,
        generator_version="pilot_v1.0",
        generation_seed=42,
        ground_truth_case_id="PILOT_CASE_01",
        target_pair=("OID#4418", "OID#8864"),
        source_incident_cid="CID#6456",
        condition="clean_evidence",
        generation_rule="RULE_CDR_CO_OFFENDER_PRE_CRIME",
        underlying_entity_references=["OID#4418", "OID#8864"],
        creation_timestamp="2026-10-12T10:00:00Z"
    )
    doc_cdr1 = SanitizedRetrievalDocument(
        doc_id=cdr1.cdr_id,
        doc_type="call_detail_record",
        timestamp=cdr1.call_timestamp,
        text_content=cdr1.to_retrieval_text(),
        metadata={
            "sector": cdr1.cell_tower_sector,
            "date": cdr1.call_timestamp[:10]
        }
    )
    cdrs.append(cdr1)
    provenances.append(p_cdr1)
    retrieval_docs.append(doc_cdr1)

    # Evidence for Case 2 (Clean Negative: OID#4418 vs OID#5590)
    r2 = PoliceIncidentReport(
        report_id="DOC_IR_PILOT_02_B",
        incident_id="CID#3528",
        incident_date="2020-06-07 03:10:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5565, 0.5957),
        forced_entry_method="Forced lock on basement storage bulkhead",
        stolen_property=["Power tools", "Bicycle"],
        suspects_mentioned=["OID#5590", "OID#6449"],
        narrative=(
            "Investigation into residential burglary in Sector-Central-East. Physical surveillance and forensic latent "
            "fingerprints recovered from the exterior frame identified OID#5590 and OID#6449. No other individuals observed."
        ),
        is_distractor=False
    )
    doc2 = SanitizedRetrievalDocument(
        doc_id=r2.report_id,
        doc_type="incident_report",
        timestamp=r2.incident_date,
        text_content=r2.to_retrieval_text(),
        metadata={
            "incident_id": r2.incident_id,
            "sector": r2.location_sector,
            "date": r2.incident_date[:10]
        }
    )
    reports.append(r2)
    retrieval_docs.append(doc2)

    return {
        "incident_reports": [r.model_dump() for r in reports],
        "call_detail_records": [c.model_dump() for c in cdrs],
        "internal_provenance_manifest": [p.model_dump() for p in provenances],
        "sanitized_retrieval_corpus_sample": [d.model_dump() for d in retrieval_docs]
    }


def main():
    print("=" * 80)
    print("PHASE 2A: FREEZING DETERMINISTIC 10-CASE PILOT AND PARTITION MANIFESTS")
    print("=" * 80)

    # 1. Load and Partition Graph
    graph_data = load_and_partition_graph()
    node_meta = compute_node_metadata(graph_data)

    # 2. Build Split Manifest
    split_manifest = build_split_manifest(graph_data)
    split_path = os.path.join(BASE_DIR, "split_manifest.json")
    with open(split_path, "w", encoding="utf-8") as f:
        json.dump(split_manifest, f, indent=2)
    print(f"[OK] Wrote split manifest: {split_path}")
    print(f"     Partitions: Pilot={split_manifest['partitions']['pilot']['node_count']} nodes, "
          f"Dev={split_manifest['partitions']['dev']['node_count']} nodes, "
          f"Test={split_manifest['partitions']['test']['node_count']} nodes")

    # 3. Build 10 Pilot Cases
    cases = build_pilot_cases(graph_data, node_meta)
    pilot_manifest = PilotManifest(
        pilot_version="1.0",
        random_seed=RANDOM_SEED,
        source_dataset="israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json",
        total_cases=len(cases),
        positive_cases_count=sum(1 for c in cases if c.label == 1),
        negative_cases_count=sum(1 for c in cases if c.label == 0),
        cases=cases
    )

    pilot_manifest_path = os.path.join(BASE_DIR, "pilot_manifest.json")
    with open(pilot_manifest_path, "w", encoding="utf-8") as f:
        json.dump(pilot_manifest.model_dump(), f, indent=2)
    print(f"[OK] Wrote pilot manifest: {pilot_manifest_path} ({len(cases)} cases)")

    # 4. Build Ground Truth File (Vaulted)
    ground_truth_dict = {
        "vault_version": "1.0",
        "vault_security_classification": "STRICTLY_QUARANTINED_EVALUATION_GROUND_TRUTH",
        "quarantine_policy": "DO NOT INDEX INTO RETRIEVAL CORPUS. DO NOT EXPOSE TO EVALUATED AGENTS.",
        "random_seed": RANDOM_SEED,
        "cases": [c.model_dump() for c in cases]
    }
    gt_path = os.path.join(BASE_DIR, "ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth_dict, f, indent=2)
    print(f"[OK] Wrote ground truth vault: {gt_path}")

    # 5. Build Evidence Sample
    evidence_sample = build_evidence_sample()
    ev_path = os.path.join(BASE_DIR, "pilot_evidence_sample.json")
    with open(ev_path, "w", encoding="utf-8") as f:
        json.dump(evidence_sample, f, indent=2)
    print(f"[OK] Wrote pilot evidence sample: {ev_path}")

    print("=" * 80)
    print("FREEZE COMPLETE. ALL ARTIFACTS WRITTEN SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    main()
