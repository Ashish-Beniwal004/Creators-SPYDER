"""
Phase 2B Deterministic Synthetic Evidence Corpus Generator (Remediated v1.1)
Project: Evidence-Grounded Agentic Criminal Network Investigation
Corpus: phase2_corpus/

Generates a reproducible, leakage-free, retrieval-ready synthetic evidence corpus
for the 10 frozen pilot cases using strictly:
1. PoliceIncidentReport
2. CallDetailRecord

Leakage Remediation (Phase 2B.1):
- All retrieval document IDs are strictly opaque hashes (DOC_IR_<hex8>, CDR_<hex8>)
  with ZERO case membership, case numbers, or condition identifiers.
- All original crime identifiers (CID#xxxx) are strictly replaced in retrieval
  text and metadata with synthetic, non-semantic incident references (INC-2020-xxxx).
- Original crime CIDs and case targets are stored EXCLUSIVELY in internal_provenance.jsonl.
- Primary joint arrest record for PILOT_CASE_05 (withheld CID#2293) is genuinely absent
  and its original CID is not leaked in any form.
"""

import os
import sys
import json
import hashlib
from typing import List, Tuple, Dict, Any

# Ensure access to phase2_ground_truth_vault schemas
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_DIR = os.path.join(REPO_ROOT, "phase2_ground_truth_vault")
if VAULT_DIR not in sys.path:
    sys.path.insert(0, VAULT_DIR)

from schemas import (
    PoliceIncidentReport,
    CallDetailRecord,
    EvidenceProvenanceEnvelope,
    SanitizedRetrievalDocument,
    validate_retrieval_corpus
)

CORPUS_DIR = os.path.dirname(os.path.abspath(__file__))
RANDOM_SEED = 42
GENERATOR_VERSION = "pilot_v1.1"
CREATION_TIMESTAMP = "2026-10-12T11:30:00Z"

# Deterministic mapping: original source crime CIDs -> synthetic non-semantic incident references
SYNTHETIC_INCIDENT_MAP: Dict[str, str] = {
    "CID#6456": "INC-2020-7182",
    "CID#3528": "INC-2020-8341",
    "CID#5170": "INC-2020-4916",
    "CID#13934": "INC-2020-5290",
    "CID#3600": "INC-2020-6173",
    "CID#3600_B": "INC-2020-6174",
    "CID#2293": "INC-2020-3849",
    "CID#4927": "INC-2020-9265",
    "CID#8101": "INC-2020-1402",
    "CID#8102": "INC-2020-1403",
    "CID#8103": "INC-2020-1404",
    "CID#5887": "INC-2020-7619",
    "CID#8104": "INC-2020-1405",
    "CID#1288": "INC-2020-3581",
    "CID#1288_INTEL": "INC-2020-3582",
    "CID#8201": "INC-2020-2911",
    "CID#8202": "INC-2020-2912",
    "CID#1288_C": "INC-2020-3583",
    "CID#3528_B": "INC-2020-8342",
    "CID#8203": "INC-2020-2913",
}


def make_opaque_id(prefix: str, token: str) -> str:
    """
    Generates a deterministic, opaque 8-character hex document identifier.
    Guaranteed free of 'PILOT', 'CASE', case numbers, or entity IDs.
    """
    raw = f"{RANDOM_SEED}_{prefix}_{token}".encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()[:8]
    return f"{prefix}_{h}"


def build_pilot_evidence_corpus() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Constructs the 31 synthetic evidence records across the 10 pilot cases with opaque IDs
    and synthetic incident references.
    Returns:
        (retrieval_documents, internal_provenance_envelopes)
    """
    reports: List[PoliceIncidentReport] = []
    cdrs: List[CallDetailRecord] = []
    provenances: List[EvidenceProvenanceEnvelope] = []

    # =========================================================================
    # CASE 01: Clean Evidence (Positive: OID#4418 & OID#8864 in CID#6456)
    # =========================================================================
    # 1. Primary Incident Report
    id_ir_01 = make_opaque_id("DOC_IR", "case_01_primary")
    r_01_a = PoliceIncidentReport(
        report_id=id_ir_01,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#6456"],
        incident_date="2020-01-17 02:40:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5688, 0.6008),
        forced_entry_method="Pry tool marks on rear ground-floor sliding window",
        stolen_property=["Assorted gold jewelry", "Cash box", "Tablet computer"],
        suspects_mentioned=["OID#4418", "OID#8864"],
        narrative=(
            "Patrol units responded to an audible burglar alarm at a commercial premises. "
            "Officers observed two individuals exiting through the rear alleyway carrying a dark duffel bag. "
            "Suspect 1 (identified as OID#4418) was detained at the alley corner; Suspect 2 (identified as OID#8864) "
            "was apprehended attempting to enter a nearby getaway sedan. Stolen items recovered on scene matched "
            "inventory reported by property owner."
        ),
        is_distractor=False
    )
    p_01_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_01,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_01",
        target_pair=("OID#4418", "OID#8864"),
        source_incident_cid="CID#6456",
        condition="clean_evidence",
        generation_rule="RULE_CO_OFFENDER_INCIDENT_REPORT_PRIMARY",
        underlying_entity_references=["OID#4418", "OID#8864"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_01_a)
    provenances.append(p_01_a)

    # 2. Corroborating CDR Call
    id_cdr_01_1 = make_opaque_id("CDR", "case_01_call")
    cdr_01_01 = CallDetailRecord(
        cdr_id=id_cdr_01_1,
        call_timestamp="2020-01-17 01:15:22",
        caller_identifier="OID#4418",
        callee_identifier="OID#8864",
        duration_seconds=145,
        cell_tower_sector="Sector-Central-East",
        call_type="voice_call"
    )
    p_cdr_01_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_01_1,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_01",
        target_pair=("OID#4418", "OID#8864"),
        source_incident_cid="CID#6456",
        condition="clean_evidence",
        generation_rule="RULE_CDR_CO_OFFENDER_PRE_CRIME",
        underlying_entity_references=["OID#4418", "OID#8864"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_01_01)
    provenances.append(p_cdr_01_01)

    # 3. Corroborating CDR SMS
    id_cdr_01_2 = make_opaque_id("CDR", "case_01_sms")
    cdr_01_02 = CallDetailRecord(
        cdr_id=id_cdr_01_2,
        call_timestamp="2020-01-17 01:48:10",
        caller_identifier="OID#8864",
        callee_identifier="OID#4418",
        duration_seconds=0,
        cell_tower_sector="Sector-Central-East",
        call_type="sms"
    )
    p_cdr_01_02 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_01_2,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_01",
        target_pair=("OID#4418", "OID#8864"),
        source_incident_cid="CID#6456",
        condition="clean_evidence",
        generation_rule="RULE_CDR_CO_OFFENDER_SMS_PRE_CRIME",
        underlying_entity_references=["OID#4418", "OID#8864"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_01_02)
    provenances.append(p_cdr_01_02)

    # =========================================================================
    # CASE 02: Clean Evidence (Negative: OID#4418 & OID#5590)
    # =========================================================================
    # 4. Independent Incident Report for OID#5590
    id_ir_02 = make_opaque_id("DOC_IR", "case_02_primary")
    r_02_a = PoliceIncidentReport(
        report_id=id_ir_02,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#3528"],
        incident_date="2020-06-07 03:10:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5565, 0.5957),
        forced_entry_method="Forced lock on basement storage bulkhead",
        stolen_property=["Power tools", "Bicycle"],
        suspects_mentioned=["OID#5590", "OID#6449"],
        narrative=(
            "Investigation into residential burglary in Sector-Central-East. Physical surveillance and forensic latent "
            "fingerprints recovered from the exterior frame identified OID#5590 and OID#6449 as perpetrators. "
            "Both subjects fled prior to police arrival."
        ),
        is_distractor=False
    )
    p_02_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_02,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_02",
        target_pair=("OID#4418", "OID#5590"),
        source_incident_cid="CID#3528",
        condition="clean_evidence",
        generation_rule="RULE_INDEPENDENT_INCIDENT_REPORT",
        underlying_entity_references=["OID#5590", "OID#6449"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_02_a)
    provenances.append(p_02_a)

    # 5. Independent CDR for OID#5590
    id_cdr_02 = make_opaque_id("CDR", "case_02_call")
    cdr_02_01 = CallDetailRecord(
        cdr_id=id_cdr_02,
        call_timestamp="2020-06-07 02:22:15",
        caller_identifier="OID#5590",
        callee_identifier="OID#6449",
        duration_seconds=95,
        cell_tower_sector="Sector-Central-East",
        call_type="voice_call"
    )
    p_cdr_02_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_02,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_02",
        target_pair=("OID#4418", "OID#5590"),
        source_incident_cid="CID#3528",
        condition="clean_evidence",
        generation_rule="RULE_CDR_INDEPENDENT_NETWORK",
        underlying_entity_references=["OID#5590", "OID#6449"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_02_01)
    provenances.append(p_cdr_02_01)

    # =========================================================================
    # CASE 03: Alias Ambiguity (Positive: OID#6819 & OID#8595)
    # =========================================================================
    # 6. Primary Incident Report with Alias Moniker "The Wire"
    id_ir_03_a = make_opaque_id("DOC_IR", "case_03_primary")
    r_03_a = PoliceIncidentReport(
        report_id=id_ir_03_a,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#5170"],
        incident_date="2020-02-20 03:15:00",
        location_sector="Sector-North-West",
        normalized_coordinates=(0.3243, 0.7725),
        forced_entry_method="Jimmied latch on rear ground-floor sliding patio door",
        stolen_property=["Designer watches", "Foreign currency", "Collector coins"],
        suspects_mentioned=["OID#6819", "The Wire"],
        narrative=(
            "Officers intercepted a residential burglary in progress. OID#6819 was detained inside the master bedroom "
            "possessing burglary tools. A second accomplice, known in field intelligence records by the street moniker "
            "'The Wire', escaped through the garage driving a dark blue sedan."
        ),
        is_distractor=False
    )
    p_03_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_03_a,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_03",
        target_pair=("OID#6819", "OID#8595"),
        source_incident_cid="CID#5170",
        condition="alias_ambiguity",
        generation_rule="RULE_ALIAS_INCIDENT_REPORT_PRIMARY",
        underlying_entity_references=["OID#6819", "The Wire"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_03_a)
    provenances.append(p_03_a)

    # 7. Alias Resolution Field Record (Links "The Wire" to OID#8595 without OID#6819)
    id_ir_03_b = make_opaque_id("DOC_IR", "case_03_field")
    r_03_b = PoliceIncidentReport(
        report_id=id_ir_03_b,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#13934"],
        incident_date="2020-02-08 22:30:00",
        location_sector="Sector-North-West",
        normalized_coordinates=(0.3244, 0.7733),
        forced_entry_method="Traffic field interview and vehicle inspection",
        stolen_property=[],
        suspects_mentioned=["OID#8595"],
        narrative=(
            "Patrol officers conducted a routine field interview of driver OID#8595 operating a dark blue sedan. "
            "Intelligence records verify subject OID#8595 uses the active street moniker 'The Wire'. "
            "Subject was cautioned regarding equipment defect and released."
        ),
        is_distractor=False
    )
    p_03_b = EvidenceProvenanceEnvelope(
        document_id=id_ir_03_b,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_03",
        target_pair=("OID#6819", "OID#8595"),
        source_incident_cid="CID#13934",
        condition="alias_ambiguity",
        generation_rule="RULE_ALIAS_RESOLUTION_FIELD_RECORD",
        underlying_entity_references=["OID#8595", "The Wire"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_03_b)
    provenances.append(p_03_b)

    # 8. CDR Intercept between Alias "The Wire" and OID#6819
    id_cdr_03 = make_opaque_id("CDR", "case_03_call")
    cdr_03_01 = CallDetailRecord(
        cdr_id=id_cdr_03,
        call_timestamp="2020-02-20 02:40:11",
        caller_identifier="The Wire",
        callee_identifier="OID#6819",
        duration_seconds=180,
        cell_tower_sector="Sector-North-West",
        call_type="voice_call"
    )
    p_cdr_03_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_03,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_03",
        target_pair=("OID#6819", "OID#8595"),
        source_incident_cid="CID#5170",
        condition="alias_ambiguity",
        generation_rule="RULE_CDR_ALIAS_COMMUNICATION",
        underlying_entity_references=["The Wire", "OID#6819"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_03_01)
    provenances.append(p_cdr_03_01)

    # =========================================================================
    # CASE 04: Alias Ambiguity (Negative: OID#8595 & OID#8827)
    # =========================================================================
    # 9. Independent Alias Incident Report for OID#8827 (Alias "The Spark")
    id_ir_04 = make_opaque_id("DOC_IR", "case_04_primary")
    r_04_a = PoliceIncidentReport(
        report_id=id_ir_04,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#3600"],
        incident_date="2020-02-25 04:00:00",
        location_sector="Sector-West-Central",
        normalized_coordinates=(0.3213, 0.7049),
        forced_entry_method="Rooftop ventilation shaft hatch cut open",
        stolen_property=["Smartphones", "Diagnostic equipment", "Soldering station"],
        suspects_mentioned=["OID#8827", "The Spark"],
        narrative=(
            "Commercial burglary of an electronics repair workshop. Security footage captured OID#8827 and an accomplice "
            "known by moniker 'The Spark' loading cartons into a silver hatchback. Distinct modus operandi and equipment observed."
        ),
        is_distractor=False
    )
    p_04_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_04,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_04",
        target_pair=("OID#8595", "OID#8827"),
        source_incident_cid="CID#3600",
        condition="alias_ambiguity",
        generation_rule="RULE_INDEPENDENT_ALIAS_INCIDENT_REPORT",
        underlying_entity_references=["OID#8827", "The Spark"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_04_a)
    provenances.append(p_04_a)

    # 10. CDR between OID#8827 and "The Spark"
    id_cdr_04 = make_opaque_id("CDR", "case_04_call")
    cdr_04_01 = CallDetailRecord(
        cdr_id=id_cdr_04,
        call_timestamp="2020-02-25 03:10:00",
        caller_identifier="OID#8827",
        callee_identifier="The Spark",
        duration_seconds=112,
        cell_tower_sector="Sector-West-Central",
        call_type="voice_call"
    )
    p_cdr_04_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_04,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_04",
        target_pair=("OID#8595", "OID#8827"),
        source_incident_cid="CID#3600",
        condition="alias_ambiguity",
        generation_rule="RULE_CDR_INDEPENDENT_ALIAS",
        underlying_entity_references=["OID#8827", "The Spark"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_04_01)
    provenances.append(p_cdr_04_01)

    # =========================================================================
    # CASE 05: Missing Evidence (Positive: OID#4866 & OID#6315)
    # (Primary joint arrest narrative withheld! Grounded in circumstantial CDRs)
    # =========================================================================
    # 11. Partial Incident Report (Perpetrators Unidentified on Scene; synthetic incident ID)
    id_ir_05 = make_opaque_id("DOC_IR", "case_05_partial")
    r_05_a = PoliceIncidentReport(
        report_id=id_ir_05,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#2293"],
        incident_date="2020-02-25 05:15:00",
        location_sector="Sector-South-Central",
        normalized_coordinates=(0.3939, 0.5914),
        forced_entry_method="Heavy crowbar prying open detached garage service door",
        stolen_property=["High-end power inverter", "Copper spools", "Welding torch"],
        suspects_mentioned=["Unidentified Suspects"],
        narrative=(
            "Commercial burglary reported at electrical contractor storage yard. Responding officers found service door compromised. "
            "Perpetrators departed the premises prior to security patrol arrival. No suspects identified on scene; "
            "forensic shoe impressions documented."
        ),
        is_distractor=False
    )
    p_05_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_05,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_05",
        target_pair=("OID#4866", "OID#6315"),
        source_incident_cid="CID#2293",
        condition="missing_evidence",
        generation_rule="RULE_MISSING_PRIMARY_INCIDENT_REPORT",
        underlying_entity_references=["Unidentified Suspects"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_05_a)
    provenances.append(p_05_a)

    # 12. Pre-Incident CDR Call linking OID#4866 and OID#6315
    id_cdr_05_1 = make_opaque_id("CDR", "case_05_call1")
    cdr_05_01 = CallDetailRecord(
        cdr_id=id_cdr_05_1,
        call_timestamp="2020-02-25 02:15:40",
        caller_identifier="OID#4866",
        callee_identifier="OID#6315",
        duration_seconds=210,
        cell_tower_sector="Sector-South-Central",
        call_type="voice_call"
    )
    p_cdr_05_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_05_1,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_05",
        target_pair=("OID#4866", "OID#6315"),
        source_incident_cid="CID#2293",
        condition="missing_evidence",
        generation_rule="RULE_CDR_CIRCUMSTANTIAL_PRE_CRIME",
        underlying_entity_references=["OID#4866", "OID#6315"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_05_01)
    provenances.append(p_cdr_05_01)

    # 13. Pre-Incident CDR SMS linking OID#6315 and OID#4866
    id_cdr_05_2 = make_opaque_id("CDR", "case_05_sms")
    cdr_05_02 = CallDetailRecord(
        cdr_id=id_cdr_05_2,
        call_timestamp="2020-02-25 02:55:12",
        caller_identifier="OID#6315",
        callee_identifier="OID#4866",
        duration_seconds=0,
        cell_tower_sector="Sector-South-Central",
        call_type="sms"
    )
    p_cdr_05_02 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_05_2,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_05",
        target_pair=("OID#4866", "OID#6315"),
        source_incident_cid="CID#2293",
        condition="missing_evidence",
        generation_rule="RULE_CDR_CIRCUMSTANTIAL_SMS",
        underlying_entity_references=["OID#4866", "OID#6315"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_05_02)
    provenances.append(p_cdr_05_02)

    # 14. Post-Incident CDR Call linking OID#4866 and OID#6315
    id_cdr_05_3 = make_opaque_id("CDR", "case_05_call2")
    cdr_05_03 = CallDetailRecord(
        cdr_id=id_cdr_05_3,
        call_timestamp="2020-02-25 04:10:05",
        caller_identifier="OID#4866",
        callee_identifier="OID#6315",
        duration_seconds=165,
        cell_tower_sector="Sector-South-Central",
        call_type="voice_call"
    )
    p_cdr_05_03 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_05_3,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_05",
        target_pair=("OID#4866", "OID#6315"),
        source_incident_cid="CID#2293",
        condition="missing_evidence",
        generation_rule="RULE_CDR_CIRCUMSTANTIAL_POST_CRIME",
        underlying_entity_references=["OID#4866", "OID#6315"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_05_03)
    provenances.append(p_cdr_05_03)

    # =========================================================================
    # CASE 06: Missing Evidence (Negative: OID#4866 & OID#5631)
    # =========================================================================
    # 15. Partial Incident Report for OID#5631 (Solo scouting incident)
    id_ir_06 = make_opaque_id("DOC_IR", "case_06_solo")
    r_06_a = PoliceIncidentReport(
        report_id=id_ir_06,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#3600_B"],
        incident_date="2020-02-25 01:45:00",
        location_sector="Sector-West-Central",
        normalized_coordinates=(0.3213, 0.7049),
        forced_entry_method="Perimeter chain-link fence cut",
        stolen_property=[],
        suspects_mentioned=["OID#5631"],
        narrative=(
            "Alarm response at commercial compound. Solo suspect OID#5631 observed scouting warehouse perimeter "
            "before retreating upon sighting patrol spotlight. No entry achieved."
        ),
        is_distractor=False
    )
    p_06_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_06,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_06",
        target_pair=("OID#4866", "OID#5631"),
        source_incident_cid="CID#3600",
        condition="missing_evidence",
        generation_rule="RULE_MISSING_PRIMARY_SOLO_REPORT",
        underlying_entity_references=["OID#5631"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_06_a)
    provenances.append(p_06_a)

    # =========================================================================
    # CASE 07: Distractors (Positive: OID#6612 & OID#7994)
    # =========================================================================
    # 16. Primary Incident Report
    id_ir_07 = make_opaque_id("DOC_IR", "case_07_primary")
    r_07_a = PoliceIncidentReport(
        report_id=id_ir_07,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#4927"],
        incident_date="2020-05-17 02:50:00",
        location_sector="Sector-South-West",
        normalized_coordinates=(0.2387, 0.6729),
        forced_entry_method="Rear basement window grate pried open",
        stolen_property=["Laptops", "Camera lenses", "Audio interface"],
        suspects_mentioned=["OID#6612", "OID#7994"],
        narrative=(
            "Patrol officers responded to an audible burglar alarm at a residential property. "
            "Officers detained OID#6612 and OID#7994 attempting to scale the rear perimeter fence carrying "
            "backpacks containing stolen recording equipment."
        ),
        is_distractor=False
    )
    p_07_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_07,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_07",
        target_pair=("OID#6612", "OID#7994"),
        source_incident_cid="CID#4927",
        condition="distractors",
        generation_rule="RULE_CO_OFFENDER_INCIDENT_REPORT_PRIMARY",
        underlying_entity_references=["OID#6612", "OID#7994"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_07_a)
    provenances.append(p_07_a)

    # 17. Corroborating CDR Call
    id_cdr_07 = make_opaque_id("CDR", "case_07_call")
    cdr_07_01 = CallDetailRecord(
        cdr_id=id_cdr_07,
        call_timestamp="2020-05-17 01:30:25",
        caller_identifier="OID#6612",
        callee_identifier="OID#7994",
        duration_seconds=130,
        cell_tower_sector="Sector-South-West",
        call_type="voice_call"
    )
    p_cdr_07_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_07,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_07",
        target_pair=("OID#6612", "OID#7994"),
        source_incident_cid="CID#4927",
        condition="distractors",
        generation_rule="RULE_CDR_CO_OFFENDER_PRE_CRIME",
        underlying_entity_references=["OID#6612", "OID#7994"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_07_01)
    provenances.append(p_cdr_07_01)

    # 18. Distractor 1: Nearby incident in Sector-South-West
    id_ir_07_dis1 = make_opaque_id("DOC_IR", "case_07_dis1")
    r_07_dis1 = PoliceIncidentReport(
        report_id=id_ir_07_dis1,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#8101"],
        incident_date="2020-05-14 23:15:00",
        location_sector="Sector-South-West",
        normalized_coordinates=(0.2350, 0.6710),
        forced_entry_method="Padlock cut with bolt cutters on municipal maintenance shed",
        stolen_property=["Gasoline cans", "Lawn trimmer"],
        suspects_mentioned=["OID#9901"],
        narrative=(
            "Municipal parks department reported break-in at storage shed. Footprints indicate a single perpetrator "
            "OID#9901 fled across public sports field."
        ),
        is_distractor=True
    )
    p_07_dis1 = EvidenceProvenanceEnvelope(
        document_id=id_ir_07_dis1,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_07",
        target_pair=("OID#6612", "OID#7994"),
        source_incident_cid="CID#8101",
        condition="distractors",
        generation_rule="RULE_DISTRACTOR_LOCAL_INCIDENT",
        underlying_entity_references=["OID#9901"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_07_dis1)
    provenances.append(p_07_dis1)

    # 19. Distractor 2: False alarm in Sector-South-West
    id_ir_07_dis2 = make_opaque_id("DOC_IR", "case_07_dis2")
    r_07_dis2 = PoliceIncidentReport(
        report_id=id_ir_07_dis2,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#8102"],
        incident_date="2020-05-18 04:10:00",
        location_sector="Sector-South-West",
        normalized_coordinates=(0.2410, 0.6750),
        forced_entry_method="Attempted force on commercial glass door",
        stolen_property=[],
        suspects_mentioned=[],
        narrative=(
            "Commercial alarm dispatch. Officers checked exterior of auto body garage. Glass door showed scratches "
            "but remained intact. Stray dog observed nearby; false alarm logged."
        ),
        is_distractor=True
    )
    p_07_dis2 = EvidenceProvenanceEnvelope(
        document_id=id_ir_07_dis2,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_07",
        target_pair=("OID#6612", "OID#7994"),
        source_incident_cid="CID#8102",
        condition="distractors",
        generation_rule="RULE_DISTRACTOR_FALSE_ALARM",
        underlying_entity_references=[],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_07_dis2)
    provenances.append(p_07_dis2)

    # 20. Distractor 3: Vehicle prowl in Sector-South-West
    id_ir_07_dis3 = make_opaque_id("DOC_IR", "case_07_dis3")
    r_07_dis3 = PoliceIncidentReport(
        report_id=id_ir_07_dis3,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#8103"],
        incident_date="2020-05-20 01:45:00",
        location_sector="Sector-South-West",
        normalized_coordinates=(0.2395, 0.6735),
        forced_entry_method="Unlocked vehicle entered in driveway",
        stolen_property=["Sunglasses", "Small change"],
        suspects_mentioned=["OID#9902"],
        narrative=(
            "Resident reported theft from vehicle parked in private driveway. Neighborhood security camera recorded "
            "unknown prowler OID#9902 trying car door handles."
        ),
        is_distractor=True
    )
    p_07_dis3 = EvidenceProvenanceEnvelope(
        document_id=id_ir_07_dis3,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_07",
        target_pair=("OID#6612", "OID#7994"),
        source_incident_cid="CID#8103",
        condition="distractors",
        generation_rule="RULE_DISTRACTOR_VEHICLE_PROWL",
        underlying_entity_references=["OID#9902"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_07_dis3)
    provenances.append(p_07_dis3)

    # =========================================================================
    # CASE 08: Distractors (Negative: OID#7661 & OID#7994)
    # =========================================================================
    # 21. Independent Incident Report for OID#7661 (with OID#7703)
    id_ir_08 = make_opaque_id("DOC_IR", "case_08_primary")
    r_08_a = PoliceIncidentReport(
        report_id=id_ir_08,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#5887"],
        incident_date="2020-06-13 03:20:00",
        location_sector="Sector-South-West",
        normalized_coordinates=(0.2214, 0.6602),
        forced_entry_method="Roll-up bay door latch compromised",
        stolen_property=["Industrial power tools", "Copper pipe fittings"],
        suspects_mentioned=["OID#7661", "OID#7703"],
        narrative=(
            "Commercial burglary at plumbing supply warehouse. CCTV surveillance recorded OID#7661 and OID#7703 "
            "loading inventory into a white van before departing heading west."
        ),
        is_distractor=False
    )
    p_08_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_08,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_08",
        target_pair=("OID#7661", "OID#7994"),
        source_incident_cid="CID#5887",
        condition="distractors",
        generation_rule="RULE_INDEPENDENT_INCIDENT_REPORT",
        underlying_entity_references=["OID#7661", "OID#7703"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_08_a)
    provenances.append(p_08_a)

    # 22. Independent CDR for OID#7661
    id_cdr_08 = make_opaque_id("CDR", "case_08_call")
    cdr_08_01 = CallDetailRecord(
        cdr_id=id_cdr_08,
        call_timestamp="2020-06-13 02:05:00",
        caller_identifier="OID#7661",
        callee_identifier="OID#7703",
        duration_seconds=88,
        cell_tower_sector="Sector-South-West",
        call_type="voice_call"
    )
    p_cdr_08_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_08,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_08",
        target_pair=("OID#7661", "OID#7994"),
        source_incident_cid="CID#5887",
        condition="distractors",
        generation_rule="RULE_CDR_INDEPENDENT_NETWORK",
        underlying_entity_references=["OID#7661", "OID#7703"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_08_01)
    provenances.append(p_cdr_08_01)

    # 23. Distractor Report in Sector-South-West
    id_ir_08_dis = make_opaque_id("DOC_IR", "case_08_dis")
    r_08_dis1 = PoliceIncidentReport(
        report_id=id_ir_08_dis,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#8104"],
        incident_date="2020-06-10 02:00:00",
        location_sector="Sector-South-West",
        normalized_coordinates=(0.2250, 0.6650),
        forced_entry_method="Side window smashed with brick",
        stolen_property=["Toolbox", "Car battery"],
        suspects_mentioned=[],
        narrative=(
            "Burglary of detached residential workshop. Homeowner discovered broken window in the morning. "
            "Forensic sweep found no latent prints; perpetrators unidentified."
        ),
        is_distractor=True
    )
    p_08_dis1 = EvidenceProvenanceEnvelope(
        document_id=id_ir_08_dis,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_08",
        target_pair=("OID#7661", "OID#7994"),
        source_incident_cid="CID#8104",
        condition="distractors",
        generation_rule="RULE_DISTRACTOR_LOCAL_INCIDENT",
        underlying_entity_references=[],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_08_dis1)
    provenances.append(p_08_dis1)

    # =========================================================================
    # CASE 09: Mixed Difficulty (Positive: OID#1964 & OID#2568)
    # (Combines: Alias "The Locksmith", withheld primary arrest file, & distractors)
    # =========================================================================
    # 24. Incident Report mentioning OID#1964 and alias "The Locksmith"
    id_ir_09_a = make_opaque_id("DOC_IR", "case_09_primary")
    r_09_a = PoliceIncidentReport(
        report_id=id_ir_09_a,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#1288"],
        incident_date="2020-06-19 04:00:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5394, 0.5983),
        forced_entry_method="Deadbolt lock cylinders picked cleanly without exterior damage",
        stolen_property=["High-grade diamonds", "Gold bullion coins"],
        suspects_mentioned=["OID#1964", "The Locksmith"],
        narrative=(
            "Commercial burglary at jewelry boutique in Sector-Central-East. Interior motion alarms triggered. "
            "CCTV footage showed two hooded perpetrators: OID#1964 carrying safe contents, while an accomplice "
            "operating with sophisticated bypass tools and known by the moniker 'The Locksmith' manipulated the vault timer."
        ),
        is_distractor=False
    )
    p_09_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_09_a,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_09",
        target_pair=("OID#1964", "OID#2568"),
        source_incident_cid="CID#1288",
        condition="mixed_difficulty",
        generation_rule="RULE_MIXED_INCIDENT_REPORT_ALIAS_PRIMARY",
        underlying_entity_references=["OID#1964", "The Locksmith"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_09_a)
    provenances.append(p_09_a)

    # 25. Field Intelligence linking OID#2568 to "The Locksmith"
    id_ir_09_b = make_opaque_id("DOC_IR", "case_09_field")
    r_09_b = PoliceIncidentReport(
        report_id=id_ir_09_b,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#1288_INTEL"],
        incident_date="2020-06-02 21:00:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5390, 0.5980),
        forced_entry_method="Field stop and intelligence interview",
        stolen_property=[],
        suspects_mentioned=["OID#2568"],
        narrative=(
            "Tactical patrol conducted a pedestrian stop of OID#2568. Subject was in possession of automotive pick sets "
            "and tension wrenches. Criminal intelligence database lists OID#2568 under the established moniker 'The Locksmith'."
        ),
        is_distractor=False
    )
    p_09_b = EvidenceProvenanceEnvelope(
        document_id=id_ir_09_b,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_09",
        target_pair=("OID#1964", "OID#2568"),
        source_incident_cid="CID#1288",
        condition="mixed_difficulty",
        generation_rule="RULE_MIXED_ALIAS_RESOLUTION",
        underlying_entity_references=["OID#2568", "The Locksmith"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_09_b)
    provenances.append(p_09_b)

    # 26. CDR between OID#1964 and OID#2568
    id_cdr_09 = make_opaque_id("CDR", "case_09_call")
    cdr_09_01 = CallDetailRecord(
        cdr_id=id_cdr_09,
        call_timestamp="2020-06-19 01:45:10",
        caller_identifier="OID#1964",
        callee_identifier="OID#2568",
        duration_seconds=215,
        cell_tower_sector="Sector-Central-East",
        call_type="voice_call"
    )
    p_cdr_09_01 = EvidenceProvenanceEnvelope(
        document_id=id_cdr_09,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_09",
        target_pair=("OID#1964", "OID#2568"),
        source_incident_cid="CID#1288",
        condition="mixed_difficulty",
        generation_rule="RULE_CDR_MIXED_CO_OFFENDER",
        underlying_entity_references=["OID#1964", "OID#2568"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    cdrs.append(cdr_09_01)
    provenances.append(p_cdr_09_01)

    # 27. Distractor Report 1 in Sector-Central-East
    id_ir_09_dis1 = make_opaque_id("DOC_IR", "case_09_dis1")
    r_09_dis1 = PoliceIncidentReport(
        report_id=id_ir_09_dis1,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#8201"],
        incident_date="2020-06-18 23:45:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5420, 0.5960),
        forced_entry_method="Display window shattered with paving stone",
        stolen_property=["Costume jewelry", "Cash register drawer"],
        suspects_mentioned=[],
        narrative=(
            "Smash-and-grab burglary at retail fashion shop. Quick response by patrol found shattered front window. "
            "Perpetrators fled on foot before arrival; cash drawer abandoned on curb."
        ),
        is_distractor=True
    )
    p_09_dis1 = EvidenceProvenanceEnvelope(
        document_id=id_ir_09_dis1,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_09",
        target_pair=("OID#1964", "OID#2568"),
        source_incident_cid="CID#8201",
        condition="mixed_difficulty",
        generation_rule="RULE_DISTRACTOR_LOCAL_INCIDENT",
        underlying_entity_references=[],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_09_dis1)
    provenances.append(p_09_dis1)

    # 28. Distractor Report 2 in Sector-Central-East
    id_ir_09_dis2 = make_opaque_id("DOC_IR", "case_09_dis2")
    r_09_dis2 = PoliceIncidentReport(
        report_id=id_ir_09_dis2,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#8202"],
        incident_date="2020-06-21 03:15:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5380, 0.6010),
        forced_entry_method="Rear fire exit forced with pry bar",
        stolen_property=["Kitchen knives", "Commercial coffee maker"],
        suspects_mentioned=["OID#9903"],
        narrative=(
            "Restaurant burglary in Sector-Central-East. Solo suspect OID#9903 apprehended in back alleyway with stolen kitchen inventory."
        ),
        is_distractor=True
    )
    p_09_dis2 = EvidenceProvenanceEnvelope(
        document_id=id_ir_09_dis2,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_09",
        target_pair=("OID#1964", "OID#2568"),
        source_incident_cid="CID#8202",
        condition="mixed_difficulty",
        generation_rule="RULE_DISTRACTOR_LOCAL_INCIDENT",
        underlying_entity_references=["OID#9903"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_09_dis2)
    provenances.append(p_09_dis2)

    # =========================================================================
    # CASE 10: Mixed Difficulty (Negative: OID#4381 & OID#6449)
    # (Unlinked aliases, omitted primary files, distractors)
    # =========================================================================
    # 29. Incident Report for OID#4381 (Alias "The Driver")
    id_ir_10_a = make_opaque_id("DOC_IR", "case_10_primary")
    r_10_a = PoliceIncidentReport(
        report_id=id_ir_10_a,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#1288_C"],
        incident_date="2020-06-15 02:45:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5394, 0.5983),
        forced_entry_method="Attempted jemmying of office back door",
        stolen_property=[],
        suspects_mentioned=["OID#4381", "The Driver"],
        narrative=(
            "Security guard interrupted an attempted burglary at logistics office. "
            "Suspect OID#4381 and an unidentified wheelman 'The Driver' fled in a grey minivan."
        ),
        is_distractor=False
    )
    p_10_a = EvidenceProvenanceEnvelope(
        document_id=id_ir_10_a,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_10",
        target_pair=("OID#4381", "OID#6449"),
        source_incident_cid="CID#1288",
        condition="mixed_difficulty",
        generation_rule="RULE_MIXED_INDEPENDENT_ALIAS_REPORT",
        underlying_entity_references=["OID#4381", "The Driver"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_10_a)
    provenances.append(p_10_a)

    # 30. Incident Report for OID#6449 (Solo print recovery)
    id_ir_10_b = make_opaque_id("DOC_IR", "case_10_solo")
    r_10_b = PoliceIncidentReport(
        report_id=id_ir_10_b,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#3528_B"],
        incident_date="2020-06-25 03:30:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5565, 0.5957),
        forced_entry_method="Ground floor louvered window pushed in",
        stolen_property=["Handheld power drill", "Tool belt"],
        suspects_mentioned=["OID#6449"],
        narrative=(
            "Residential burglary investigation in Sector-Central-East. Latent palm print identified OID#6449 on the window frame."
        ),
        is_distractor=False
    )
    p_10_b = EvidenceProvenanceEnvelope(
        document_id=id_ir_10_b,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_10",
        target_pair=("OID#4381", "OID#6449"),
        source_incident_cid="CID#3528",
        condition="mixed_difficulty",
        generation_rule="RULE_MIXED_INDEPENDENT_SOLO_REPORT",
        underlying_entity_references=["OID#6449"],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_10_b)
    provenances.append(p_10_b)

    # 31. Distractor Report in Sector-Central-East
    id_ir_10_dis = make_opaque_id("DOC_IR", "case_10_dis")
    r_10_dis1 = PoliceIncidentReport(
        report_id=id_ir_10_dis,
        incident_id=SYNTHETIC_INCIDENT_MAP["CID#8203"],
        incident_date="2020-06-14 01:10:00",
        location_sector="Sector-Central-East",
        normalized_coordinates=(0.5450, 0.5970),
        forced_entry_method="Cut padlock on construction site container",
        stolen_property=["Extension cords", "Scaffolding clamps"],
        suspects_mentioned=[],
        narrative=(
            "Theft from construction site container in Sector-Central-East. No suspect description available."
        ),
        is_distractor=True
    )
    p_10_dis1 = EvidenceProvenanceEnvelope(
        document_id=id_ir_10_dis,
        is_synthetic=True,
        generator_version=GENERATOR_VERSION,
        generation_seed=RANDOM_SEED,
        ground_truth_case_id="PILOT_CASE_10",
        target_pair=("OID#4381", "OID#6449"),
        source_incident_cid="CID#8203",
        condition="mixed_difficulty",
        generation_rule="RULE_DISTRACTOR_LOCAL_INCIDENT",
        underlying_entity_references=[],
        creation_timestamp=CREATION_TIMESTAMP
    )
    reports.append(r_10_dis1)
    provenances.append(p_10_dis1)

    # Convert all reports and CDRs to SanitizedRetrievalDocument
    retrieval_docs: List[SanitizedRetrievalDocument] = []

    for r in reports:
        doc = SanitizedRetrievalDocument(
            doc_id=r.report_id,
            doc_type="incident_report",
            timestamp=r.incident_date,
            text_content=r.to_retrieval_text(),
            metadata={
                "incident_id": r.incident_id,
                "sector": r.location_sector,
                "date": r.incident_date[:10]
            }
        )
        retrieval_docs.append(doc)

    for c in cdrs:
        doc = SanitizedRetrievalDocument(
            doc_id=c.cdr_id,
            doc_type="call_detail_record",
            timestamp=c.call_timestamp,
            text_content=c.to_retrieval_text(),
            metadata={
                "sector": c.cell_tower_sector,
                "date": c.call_timestamp[:10]
            }
        )
        retrieval_docs.append(doc)

    # Sort retrieval docs chronologically for deterministic order
    retrieval_docs.sort(key=lambda d: (d.timestamp, d.doc_id))

    # Validate full corpus at corpus level (duplicate IDs, non-empty)
    validate_retrieval_corpus(retrieval_docs)

    # Match provenances mapping
    prov_map = {p.document_id: p for p in provenances}
    sorted_provenances = [prov_map[d.doc_id] for d in retrieval_docs]

    retrieval_dicts = [d.model_dump(mode="json") for d in retrieval_docs]
    provenance_dicts = [p.model_dump(mode="json") for p in sorted_provenances]

    return retrieval_dicts, provenance_dicts


def main():
    print("=" * 80)
    print("PHASE 2B.1: DETERMINISTIC PILOT EVIDENCE GENERATION (REMEDIATED)")
    print(f"Seed: {RANDOM_SEED} | Generator Version: {GENERATOR_VERSION}")
    print("=" * 80)

    os.makedirs(CORPUS_DIR, exist_ok=True)

    retrieval_docs, provenances = build_pilot_evidence_corpus()

    retrieval_path = os.path.join(CORPUS_DIR, "retrieval_documents.jsonl")
    with open(retrieval_path, "w", encoding="utf-8") as f:
        for doc in retrieval_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"[OK] Wrote {len(retrieval_docs)} retrieval documents: {retrieval_path}")

    prov_path = os.path.join(CORPUS_DIR, "internal_provenance.jsonl")
    with open(prov_path, "w", encoding="utf-8") as f:
        for p in provenances:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[OK] Wrote {len(provenances)} internal provenance records: {prov_path}")

    # Breakdown stats
    ir_count = sum(1 for d in retrieval_docs if d["doc_type"] == "incident_report")
    cdr_count = sum(1 for d in retrieval_docs if d["doc_type"] == "call_detail_record")
    print(f"     Evidence Breakdown: {ir_count} PoliceIncidentReports, {cdr_count} CallDetailRecords")

    cases_covered = {p["ground_truth_case_id"] for p in provenances if p["ground_truth_case_id"]}
    print(f"     Pilot Cases Exercised: {len(cases_covered)} / 10 cases")
    print("=" * 80)


if __name__ == "__main__":
    main()
