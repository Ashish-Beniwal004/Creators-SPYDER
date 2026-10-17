"""
Phase 2F Full Benchmark Synthetic Evidence Corpus Generator
Project: Evidence-Grounded Agentic Criminal Network Investigation
Corpus: phase2_corpus/generate_test_evidence.py

Generates the complete synthetic evidence corpus for all 200 test cases:
1. phase2_corpus/test_retrieval_documents.jsonl (Sanitized public retrieval corpus)
2. phase2_corpus/test_internal_provenance.jsonl (Internal provenance envelopes)

Strict Invariants:
- Uses ONLY PoliceIncidentReport and CallDetailRecord schemas.
- All retrieval document IDs are strictly opaque hashes (DOC_IR_<hex8>, CDR_<hex8>).
- Synthetic incident references (INC-2020-xxxx) replace all authentic crime CIDs.
- Missing-evidence positive cases genuinely omit the primary joint arrest narrative.
- Full compliance with SanitizedRetrievalDocument validation (zero leakage tokens).
"""

import os
import sys
import json
import hashlib
from typing import List, Tuple, Dict, Any, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

VAULT_DIR = os.path.join(REPO_ROOT, "phase2_ground_truth_vault")
if VAULT_DIR not in sys.path:
    sys.path.insert(0, VAULT_DIR)

from schemas import (
    PoliceIncidentReport,
    CallDetailRecord,
    EvidenceProvenanceEnvelope,
    SanitizedRetrievalDocument,
    validate_retrieval_corpus,
)

CORPUS_DIR = os.path.dirname(os.path.abspath(__file__))
RANDOM_SEED = 42
GENERATOR_VERSION = "test_v1.0"
CREATION_TIMESTAMP = "2026-10-13T19:00:00Z"

TEST_MANIFEST_PATH = os.path.join(VAULT_DIR, "test_manifest.json")
RAW_DATA_PATH = os.path.join(REPO_ROOT, "phase1_dataset_audit", "data", "israel_lea_inp_burglary_offender_id_network_from_2020-01-01_to_2020-06-30.json")

# Pool of street monikers for alias conditions
ALIAS_MONIKERS = [
    "The Wire", "The Spark", "The Driver", "The Locksmith", "The Raven", "The Ghost",
    "The Falcon", "The Shadow", "The Viper", "The Hawk", "The Whisper", "The Jackal",
    "The Lynx", "The Fox", "The Spider", "The Badger", "The Bishop", "The Rook",
    "The Hammer", "The Wolf", "The Baron", "The Cobra", "The Echo", "The Mirage",
    "The Phantom", "The Sentry", "The Scout", "The Nomad", "The Courier", "The Weaver",
    "The Craftsman", "The Chemist", "The Pilot", "The Navigator", "The Warden", "The Smith",
    "The Miller", "The Porter", "The Tanner", "The Mason", "The Thatcher", "The Hunter",
    "The Tracker", "The Archer", "The Ranger", "The Fletcher", "The Cooper", "The Carpenter",
    "The Wheelwright", "The Sawyer", "The Forrester", "The Fisher", "The Fowler", "The Shepherd"
]

FORCED_ENTRY_METHODS = [
    "Pry tool marks on rear ground-floor sliding patio door",
    "Forced lock on basement storage bulkhead door",
    "Jimmied latch on rear ground-floor sliding window",
    "Smashed side windowpane adjacent to master bedroom door",
    "Pry marks on exterior commercial delivery entryway",
    "Forced entry through second-floor balcony French doors",
    "Cut padlock on perimeter security gate and jimmied side door",
    "Bypassed deadbolt using mechanical lock-picking tools",
    "Forced deadbolt lock on rear garage service door",
    "Pried open security grille on ground-floor kitchen window",
]

STOLEN_PROPERTY_SETS = [
    ["Assorted gold jewelry", "Cash box", "Tablet computer"],
    ["Designer watches", "Foreign currency", "Collector coins"],
    ["High-value power tools", "Bicycle", "Cordless equipment"],
    ["Laptop computers", "Safe contents", "Silverware"],
    ["High-end audio equipment", "Vintage cameras", "Cash envelope"],
    ["Commercial inventory", "Desktop workstation", "Handheld scanners"],
    ["Precious gemstones", "Estate jewelry", "Bank notes"],
    ["Home security DVR", "Jewelry armoire contents", "Designer bags"],
]


def make_opaque_id(prefix: str, token: str) -> str:
    """Deterministic, opaque 8-character hex document identifier."""
    raw = f"{RANDOM_SEED}_{prefix}_{token}".encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()[:8]
    return f"{prefix}_{h}"


def get_sector_name(x: float, y: float) -> str:
    """Maps normalized coordinates (X, Y) to metropolitan sector names."""
    ew = "West" if x < 0.33 else ("Central" if x < 0.66 else "East")
    ns = "South" if y < 0.33 else ("Central" if y < 0.66 else "North")
    if ew == "Central" and ns == "Central":
        return "Sector-Central"
    return f"Sector-{ns}-{ew}"


def build_synthetic_incident_id(token: str) -> str:
    """Maps source token to non-semantic synthetic incident identifier INC-2020-xxxx."""
    raw = f"{RANDOM_SEED}_{token}".encode("utf-8")
    h = int(hashlib.sha256(raw).hexdigest()[:6], 16) % 9000 + 1000
    return f"INC-2020-{h}"


def generate_full_test_corpus(manifest_path: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    target_manifest_path = manifest_path or TEST_MANIFEST_PATH
    with open(target_manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    raw_nodes = {n["id"]: n for n in raw_data["nodes"]}

    reports: List[PoliceIncidentReport] = []
    cdrs: List[CallDetailRecord] = []
    provenances: List[EvidenceProvenanceEnvelope] = []

    # Map to ensure identical opaque IDs are never reused inappropriately
    seen_doc_ids = set()

    for idx, case in enumerate(manifest_data["cases"]):
        c_id = case["case_id"]
        u, v = case["target_pair"]
        label = case["label"]
        cond = case["condition"]
        shared_cids = case.get("shared_crime_ids", [])
        shared_months = case.get("temporal_overlap", ["2020-03"])
        primary_month = shared_months[0] if shared_months else "2020-03"

        # Coordinates
        node_u_meta = raw_nodes.get(u, {})
        u_crimes = node_u_meta.get("crime_details", {})
        first_cid = shared_cids[0] if shared_cids else list(u_crimes.keys())[0] if u_crimes else "CID#9999"
        cid_details = u_crimes.get(first_cid, {})
        base_x = cid_details.get("X", 0.5)
        base_y = cid_details.get("Y", 0.5)
        sector = get_sector_name(base_x, base_y)

        crime_date = cid_details.get("date", f"{primary_month}-15 02:30:00")
        date_part = crime_date[:10]
        time_part = crime_date[11:] if len(crime_date) > 11 else "02:30:00"

        entry_method = FORCED_ENTRY_METHODS[idx % len(FORCED_ENTRY_METHODS)]
        stolen_items = STOLEN_PROPERTY_SETS[idx % len(STOLEN_PROPERTY_SETS)]
        moniker_a = ALIAS_MONIKERS[(idx * 2) % len(ALIAS_MONIKERS)]
        moniker_b = ALIAS_MONIKERS[(idx * 2 + 1) % len(ALIAS_MONIKERS)]

        inc_ref_primary = build_synthetic_incident_id(f"{c_id}_primary")
        inc_ref_alt = build_synthetic_incident_id(f"{c_id}_alt")
        inc_ref_dist1 = build_synthetic_incident_id(f"{c_id}_dist1")
        inc_ref_dist2 = build_synthetic_incident_id(f"{c_id}_dist2")

        # =====================================================================
        # 1. POSITIVE CASES (label == 1)
        # =====================================================================
        if label == 1:
            if cond == "clean_evidence":
                # Primary joint report
                id_ir = make_opaque_id("DOC_IR", f"{c_id}_clean_primary")
                r_prim = PoliceIncidentReport(
                    report_id=id_ir,
                    incident_id=inc_ref_primary,
                    incident_date=f"{date_part} {time_part}",
                    location_sector=sector,
                    normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                    forced_entry_method=entry_method,
                    stolen_property=stolen_items,
                    suspects_mentioned=[u, v],
                    narrative=(
                        f"Patrol units responded to an audible burglar alarm at a residential premises in {sector}. "
                        f"Officers observed two individuals exiting through the rear perimeter carrying a dark duffel bag. "
                        f"Suspect 1 (identified as {u}) was detained at the scene; Suspect 2 (identified as {v}) "
                        f"was apprehended attempting to flee on foot. Case cleared by arrest of both co-suspects. "
                        f"Stolen items recovered matched property owner inventory."
                    ),
                    is_distractor=False
                )
                p_prim = EvidenceProvenanceEnvelope(
                    document_id=id_ir, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_CO_OFFENDER_INCIDENT_REPORT_PRIMARY",
                    underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_prim)
                provenances.append(p_prim)

                # Corroborating CDR Call
                id_cdr = make_opaque_id("CDR", f"{c_id}_call")
                c_call = CallDetailRecord(
                    cdr_id=id_cdr, call_timestamp=f"{date_part} 01:15:22",
                    caller_identifier=u, callee_identifier=v,
                    duration_seconds=140, cell_tower_sector=sector, call_type="voice_call"
                )
                p_call = EvidenceProvenanceEnvelope(
                    document_id=id_cdr, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_CDR_CO_OFFENDER_PRE_CRIME",
                    underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                )
                cdrs.append(c_call)
                provenances.append(p_call)

            elif cond == "alias_ambiguity":
                # Primary joint report naming u and alias moniker_a
                id_ir = make_opaque_id("DOC_IR", f"{c_id}_alias_primary")
                r_prim = PoliceIncidentReport(
                    report_id=id_ir,
                    incident_id=inc_ref_primary,
                    incident_date=f"{date_part} {time_part}",
                    location_sector=sector,
                    normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                    forced_entry_method=entry_method,
                    stolen_property=stolen_items,
                    suspects_mentioned=[u, moniker_a],
                    narrative=(
                        f"Patrol units intercepted a residential burglary in progress in {sector}. {u} was apprehended "
                        f"inside the premises. Accomplice operating under street moniker '{moniker_a}' fled prior to capture. "
                        f"Case clearance and detention logged for co-participants."
                    ),
                    is_distractor=False
                )
                p_prim = EvidenceProvenanceEnvelope(
                    document_id=id_ir, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_ALIAS_INCIDENT_REPORT_PRIMARY",
                    underlying_entity_references=[u, moniker_a], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_prim)
                provenances.append(p_prim)

                # Field resolution report resolving moniker_a to v
                id_ir_res = make_opaque_id("DOC_IR", f"{c_id}_alias_resolution")
                r_res = PoliceIncidentReport(
                    report_id=id_ir_res,
                    incident_id=inc_ref_alt,
                    incident_date=f"{date_part} 18:45:00",
                    location_sector=sector,
                    normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                    forced_entry_method="Traffic stop and field interrogation",
                    stolen_property=[],
                    suspects_mentioned=[v],
                    narrative=(
                        f"Field intelligence interview conducted in {sector}. Verified subject {v} was identified "
                        f"operating vehicle. Departmental intelligence confirms subject operates under street moniker '{moniker_a}'."
                    ),
                    is_distractor=False
                )
                p_res = EvidenceProvenanceEnvelope(
                    document_id=id_ir_res, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_ALIAS_RESOLUTION_FIELD_RECORD",
                    underlying_entity_references=[v, moniker_a], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_res)
                provenances.append(p_res)

                # Corroborating CDR
                id_cdr = make_opaque_id("CDR", f"{c_id}_call")
                c_call = CallDetailRecord(
                    cdr_id=id_cdr, call_timestamp=f"{date_part} 01:20:00",
                    caller_identifier=u, callee_identifier=v,
                    duration_seconds=115, cell_tower_sector=sector, call_type="voice_call"
                )
                p_call = EvidenceProvenanceEnvelope(
                    document_id=id_cdr, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_CDR_CO_OFFENDER_PRE_CRIME",
                    underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                )
                cdrs.append(c_call)
                provenances.append(p_call)

            elif cond == "missing_evidence":
                # Primary joint report WITHHELD from retrieval corpus, saved in provenance only!
                id_ir = make_opaque_id("DOC_IR", f"{c_id}_withheld_primary")
                r_withheld = PoliceIncidentReport(
                    report_id=id_ir,
                    incident_id=inc_ref_primary,
                    incident_date=f"{date_part} {time_part}",
                    location_sector=sector,
                    normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                    forced_entry_method=entry_method,
                    stolen_property=stolen_items,
                    suspects_mentioned=[u, v],
                    narrative=(
                        f"OFFICIAL WITHHELD RECORD: Direct co-arrest of {u} and {v} in burglary {inc_ref_primary}. "
                        f"This primary document is intentionally excluded from the public retrieval corpus."
                    ),
                    is_distractor=False
                )
                p_withheld = EvidenceProvenanceEnvelope(
                    document_id=id_ir, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_MISSING_PRIMARY_INCIDENT_REPORT",
                    underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                )
                # DO NOT append r_withheld to reports (withheld from retrieval corpus!)
                provenances.append(p_withheld)

                # 3 Corroborating CDRs (pre-crime call, SMS, post-crime call)
                for c_step, (offset, ctype, dur) in enumerate([("01:10:00", "voice_call", 180), ("01:50:00", "sms", 0), ("04:15:00", "voice_call", 130)]):
                    id_c = make_opaque_id("CDR", f"{c_id}_circ_{c_step}")
                    c_rec = CallDetailRecord(
                        cdr_id=id_c, call_timestamp=f"{date_part} {offset}",
                        caller_identifier=u if c_step % 2 == 0 else v,
                        callee_identifier=v if c_step % 2 == 0 else u,
                        duration_seconds=dur, cell_tower_sector=sector, call_type=ctype
                    )
                    p_rec = EvidenceProvenanceEnvelope(
                        document_id=id_c, is_synthetic=True, generator_version=GENERATOR_VERSION,
                        generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                        source_incident_cid=first_cid, condition=cond,
                        generation_rule=f"RULE_CDR_CIRCUMSTANTIAL_{c_step}",
                        underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                    )
                    cdrs.append(c_rec)
                    provenances.append(p_rec)

            elif cond == "distractors":
                # Primary joint report
                id_ir = make_opaque_id("DOC_IR", f"{c_id}_dist_primary")
                r_prim = PoliceIncidentReport(
                    report_id=id_ir, incident_id=inc_ref_primary, incident_date=f"{date_part} {time_part}",
                    location_sector=sector, normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                    forced_entry_method=entry_method, stolen_property=stolen_items,
                    suspects_mentioned=[u, v],
                    narrative=(
                        f"Patrol response to verified burglary alarm in {sector}. Co-suspects {u} and {v} apprehended "
                        f"leaving building with stolen inventory. Case cleared by arrest."
                    ),
                    is_distractor=False
                )
                p_prim = EvidenceProvenanceEnvelope(
                    document_id=id_ir, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_CO_OFFENDER_INCIDENT_REPORT_PRIMARY",
                    underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_prim)
                provenances.append(p_prim)

                # 2 Distractor reports in same sector
                for d_step in range(2):
                    id_dist = make_opaque_id("DOC_IR", f"{c_id}_distractor_{d_step}")
                    r_dist = PoliceIncidentReport(
                        report_id=id_dist, incident_id=build_synthetic_incident_id(f"{c_id}_dist_{d_step}"),
                        incident_date=f"{date_part} 05:00:00", location_sector=sector,
                        normalized_coordinates=(round(base_x + 0.005, 4), round(base_y - 0.005, 4)),
                        forced_entry_method="False alarm or unknown prowler", stolen_property=[],
                        suspects_mentioned=[],
                        narrative=f"Distractor report: False commercial burglar alarm in {sector}. No suspects observed.",
                        is_distractor=True
                    )
                    p_dist = EvidenceProvenanceEnvelope(
                        document_id=id_dist, is_synthetic=True, generator_version=GENERATOR_VERSION,
                        generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                        source_incident_cid="CID#DISTRACTOR", condition=cond,
                        generation_rule="RULE_DISTRACTOR_INCIDENT_REPORT",
                        underlying_entity_references=[], creation_timestamp=CREATION_TIMESTAMP
                    )
                    reports.append(r_dist)
                    provenances.append(p_dist)

                # CDR
                id_cdr = make_opaque_id("CDR", f"{c_id}_call")
                c_call = CallDetailRecord(
                    cdr_id=id_cdr, call_timestamp=f"{date_part} 01:30:00",
                    caller_identifier=u, callee_identifier=v,
                    duration_seconds=90, cell_tower_sector=sector, call_type="voice_call"
                )
                p_call = EvidenceProvenanceEnvelope(
                    document_id=id_cdr, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_CDR_CO_OFFENDER_PRE_CRIME",
                    underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                )
                cdrs.append(c_call)
                provenances.append(p_call)

            elif cond == "mixed_difficulty":
                # Primary report with moniker_a
                id_ir = make_opaque_id("DOC_IR", f"{c_id}_mixed_primary")
                r_prim = PoliceIncidentReport(
                    report_id=id_ir, incident_id=inc_ref_primary, incident_date=f"{date_part} {time_part}",
                    location_sector=sector, normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                    forced_entry_method=entry_method, stolen_property=stolen_items,
                    suspects_mentioned=[u, moniker_a],
                    narrative=(
                        f"Residential burglary in {sector}. Patrol officers detained {u} on scene. Accomplice "
                        f"operating under moniker '{moniker_a}' fled prior to capture. Solved clearance verified."
                    ),
                    is_distractor=False
                )
                p_prim = EvidenceProvenanceEnvelope(
                    document_id=id_ir, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_ALIAS_INCIDENT_REPORT_PRIMARY",
                    underlying_entity_references=[u, moniker_a], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_prim)
                provenances.append(p_prim)

                # Field resolution report
                id_ir_res = make_opaque_id("DOC_IR", f"{c_id}_mixed_resolution")
                r_res = PoliceIncidentReport(
                    report_id=id_ir_res, incident_id=inc_ref_alt, incident_date=f"{date_part} 21:00:00",
                    location_sector=sector, normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                    forced_entry_method="Traffic stop and identification", stolen_property=[],
                    suspects_mentioned=[v],
                    narrative=f"Intelligence field interview: Verified subject {v} operates under moniker '{moniker_a}'.",
                    is_distractor=False
                )
                p_res = EvidenceProvenanceEnvelope(
                    document_id=id_ir_res, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_ALIAS_RESOLUTION_FIELD_RECORD",
                    underlying_entity_references=[v, moniker_a], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_res)
                provenances.append(p_res)

                # Distractor report
                id_dist = make_opaque_id("DOC_IR", f"{c_id}_mixed_distractor")
                r_dist = PoliceIncidentReport(
                    report_id=id_dist, incident_id=inc_ref_dist1, incident_date=f"{date_part} 06:15:00",
                    location_sector=sector, normalized_coordinates=(round(base_x + 0.008, 4), round(base_y - 0.008, 4)),
                    forced_entry_method="Alarm activation", stolen_property=[], suspects_mentioned=[],
                    narrative=f"Distractor report: Security patrol responded to perimeter motion sensor in {sector}. No entry effected.",
                    is_distractor=True
                )
                p_dist = EvidenceProvenanceEnvelope(
                    document_id=id_dist, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid="CID#DISTRACTOR", condition=cond,
                    generation_rule="RULE_DISTRACTOR_INCIDENT_REPORT",
                    underlying_entity_references=[], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_dist)
                provenances.append(p_dist)

                # CDR
                id_cdr = make_opaque_id("CDR", f"{c_id}_mixed_call")
                c_call = CallDetailRecord(
                    cdr_id=id_cdr, call_timestamp=f"{date_part} 01:10:00",
                    caller_identifier=u, callee_identifier=v,
                    duration_seconds=110, cell_tower_sector=sector, call_type="voice_call"
                )
                p_call = EvidenceProvenanceEnvelope(
                    document_id=id_cdr, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid=first_cid, condition=cond,
                    generation_rule="RULE_CDR_CO_OFFENDER_PRE_CRIME",
                    underlying_entity_references=[u, v], creation_timestamp=CREATION_TIMESTAMP
                )
                cdrs.append(c_call)
                provenances.append(p_call)

        # =====================================================================
        # 2. NEGATIVE CASES (label == 0)
        # =====================================================================
        else:
            # Independent reports and independent CDRs
            id_ir_u = make_opaque_id("DOC_IR", f"{c_id}_indep_u")
            r_u = PoliceIncidentReport(
                report_id=id_ir_u, incident_id=inc_ref_primary, incident_date=f"{date_part} {time_part}",
                location_sector=sector, normalized_coordinates=(round(base_x, 4), round(base_y, 4)),
                forced_entry_method=entry_method, stolen_property=stolen_items,
                suspects_mentioned=[u] if cond != "alias_ambiguity" and cond != "mixed_difficulty" else [u, moniker_a],
                narrative=(
                    f"Burglary investigation in {sector}. Subject {u} identified as sole actor in incident {inc_ref_primary}."
                    if cond != "alias_ambiguity" and cond != "mixed_difficulty" else
                    f"Burglary investigation in {sector}. Subject {u} observed alongside accomplice '{moniker_a}'. (Unlinked to {v})."
                ),
                is_distractor=False
            )
            p_u = EvidenceProvenanceEnvelope(
                document_id=id_ir_u, is_synthetic=True, generator_version=GENERATOR_VERSION,
                generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                source_incident_cid=first_cid, condition=cond,
                generation_rule="RULE_INDEPENDENT_INCIDENT_REPORT_U",
                underlying_entity_references=[u], creation_timestamp=CREATION_TIMESTAMP
            )
            reports.append(r_u)
            provenances.append(p_u)

            # Independent report for v in adjacent sector/time
            id_ir_v = make_opaque_id("DOC_IR", f"{c_id}_indep_v")
            r_v = PoliceIncidentReport(
                report_id=id_ir_v, incident_id=inc_ref_alt, incident_date=f"{date_part} 04:00:00",
                location_sector=sector, normalized_coordinates=(round(base_x + 0.003, 4), round(base_y + 0.003, 4)),
                forced_entry_method=entry_method, stolen_property=stolen_items,
                suspects_mentioned=[v],
                narrative=f"Independent incident in {sector}: Patrol response logged subject {v} operating independently.",
                is_distractor=False
            )
            p_v = EvidenceProvenanceEnvelope(
                document_id=id_ir_v, is_synthetic=True, generator_version=GENERATOR_VERSION,
                generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                source_incident_cid="CID#INDEP_V", condition=cond,
                generation_rule="RULE_INDEPENDENT_INCIDENT_REPORT_V",
                underlying_entity_references=[v], creation_timestamp=CREATION_TIMESTAMP
            )
            reports.append(r_v)
            provenances.append(p_v)

            # Independent CDR (u calling someone else, NOT v!)
            id_cdr = make_opaque_id("CDR", f"{c_id}_indep_call")
            c_call = CallDetailRecord(
                cdr_id=id_cdr, call_timestamp=f"{date_part} 01:45:00",
                caller_identifier=u, callee_identifier="OID#EXTERN",
                duration_seconds=75, cell_tower_sector=sector, call_type="voice_call"
            )
            p_call = EvidenceProvenanceEnvelope(
                document_id=id_cdr, is_synthetic=True, generator_version=GENERATOR_VERSION,
                generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                source_incident_cid=first_cid, condition=cond,
                generation_rule="RULE_CDR_INDEPENDENT_NETWORK",
                underlying_entity_references=[u], creation_timestamp=CREATION_TIMESTAMP
            )
            cdrs.append(c_call)
            provenances.append(p_call)

            # Add distractor report if distractors or mixed_difficulty
            if cond == "distractors":
                for d_step in range(2):
                    id_dist = make_opaque_id("DOC_IR", f"{c_id}_neg_distractor_{d_step}")
                    r_dist = PoliceIncidentReport(
                        report_id=id_dist, incident_id=build_synthetic_incident_id(f"{c_id}_neg_dist_{d_step}"),
                        incident_date=f"{date_part} 06:30:00", location_sector=sector,
                        normalized_coordinates=(round(base_x + 0.009 * (d_step + 1), 4), round(base_y - 0.009 * (d_step + 1), 4)),
                        forced_entry_method="Distractor prowler call" if d_step == 0 else "Distractor alarm dispatch",
                        stolen_property=[], suspects_mentioned=[],
                        narrative=(
                            f"Distractor report: Security patrol checked perimeter in {sector}. No suspects observed."
                            if d_step == 0 else
                            f"Distractor report: Automated alarm reset at commercial storage yard in {sector}. Premises secure; no intrusion."
                        ),
                        is_distractor=True
                    )
                    p_dist = EvidenceProvenanceEnvelope(
                        document_id=id_dist, is_synthetic=True, generator_version=GENERATOR_VERSION,
                        generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                        source_incident_cid="CID#DISTRACTOR", condition=cond,
                        generation_rule="RULE_DISTRACTOR_INCIDENT_REPORT",
                        underlying_entity_references=[], creation_timestamp=CREATION_TIMESTAMP
                    )
                    reports.append(r_dist)
                    provenances.append(p_dist)
            elif cond == "mixed_difficulty":
                id_dist = make_opaque_id("DOC_IR", f"{c_id}_neg_distractor_0")
                r_dist = PoliceIncidentReport(
                    report_id=id_dist, incident_id=build_synthetic_incident_id(f"{c_id}_neg_dist_0"),
                    incident_date=f"{date_part} 06:30:00", location_sector=sector,
                    normalized_coordinates=(round(base_x + 0.009, 4), round(base_y - 0.009, 4)),
                    forced_entry_method="Distractor prowler call", stolen_property=[], suspects_mentioned=[],
                    narrative=f"Distractor report: Security patrol checked perimeter in {sector}. No suspects observed.",
                    is_distractor=True
                )
                p_dist = EvidenceProvenanceEnvelope(
                    document_id=id_dist, is_synthetic=True, generator_version=GENERATOR_VERSION,
                    generation_seed=RANDOM_SEED, ground_truth_case_id=c_id, target_pair=(u, v),
                    source_incident_cid="CID#DISTRACTOR", condition=cond,
                    generation_rule="RULE_DISTRACTOR_INCIDENT_REPORT",
                    underlying_entity_references=[], creation_timestamp=CREATION_TIMESTAMP
                )
                reports.append(r_dist)
                provenances.append(p_dist)

    # Convert to SanitizedRetrievalDocument
    retrieval_docs: List[SanitizedRetrievalDocument] = []
    for r in reports:
        doc = SanitizedRetrievalDocument(
            doc_id=r.report_id,
            doc_type="incident_report",
            timestamp=r.incident_date,
            text_content=r.to_retrieval_text(),
            metadata={"sector": r.location_sector, "forced_entry": r.forced_entry_method}
        )
        retrieval_docs.append(doc)

    for c in cdrs:
        doc = SanitizedRetrievalDocument(
            doc_id=c.cdr_id,
            doc_type="call_detail_record",
            timestamp=c.call_timestamp,
            text_content=c.to_retrieval_text(),
            metadata={"sector": c.cell_tower_sector, "call_type": c.call_type}
        )
        retrieval_docs.append(doc)

    # Validate corpus
    validate_retrieval_corpus(retrieval_docs)

    return retrieval_docs, provenances


def save_test_evidence_corpus(output_corpus_dir: Optional[str] = None, manifest_path: Optional[str] = None):
    retrieval_docs, provenances = generate_full_test_corpus(manifest_path=manifest_path)
    target_corpus_dir = output_corpus_dir or CORPUS_DIR

    # Save test_retrieval_documents.jsonl
    corpus_file = os.path.join(target_corpus_dir, "test_retrieval_documents.jsonl")
    with open(corpus_file, "w", encoding="utf-8") as f:
        for doc in retrieval_docs:
            f.write(doc.model_dump_json() + "\n")
    print(f"Saved: {corpus_file} ({len(retrieval_docs)} documents)")

    # Save test_internal_provenance.jsonl
    provenance_file = os.path.join(target_corpus_dir, "test_internal_provenance.jsonl")
    with open(provenance_file, "w", encoding="utf-8") as f:
        for p in provenances:
            f.write(p.model_dump_json() + "\n")
    print(f"Saved: {provenance_file} ({len(provenances)} records)")

    return retrieval_docs, provenances


# Stable public function alias
build_test_evidence_corpus = save_test_evidence_corpus


if __name__ == "__main__":
    print("=" * 80)
    print("GENERATING SPYDER 200-CASE TEST EVIDENCE CORPUS")
    print("=" * 80)
    save_test_evidence_corpus()
    print("Done.")
