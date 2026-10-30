"""
Phase 2D, 2D.1 & 2D.2 Evidence-Grounded Hypothesis Verification Service
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_verification/verifier.py

Target Claim Evaluated:
"Entity A and Entity B share at least one documented solved burglary case
within the selected evaluation window (benchmark target co-offending relationship)."

Decision Logic & Grounding Rules:
- Direct communication (CDRs) establishes telecommunication, NOT shared burglary co-offending.
  A CDR alone returns 'Insufficient Evidence'.
- Alias resolution records establish an alias-to-entity mapping, NOT shared burglary participation.
  An alias resolution record alone returns 'Insufficient Evidence'.
- Solved-case validation: 'Supported' strictly requires evidence of a shared *solved* burglary case
  (documented apprehension, detention, arrest, or forensic/surveillance positive identification).
  If a burglary report is unsolved or of unverified/unknown status, it returns 'Insufficient Evidence'.
- Pair-level 'Unsupported' vs Incident-level Contradiction:
  - An incident-specific exclusion or contradictory alias attribution refutes co-offending for that
    particular incident, but does NOT prove that the pair shares no other solved burglary case across
    the evaluation window. It is recorded as an incident-level finding while the pair-level verdict
    returns 'Insufficient Evidence'.
  - A global contradiction (e.g. continuous custodial detention / incarceration spanning the evaluation window)
    logically precluding any offenses during the window establishes pair-level 'Unsupported'.
- Absence of evidence is NEVER treated as proof of non-association ('Insufficient Evidence').
"""

import os
import sys
import re
from typing import List, Dict, Set, Tuple, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from phase2_ground_truth_vault.schemas import SanitizedRetrievalDocument
from phase2_retrieval.retriever import load_and_validate_corpus, DEFAULT_CORPUS_PATH
from phase2_verification.schemas import (
    VerificationResult,
    VerificationFinding,
    VerificationStatus,
    EvidenceClassification,
)

ENTITY_REGEX = re.compile(r"^OID#\d+$")
DOC_ID_REGEX = re.compile(r"^(DOC_IR|CDR)_[0-9a-f]{8}$")

EVALUATION_WINDOW_START = "2020-01-01"
EVALUATION_WINDOW_END = "2020-06-30"

GLOBAL_EXCLUSION_PATTERNS = [
    r"continuous(?:ly)?\s+(?:incarcerated|detained|in\s+custody|custodial\s+detention)\s+(?:throughout|spanning|covering|for)\s+(?:the\s+)?(?:entire\s+)?(?:evaluation\s+)?(?:window|period|duration)",
    r"in\s+custody\s+throughout\s+(?:the\s+)?(?:entire\s+)?(?:evaluation\s+)?(?:window|period|duration)",
    r"incarcerated\s+(?:for\s+)?(?:the\s+)?entire\s+(?:evaluation\s+)?(?:window|period|duration)",
    r"custodial\s+(?:detention|confinement)\s+(?:spanning|covering|throughout)\s+(?:the\s+)?(?:entire\s+)?(?:evaluation\s+)?(?:window|period|duration)",
    r"(?:incarcerated|custodial\s+(?:detention|confinement))\s+(?:from\s+2020-01-01\s+(?:through|to)\s+2020-06-30|covering\s+2020-01-01\s+to\s+2020-06-30)",
    r"precluding\s+(?:any\s+)?(?:community\s+)?offenses\s+(?:during|throughout)\s+(?:the\s+)?(?:entire\s+)?(?:evaluation\s+)?(?:window|period|duration)",
    r"verified\s+outside\s+(?:the\s+)?jurisdiction\s+(?:throughout|during)\s+(?:the\s+)?(?:entire\s+)?(?:evaluation\s+)?(?:window|period)",
    r"verified\s+non-association\s+throughout\s+(?:the\s+)?(?:entire\s+)?(?:evaluation\s+)?(?:window|period)",
]

INCIDENT_EXCLUSION_PATTERNS = [
    r"cleared of (?:all )?involvement",
    r"excluded as (?:a )?suspect",
    r"alibi verified",
    r"confirmed not present",
    r"forensic(?:ally)? excluded",
    r"ruled out as (?:a )?perpetrator",
    r"verified not involved",
    r"eliminated from (?:the )?investigation",
]

UNSOLVED_PATTERNS = [
    r"\bcase (?:remains )?unsolved\b",
    r"\bunsolved case\b",
    r"\bcase is unsolved\b",
    r"\bremains an? unsolved\b",
    r"\bperpetrators? unidentified\b",
    r"\bno suspects? (?:have been |were )?identified\b",
    r"\bunidentified suspects\b",
    r"\bunidentified actors\b",
    r"\bunknown prowler\b",
    r"\bfalse alarm logged\b",
    r"\bperpetrators departed .*? prior to .*? arrival\b",
]

NEGATION_PATTERNS = [
    r"\b(?:not|never|neither|no|without)\s+(?:\w+\s+){0,4}(?:arrested?|detained?|apprehended?|in custody|placed under arrest|identified|charges filed)\b",
    r"\b(?:was|were|is|are|been)\s+not\s+(?:arrested|detained|apprehended)\b",
    r"\bneither\s+(?:suspect\s+)?was\s+(?:arrested|detained|apprehended)\b",
    r"\bno\s+suspects?\s+(?:were\s+)?(?:arrested|detained|apprehended)\b",
    r"\bno\s+arrests?\s+(?:were|was)?\s*(?:made|effected)\b",
    r"\bfailed\s+to\s+(?:arrest|detain|apprehend)\b",
    r"\bnot\s+arrested\b",
    r"\bnot\s+detained\b",
    r"\bnot\s+apprehended\b",
]

FAILED_ATTEMPT_PATTERNS = [
    r"\b(?:attempted?|tried|sought)\s+(?:to\s+)?(?:arrest|detain|apprehend)\b[^.\n]*?\b(?:failed|unsuccessful|fled|escaped|evaded)\b",
    r"\bofficers attempted to (?:arrest|detain|apprehend)[^.\n]*?(?:but failed|unsuccessfully)\b",
    r"\b(?:attempted|unsuccessful)\s+(?:arrest|detention|apprehension)\b",
    r"\b(?:evaded|escaped|fled\s+from|resisted)\s+(?:arrest|detention|apprehension|custody)\b",
    r"\battempted to (?:arrest|detain|apprehend)\b",
]

UNCERTAINTY_PATTERNS = [
    r"\b(?:may|might|could|possibly|allegedly|rumored|suspected\s+to|reportedly|unconfirmed\s+to|perhaps)\s+(?:have\s+been\s+)?(?:arrested|detained|apprehended|in custody|identified)\b",
    r"\b(?:unconfirmed|possible|alleged|rumored)\s+(?:arrest|detention|apprehension|identification)\b",
    r"\b(?:may|might|could)\s+be\s+(?:detained|arrested|in custody)\b",
]

HISTORICAL_UNRELATED_PATTERNS = [
    r"\b(?:previously|prior|past|earlier|historically)\s+(?:arrested|detained|apprehended|convicted|charged|in custody)\b",
    r"\b(?:prior|past|previous)\s+(?:arrest|detention|conviction|record|charges)\b",
    r"\barrested\s+(?:in|back\s+in)\s+(?:19\d\d|200\d|201[0-9])\b",
    r"\b(?:arrested|detained|apprehended)\s+(?:on|for)\s+unrelated\s+charges\b",
    r"\b(?:another|other|different)\s+person\s+(?:was\s+)?(?:previously\s+)?arrested\b",
    r"\barrested\s+in\s+(?:a\s+separate|an\s+unrelated|another)\s+(?:case|incident|investigation)\b",
    r"\bpreviously\s+arrested\b",
    r"\bprior\s+arrest\b",
]

CLEARANCE_KEYWORDS = [
    r"\bplaced under arrest\b",
    r"\bcleared by arrest\b",
    r"\barrested\b",
    r"\bdetained\b",
    r"\bapprehended\b",
    r"\bin custody\b",
    r"\bcharges? filed\b",
    r"\bcase solved\b",
    r"\bpositively identified\b",
    r"\bidentified as (?:the )?(?:perpetrators?|suspects?)\b",
    r"\b(?:latent\s+)?(?:fingerprints?|palm\s+prints?)\s+(?:recovered\s+[^.\n]*?\s+)?identified\b",
    r"\bpositively identified (?:via|from|through|by) (?:cctv|surveillance|security footage)\b",
    r"\bidentified (?:from|via|by|through) (?:cctv|surveillance|security footage)\b",
    r"\b(?:cctv|security footage|surveillance)\s+(?:footage\s+|surveillance\s+)?(?:recorded|showed|captured)\s+(?:and\s+)?(?:positively\s+)?identified\b",
    r"\b(?:cctv|security footage|surveillance)\s+(?:footage\s+|surveillance\s+)?(?:showed|captured|recorded)\s+(?:two\s+(?:\w+\s+)?perpetrators:?\s+)?(?:OID#\d+|The\s+[A-Z]\w+)",
]


def is_within_evaluation_window(doc: SanitizedRetrievalDocument) -> bool:
    """
    Validates whether the document or documented incident falls within the 6-month evaluation window
    (2020-01-01 to 2020-06-30).
    """
    # 1. Check doc.timestamp
    ts = doc.timestamp.strip()
    m_ts = re.match(r"^(\d{4}-\d{2}-\d{2})", ts)
    if m_ts:
        d = m_ts.group(1)
        if not (EVALUATION_WINDOW_START <= d <= EVALUATION_WINDOW_END):
            return False

    # 2. Check explicit narrative Date header
    m_date = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", doc.text_content)
    if m_date:
        d = m_date.group(1)
        if not (EVALUATION_WINDOW_START <= d <= EVALUATION_WINDOW_END):
            return False

    # 3. Check for historical year mentions in incident description
    m_hist = re.search(
        r"(?:incident occurred in|break-in in|burglary in|occurred on)\s+(19\d\d|20[01]\d|202[1-9])\b",
        doc.text_content,
        re.IGNORECASE
    )
    if m_hist:
        year = int(m_hist.group(1))
        if year != 2020:
            return False

    return True


def determine_solved_status(text: str) -> str:
    """
    Determines whether a documented burglary incident is solved, unsolved, or of unknown status.
    Returns: 'solved', 'unsolved', or 'unknown'.

    Semantic rules:
    - Positive clearance: Explicit arrest, detention, apprehension, charges filed, or positive
      identification establishes solved status in the absence of explicit unsolved assertions.
    - Negated arrest ('suspect was not arrested') does not establish solved status.
    - Failed/attempted arrest ('officers attempted to arrest the suspect but failed') does not establish solved status.
    - Uncertainty ('suspect may have been arrested') does not establish solved status.
    - Historical/prior references (another person previously arrested) do not establish current case solved.
    - Explicit unsolved evidence ('case remains unsolved') cannot be overridden by unrelated mentions of arrest, CCTV, or identification.
    - CCTV & forensic evidence: Mere mention of CCTV or fingerprints does not count as positive identification.
      Requires an explicit, contextually valid identification statement.
    """
    # 1. Explicit unsolved assertions strictly override any unrelated mentions
    if re.search(r"\bcase (?:remains )?unsolved\b", text, re.IGNORECASE):
        return "unsolved"

    has_unsolved = any(re.search(p, text, re.IGNORECASE) for p in UNSOLVED_PATTERNS)

    # 2. Check for contextually valid positive clearance statements
    sentences = re.split(r"[.\n;]+", text)
    valid_clearance = False

    for sent in sentences:
        sent_clean = sent.strip()
        if not sent_clean:
            continue

        has_kw = any(re.search(kw, sent_clean, re.IGNORECASE) for kw in CLEARANCE_KEYWORDS)
        if not has_kw:
            continue

        # Invalidate if negated, attempted/failed, uncertain, or historical/unrelated
        if any(re.search(p, sent_clean, re.IGNORECASE) for p in NEGATION_PATTERNS):
            continue
        if any(re.search(p, sent_clean, re.IGNORECASE) for p in FAILED_ATTEMPT_PATTERNS):
            continue
        if any(re.search(p, sent_clean, re.IGNORECASE) for p in UNCERTAINTY_PATTERNS):
            continue
        if any(re.search(p, sent_clean, re.IGNORECASE) for p in HISTORICAL_UNRELATED_PATTERNS):
            continue

        valid_clearance = True
        break

    if has_unsolved and not valid_clearance:
        return "unsolved"
    if valid_clearance and not has_unsolved:
        return "solved"
    if has_unsolved and valid_clearance:
        return "unsolved"
    return "unknown"


def _alias_key(alias: str) -> str:
    """Match spelling variants without changing the spelling shown in findings."""
    return " ".join(alias.split()).casefold()


def extract_document_facts(doc: SanitizedRetrievalDocument) -> Dict:
    """
    Extracts grounded evidential facts from a single validated retrieval document.
    Accurately separates direct communication, alias attributions, solved vs unsolved/unknown
    burglary incidents, and incident-level vs global exclusions.
    """
    text = doc.text_content
    doc_type = doc.doc_type

    is_field_interview = bool(re.search(
        r"field (?:intelligence )?(?:interview|interrogation|stop)|pedestrian stop",
        text, re.IGNORECASE,
    ))
    construction_container_burglary = bool(
        re.search(
            r"^\s*Entry Method:\s*cut\s+padlock\s+on\s+(?:the\s+)?construction\s+site\s+container\b",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    is_burglary = (
        doc_type == "incident_report"
        and not is_field_interview
        and (
            bool(re.search(r"burglar|burglary|break-in|forced lock|pried|jimmied|cut open", text, re.IGNORECASE))
            or construction_container_burglary
        )
    )
    in_window = is_within_evaluation_window(doc)
    solved_status = determine_solved_status(text) if is_burglary else "not_applicable"

    facts = {
        "doc_id": doc.doc_id,
        "doc_type": doc_type,
        "is_burglary_incident": is_burglary,
        "is_field_interview": is_field_interview,
        "is_in_evaluation_window": in_window,
        "solved_status": solved_status,
        "entities_mentioned": set(re.findall(r"OID#\d+", text)),
        "aliases_mentioned": set(),
        "alias_resolutions": {},  # alias -> canonical_entity
        "alias_candidates": [],  # retain competing attributions instead of last-write wins
        "co_suspects": [],
        "cdr_pair": None,
        "incident_id": None,
        "global_exclusions": [],   # list of (entity, matched_text)
        "incident_exclusions": [], # list of (entity, matched_text)
    }

    # Explicit attributions only; never infer identity from proximity or a suspect list.
    alias_patterns = [
        r"(OID#\d+)\s+uses\s+(?:the\s+active\s+street\s+)?moniker\s+['\"]([^'\"]+)['\"]",
        r"lists\s+(OID#\d+)\s+under\s+(?:the\s+established\s+)?moniker\s+['\"]([^'\"]+)['\"]",
        r"(OID#\d+)\s+(?:also\s+)?known\s+(?:by\s+the\s+moniker\s+|as\s+)['\"]([^'\"]+)['\"]",
        r"(OID#\d+)\s+operates\s+under\s+(?:the\s+)?(?:street\s+)?moniker\s+['\"]([^'\"]+)['\"]",
    ]
    for pattern in alias_patterns:
        for ent, al in re.findall(pattern, text, re.IGNORECASE):
            facts["alias_candidates"].append((al.strip(), ent.upper()))

    # This field-record form refers to 'subject' rather than repeating the ID.
    # Resolve it only in a single-entity interview with an explicit verified subject.
    verified = re.findall(r"\bVerified subject\s+(OID#\d+)\b", text)
    if is_field_interview and len(facts["entities_mentioned"]) == 1 and len(set(verified)) == 1:
        for al in re.findall(
            r"(?:^|[.\n])\s*Departmental intelligence confirms subject operates under "
            r"(?:the )?(?:street )?moniker ['\"]([^'\"]+)['\"]",
            text, re.IGNORECASE,
        ):
            facts["alias_candidates"].append((al.strip(), verified[0]))

    candidates_by_key = {}
    for al, ent in facts["alias_candidates"]:
        facts["aliases_mentioned"].add(al)
        candidates_by_key.setdefault(_alias_key(al), set()).add(ent)
    for al, ent in facts["alias_candidates"]:
        if len(candidates_by_key[_alias_key(al)]) == 1:
            facts["alias_resolutions"][al] = ent

    # Check for global exclusions (e.g. continuous custodial detention spanning evaluation window)
    for pattern in GLOBAL_EXCLUSION_PATTERNS:
        for m in re.finditer(rf"(OID#\d+)[^.\n]*?(?:{pattern})", text, re.IGNORECASE):
            ent = m.group(1).strip()
            item = (ent, m.group(0).strip())
            if item not in facts["global_exclusions"]:
                facts["global_exclusions"].append(item)
        for m in re.finditer(rf"(?:{pattern})[^.\n]*?(OID#\d+)", text, re.IGNORECASE):
            ent = m.group(1).strip()
            item = (ent, m.group(0).strip())
            if item not in facts["global_exclusions"]:
                facts["global_exclusions"].append(item)

    # Check for incident-specific exculpatory exclusion phrases in sentence
    for pattern in INCIDENT_EXCLUSION_PATTERNS:
        for m in re.finditer(rf"(OID#\d+)[^.\n]*?(?:{pattern})", text, re.IGNORECASE):
            ent = m.group(1).strip()
            item = (ent, m.group(0).strip())
            if item not in facts["incident_exclusions"]:
                facts["incident_exclusions"].append(item)
        for m in re.finditer(rf"(?:{pattern})[^.\n]*?(OID#\d+)", text, re.IGNORECASE):
            ent = m.group(1).strip()
            item = (ent, m.group(0).strip())
            if item not in facts["incident_exclusions"]:
                facts["incident_exclusions"].append(item)

    # Type-specific extraction
    if doc_type == "call_detail_record":
        for line in text.splitlines():
            if line.startswith("Caller:"):
                parts = line.split("-> Callee:")
                if len(parts) == 2:
                    caller = parts[0].replace("Caller:", "").strip().strip("'\"")
                    callee = parts[1].strip().strip("'\"")
                    facts["cdr_pair"] = (caller, callee)
                    if not caller.startswith("OID#"):
                        facts["aliases_mentioned"].add(caller)
                    if not callee.startswith("OID#"):
                        facts["aliases_mentioned"].add(callee)

    elif doc_type == "incident_report":
        inc_m = re.search(r"CASE\s+(INC-\d{4}-\d{4})", text)
        if inc_m:
            facts["incident_id"] = inc_m.group(1)

        for line in text.splitlines():
            if line.startswith("Suspects/Persons of Interest:"):
                suspect_str = line.replace("Suspects/Persons of Interest:", "").strip()
                items = [s.strip().strip("'\"") for s in suspect_str.split(",") if s.strip()]
                facts["co_suspects"] = items
                for item in items:
                    if not item.startswith("OID#") and not item.lower().startswith("unidentified"):
                        facts["aliases_mentioned"].add(item)

    return facts


class HypothesisVerifier:
    """
    Deterministic hypothesis verification tool.
    Evaluates whether candidate entities share at least one documented solved
    burglary case based strictly on cited corpus documents.
    """

    def __init__(self, corpus_path: Optional[str] = None):
        self._corpus_path = corpus_path or DEFAULT_CORPUS_PATH
        self._documents: Dict[str, SanitizedRetrievalDocument] = {}
        self._load_corpus()

    def _load_corpus(self) -> None:
        docs = load_and_validate_corpus(self._corpus_path)
        self._documents = {doc.doc_id: doc for doc in docs}

    @property
    def document_count(self) -> int:
        return len(self._documents)

    def verify(
        self,
        entity_a: str,
        entity_b: str,
        evidence_ids: List[str]
    ) -> VerificationResult:
        """
        Verifies the benchmark target hypothesis:
        'entity_a and entity_b share at least one documented solved burglary case within the evaluation window'.

        Validation rules:
        - entity_a and entity_b must be distinct, canonical 'OID#<digits>' strings.
        - evidence_ids must be a non-empty list of unique valid document IDs existing in the corpus.
        - Unknown document IDs raise ValueError.

        Decision rules:
        - 'Supported': Available evidence establishes shared-burglary co-offending via:
            1. Direct joint burglary incident report listing both entities as suspects with case clearance/solved status, OR
            2. Burglary incident report naming an alias that is resolved across cited evidence with case clearance/solved status.
        - 'Unsupported': Available evidence logically RULES OUT the benchmark target relationship across the
            full evaluation window (e.g. continuous custodial detention / incarceration spanning the entire evaluation window).
        - 'Insufficient Evidence': Evidence does not establish the benchmark target.
            1. An incident-specific exclusion or contradictory alias attribution refutes a single incident,
               but does not prove the absence of any other shared solved burglary across the evaluation window.
               (Recorded as an incident-level finding while the pair-level verdict remains 'Insufficient Evidence').
            2. A burglary incident with unknown or unsolved status does not establish a *solved* burglary case.
            3. Direct telecommunication (CDRs) or alias resolutions alone do not establish shared burglary participation.
            4. Absence of evidence is NEVER treated as proof of non-association.
        """
        # Validate entity identifiers
        if not isinstance(entity_a, str) or not ENTITY_REGEX.match(entity_a.strip()):
            raise ValueError(f"Invalid entity identifier: '{entity_a}'. Expected format 'OID#<digits>'.")
        if not isinstance(entity_b, str) or not ENTITY_REGEX.match(entity_b.strip()):
            raise ValueError(f"Invalid entity identifier: '{entity_b}'. Expected format 'OID#<digits>'.")

        ent_a = entity_a.strip()
        ent_b = entity_b.strip()

        if ent_a == ent_b:
            raise ValueError(
                f"Hypothesis entities must be distinct. Received identical entity '{ent_a}' for both arguments."
            )

        # Validate evidence IDs
        if not isinstance(evidence_ids, list) or len(evidence_ids) == 0:
            raise ValueError("evidence_ids must be a non-empty list of document IDs.")

        seen_ids = set()
        for doc_id in evidence_ids:
            if not isinstance(doc_id, str) or not DOC_ID_REGEX.match(doc_id):
                raise ValueError(
                    f"Invalid document ID format: '{doc_id}'. Must match '^(DOC_IR|CDR)_[0-9a-f]{{8}}$'."
                )
            if doc_id in seen_ids:
                raise ValueError(f"Duplicate document ID detected in evidence_ids: '{doc_id}'.")
            seen_ids.add(doc_id)

            if doc_id not in self._documents:
                raise ValueError(
                    f"Unknown document ID '{doc_id}' not found in retrieval corpus. "
                    f"All evidence IDs must exist in the validated corpus."
                )

        target_set = {ent_a, ent_b}

        # Extract facts from each cited document
        doc_facts = [extract_document_facts(self._documents[did]) for did in evidence_ids]

        # Aggregate known alias resolutions in cited evidence
        alias_resolutions: Dict[str, Tuple[str, str]] = {}  # alias -> (canonical_entity, resolving_doc_id)
        candidates_by_key = {}
        for df in doc_facts:
            for al, ent in df["alias_candidates"]:
                candidates_by_key.setdefault(_alias_key(al), set()).add((ent, df["doc_id"]))
        for df in doc_facts:
            for al in df["aliases_mentioned"]:
                candidates = candidates_by_key.get(_alias_key(al), set())
                if len({ent for ent, _ in candidates}) == 1:
                    alias_resolutions[al] = sorted(candidates)[0]

        findings: List[VerificationFinding] = []
        for df in doc_facts:
            conflicting = sorted({al for al, _ in df["alias_candidates"]
                                  if len({ent for ent, _ in candidates_by_key[_alias_key(al)]}) > 1})
            if conflicting:
                findings.append(VerificationFinding(
                    doc_id=df["doc_id"], doc_type=df["doc_type"],
                    finding_type="conflicting_alias_attribution",
                    entities_mentioned=sorted(df["entities_mentioned"]), aliases_mentioned=conflicting,
                    summary=f"Conflicting alias attributions in cited evidence for {', '.join(conflicting)}; identity left unresolved.",
                ))
        global_contradictions: List[Dict] = []
        incident_contradictions: List[Dict] = []
        cleared_incidents: Set[str] = set()

        direct_burglary_solved: List[Dict] = []
        direct_burglary_unsolved_or_unknown: List[Dict] = []
        alias_burglary_resolved_solved: List[Dict] = []
        alias_burglary_resolved_unsolved_or_unknown: List[Dict] = []
        alias_burglary_unresolved: List[Dict] = []
        direct_communication: List[Dict] = []
        alias_communication_resolved: List[Dict] = []
        alias_communication_unresolved: List[Dict] = []
        independent_mentions: List[Tuple[str, str]] = []
        alias_resolutions_only: List[Dict] = []

        # First pass: identify exclusions and track cleared incidents
        for df in doc_facts:
            did = df["doc_id"]
            dtype = df["doc_type"]
            ents = df["entities_mentioned"]
            als = df["aliases_mentioned"]

            # Global exclusions (e.g. continuous incarceration spanning evaluation window)
            for excl_subj, excl_text in df["global_exclusions"]:
                if excl_subj in target_set:
                    summary = (
                        f"Global exclusion documented in {did}: {excl_subj} - '{excl_text}', "
                        f"logically precluding offenses across the entire evaluation window."
                    )
                    global_contradictions.append({
                        "doc_id": did,
                        "type": "global_exclusion",
                        "entity": excl_subj,
                        "details": summary,
                    })
                    findings.append(VerificationFinding(
                        doc_id=did,
                        doc_type=dtype,
                        finding_type="global_exclusion",
                        entities_mentioned=sorted(list(ents)),
                        aliases_mentioned=sorted(list(als)),
                        summary=summary,
                    ))

            # Incident-specific exclusions
            for excl_subj, excl_text in df["incident_exclusions"]:
                if excl_subj in target_set:
                    inc_str = f"case {df['incident_id']}" if df["incident_id"] else did
                    if df["incident_id"]:
                        cleared_incidents.add(df["incident_id"])
                    summary = f"Explicit incident exclusion documented in {did} ({inc_str}): {excl_subj} - '{excl_text}'."
                    incident_contradictions.append({
                        "doc_id": did,
                        "incident_id": df["incident_id"],
                        "type": "explicit_exclusion",
                        "entity": excl_subj,
                        "details": summary,
                    })
                    findings.append(VerificationFinding(
                        doc_id=did,
                        doc_type=dtype,
                        finding_type="explicit_exclusion",
                        entities_mentioned=sorted(list(ents)),
                        aliases_mentioned=sorted(list(als)),
                        summary=summary,
                    ))

        # Second pass: evaluate co-offending, communications, and alias mappings
        for df in doc_facts:
            did = df["doc_id"]
            dtype = df["doc_type"]
            ents = df["entities_mentioned"]
            als = df["aliases_mentioned"]
            is_burglary = df["is_burglary_incident"]
            solved_st = df["solved_status"]

            # Incident reports
            if dtype == "incident_report":
                suspects = set(df["co_suspects"])

                if is_burglary:
                    # Direct burglary co-offending
                    if ent_a in suspects and ent_b in suspects:
                        is_cleared = bool(df["incident_id"] and df["incident_id"] in cleared_incidents)
                        if not is_cleared:
                            if not df["is_in_evaluation_window"]:
                                finding_summary = (
                                    f"Burglary incident report {did} (case {df['incident_id']}) lists {ent_a} and {ent_b} as suspects, "
                                    f"but the incident occurred outside the defined 6-month evaluation window ({EVALUATION_WINDOW_START} to {EVALUATION_WINDOW_END})."
                                )
                                direct_burglary_unsolved_or_unknown.append({
                                    "doc_id": did,
                                    "incident_id": df["incident_id"],
                                    "solved_status": "out_of_window",
                                    "details": finding_summary
                                })
                                findings.append(VerificationFinding(
                                    doc_id=did,
                                    doc_type=dtype,
                                    finding_type="out_of_window_burglary",
                                    entities_mentioned=sorted(list(ents)),
                                    aliases_mentioned=sorted(list(als)),
                                    summary=finding_summary
                                ))
                            elif solved_st == "solved":
                                finding_summary = (
                                    f"Direct solved burglary co-offending documented in {did} (case {df['incident_id']}): "
                                    f"{ent_a} and {ent_b} listed as co-suspects with case clearance/apprehension verified."
                                )
                                direct_burglary_solved.append({
                                    "doc_id": did,
                                    "incident_id": df["incident_id"],
                                    "details": finding_summary
                                })
                                findings.append(VerificationFinding(
                                    doc_id=did,
                                    doc_type=dtype,
                                    finding_type="direct_burglary_co_offending",
                                    entities_mentioned=sorted(list(ents)),
                                    aliases_mentioned=sorted(list(als)),
                                    summary=finding_summary
                                ))
                            else:
                                finding_summary = (
                                    f"Burglary incident report {did} (case {df['incident_id']}) lists {ent_a} and {ent_b} as suspects, "
                                    f"but available evidence does not establish solved status (status: {solved_st})."
                                )
                                direct_burglary_unsolved_or_unknown.append({
                                    "doc_id": did,
                                    "incident_id": df["incident_id"],
                                    "solved_status": solved_st,
                                    "details": finding_summary
                                })
                                findings.append(VerificationFinding(
                                    doc_id=did,
                                    doc_type=dtype,
                                    finding_type="unsolved_burglary_incident" if solved_st == "unsolved" else "unverified_status_burglary",
                                    entities_mentioned=sorted(list(ents)),
                                    aliases_mentioned=sorted(list(als)),
                                    summary=finding_summary
                                ))
                    else:
                        # Alias co-offending in burglary
                        for al in als:
                            if al in suspects:
                                if ent_a in suspects:
                                    if al in alias_resolutions:
                                        resolved_ent, res_doc = alias_resolutions[al]
                                        if resolved_ent == ent_b:
                                            is_cleared = bool(df["incident_id"] and df["incident_id"] in cleared_incidents)
                                            if not is_cleared:
                                                if not df["is_in_evaluation_window"]:
                                                    summary = (
                                                        f"Burglary incident report {did} (case {df['incident_id']}) with '{al}' "
                                                        f"(resolved to {ent_b} in {res_doc}) occurred outside the defined 6-month evaluation window ({EVALUATION_WINDOW_START} to {EVALUATION_WINDOW_END})."
                                                    )
                                                    alias_burglary_resolved_unsolved_or_unknown.append({
                                                        "doc_id": did,
                                                        "resolution_doc_id": res_doc,
                                                        "alias": al,
                                                        "incident_id": df["incident_id"],
                                                        "solved_status": "out_of_window",
                                                        "details": summary
                                                    })
                                                    findings.append(VerificationFinding(
                                                        doc_id=did,
                                                        doc_type=dtype,
                                                        finding_type="out_of_window_burglary",
                                                        entities_mentioned=sorted(list(ents)),
                                                        aliases_mentioned=sorted(list(als)),
                                                        summary=summary
                                                    ))
                                                elif solved_st == "solved":
                                                    summary = (
                                                        f"Solved burglary co-offending in {did} (case {df['incident_id']}) with '{al}', "
                                                        f"where '{al}' is resolved to {ent_b} in document {res_doc} and case clearance is verified."
                                                    )
                                                    alias_burglary_resolved_solved.append({
                                                        "doc_id": did,
                                                        "resolution_doc_id": res_doc,
                                                        "alias": al,
                                                        "incident_id": df["incident_id"],
                                                        "details": summary
                                                    })
                                                    findings.append(VerificationFinding(
                                                        doc_id=did,
                                                        doc_type=dtype,
                                                        finding_type="alias_burglary_co_offending",
                                                        entities_mentioned=sorted(list(ents)),
                                                        aliases_mentioned=sorted(list(als)),
                                                        summary=summary
                                                    ))
                                                else:
                                                    summary = (
                                                        f"Burglary incident report {did} (case {df['incident_id']}) with '{al}' "
                                                        f"(resolved to {ent_b} in {res_doc}), but incident is not established as solved (status: {solved_st})."
                                                    )
                                                    alias_burglary_resolved_unsolved_or_unknown.append({
                                                        "doc_id": did,
                                                        "resolution_doc_id": res_doc,
                                                        "alias": al,
                                                        "incident_id": df["incident_id"],
                                                        "solved_status": solved_st,
                                                        "details": summary
                                                    })
                                                    findings.append(VerificationFinding(
                                                        doc_id=did,
                                                        doc_type=dtype,
                                                        finding_type="unsolved_burglary_incident" if solved_st == "unsolved" else "unverified_status_burglary",
                                                        entities_mentioned=sorted(list(ents)),
                                                        aliases_mentioned=sorted(list(als)),
                                                        summary=summary
                                                    ))
                                        else:
                                            summary = (
                                                f"Contradictory alias attribution: Accomplice '{al}' in {did} ({df['incident_id']}) "
                                                f"is resolved to {resolved_ent} (in {res_doc}), contradicting {ent_b} for this incident."
                                            )
                                            incident_contradictions.append({
                                                "doc_id": did,
                                                "resolution_doc_id": res_doc,
                                                "alias": al,
                                                "type": "contradictory_attribution",
                                                "details": summary
                                            })
                                            findings.append(VerificationFinding(
                                                doc_id=did,
                                                doc_type=dtype,
                                                finding_type="contradictory_attribution",
                                                entities_mentioned=sorted(list(ents)),
                                                aliases_mentioned=sorted(list(als)),
                                                summary=summary
                                            ))
                                    else:
                                        summary = (
                                            f"Accomplice '{al}' documented in {did} (case {df['incident_id']}) alongside {ent_a}, "
                                            f"but moniker '{al}' is not resolved to {ent_b} in cited evidence."
                                        )
                                        alias_burglary_unresolved.append({
                                            "doc_id": did,
                                            "alias": al,
                                            "details": summary
                                        })
                                        findings.append(VerificationFinding(
                                            doc_id=did,
                                            doc_type=dtype,
                                            finding_type="alias_burglary_co_offending",
                                            entities_mentioned=sorted(list(ents)),
                                            aliases_mentioned=sorted(list(als)),
                                            summary=summary
                                        ))

                                elif ent_b in suspects:
                                    if al in alias_resolutions:
                                        resolved_ent, res_doc = alias_resolutions[al]
                                        if resolved_ent == ent_a:
                                            is_cleared = bool(df["incident_id"] and df["incident_id"] in cleared_incidents)
                                            if not is_cleared:
                                                if not df["is_in_evaluation_window"]:
                                                    summary = (
                                                        f"Burglary incident report {did} (case {df['incident_id']}) with '{al}' "
                                                        f"(resolved to {ent_a} in {res_doc}) occurred outside the defined 6-month evaluation window ({EVALUATION_WINDOW_START} to {EVALUATION_WINDOW_END})."
                                                    )
                                                    alias_burglary_resolved_unsolved_or_unknown.append({
                                                        "doc_id": did,
                                                        "resolution_doc_id": res_doc,
                                                        "alias": al,
                                                        "incident_id": df["incident_id"],
                                                        "solved_status": "out_of_window",
                                                        "details": summary
                                                    })
                                                    findings.append(VerificationFinding(
                                                        doc_id=did,
                                                        doc_type=dtype,
                                                        finding_type="out_of_window_burglary",
                                                        entities_mentioned=sorted(list(ents)),
                                                        aliases_mentioned=sorted(list(als)),
                                                        summary=summary
                                                    ))
                                                elif solved_st == "solved":
                                                    summary = (
                                                        f"Solved burglary co-offending in {did} (case {df['incident_id']}) with '{al}', "
                                                        f"where '{al}' is resolved to {ent_a} in document {res_doc} and case clearance is verified."
                                                    )
                                                    alias_burglary_resolved_solved.append({
                                                        "doc_id": did,
                                                        "resolution_doc_id": res_doc,
                                                        "alias": al,
                                                        "incident_id": df["incident_id"],
                                                        "details": summary
                                                    })
                                                    findings.append(VerificationFinding(
                                                        doc_id=did,
                                                        doc_type=dtype,
                                                        finding_type="alias_burglary_co_offending",
                                                        entities_mentioned=sorted(list(ents)),
                                                        aliases_mentioned=sorted(list(als)),
                                                        summary=summary
                                                    ))
                                                else:
                                                    summary = (
                                                        f"Burglary incident report {did} (case {df['incident_id']}) with '{al}' "
                                                        f"(resolved to {ent_a} in {res_doc}), but incident is not established as solved (status: {solved_st})."
                                                    )
                                                    alias_burglary_resolved_unsolved_or_unknown.append({
                                                        "doc_id": did,
                                                        "resolution_doc_id": res_doc,
                                                        "alias": al,
                                                        "incident_id": df["incident_id"],
                                                        "solved_status": solved_st,
                                                        "details": summary
                                                    })
                                                    findings.append(VerificationFinding(
                                                        doc_id=did,
                                                        doc_type=dtype,
                                                        finding_type="unsolved_burglary_incident" if solved_st == "unsolved" else "unverified_status_burglary",
                                                        entities_mentioned=sorted(list(ents)),
                                                        aliases_mentioned=sorted(list(als)),
                                                        summary=summary
                                                    ))
                                        else:
                                            summary = (
                                                f"Contradictory alias attribution: Accomplice '{al}' in {did} ({df['incident_id']}) "
                                                f"is resolved to {resolved_ent} (in {res_doc}), contradicting {ent_a} for this incident."
                                            )
                                            incident_contradictions.append({
                                                "doc_id": did,
                                                "resolution_doc_id": res_doc,
                                                "alias": al,
                                                "type": "contradictory_attribution",
                                                "details": summary
                                            })
                                            findings.append(VerificationFinding(
                                                doc_id=did,
                                                doc_type=dtype,
                                                finding_type="contradictory_attribution",
                                                entities_mentioned=sorted(list(ents)),
                                                aliases_mentioned=sorted(list(als)),
                                                summary=summary
                                            ))
                                    else:
                                        summary = (
                                            f"Accomplice '{al}' documented in {did} (case {df['incident_id']}) alongside {ent_b}, "
                                            f"but moniker '{al}' is not resolved to {ent_a} in cited evidence."
                                        )
                                        alias_burglary_unresolved.append({
                                            "doc_id": did,
                                            "alias": al,
                                            "details": summary
                                        })
                                        findings.append(VerificationFinding(
                                            doc_id=did,
                                            doc_type=dtype,
                                            finding_type="alias_burglary_co_offending",
                                            entities_mentioned=sorted(list(ents)),
                                            aliases_mentioned=sorted(list(als)),
                                            summary=summary
                                        ))

                # Alias resolution records (e.g. field interview / stop)
                if df["alias_resolutions"]:
                    for al, ent in df["alias_resolutions"].items():
                        if ent in target_set:
                            alias_resolutions_only.append({"doc_id": did, "entity": ent, "alias": al})
                        findings.append(VerificationFinding(
                            doc_id=did,
                            doc_type=dtype,
                            finding_type="alias_attribution",
                            entities_mentioned=sorted(list(ents)),
                            aliases_mentioned=sorted(list(als)),
                            summary=f"Intelligence resolution in {did}: verified subject {ent} operates under moniker '{al}'."
                        ))

            # Call Detail Records (CDRs)
            elif dtype == "call_detail_record":
                caller, callee = df["cdr_pair"]
                pair_set = {caller, callee}
                if pair_set == target_set:
                    summary = f"Direct telecommunication logged in {did}: {caller} <-> {callee}."
                    direct_communication.append({
                        "doc_id": did,
                        "type": "direct_communication",
                        "details": summary
                    })
                    findings.append(VerificationFinding(
                        doc_id=did,
                        doc_type=dtype,
                        finding_type="direct_communication",
                        entities_mentioned=sorted(list(ents)),
                        aliases_mentioned=sorted(list(als)),
                        summary=summary
                    ))
                else:
                    for al in als:
                        if al in pair_set:
                            other = callee if caller == al else caller
                            if other == ent_a:
                                if al in alias_resolutions:
                                    resolved_ent, res_doc = alias_resolutions[al]
                                    if resolved_ent == ent_b:
                                        summary = (
                                            f"Communication logged in {did} between {ent_a} and '{al}', "
                                            f"where '{al}' is established as {ent_b} in document {res_doc}."
                                        )
                                        alias_communication_resolved.append({
                                            "doc_id": did,
                                            "details": summary
                                        })
                                        findings.append(VerificationFinding(
                                            doc_id=did,
                                            doc_type=dtype,
                                            finding_type="alias_communication",
                                            entities_mentioned=sorted(list(ents)),
                                            aliases_mentioned=sorted(list(als)),
                                            summary=summary
                                        ))
                                    else:
                                        summary = (
                                            f"Contradictory alias communication in {did} between {ent_a} and '{al}', "
                                            f"where '{al}' is resolved to {resolved_ent} (in {res_doc}), contradicting {ent_b}."
                                        )
                                        incident_contradictions.append({
                                            "doc_id": did,
                                            "details": summary
                                        })
                                        findings.append(VerificationFinding(
                                            doc_id=did,
                                            doc_type=dtype,
                                            finding_type="contradictory_attribution",
                                            entities_mentioned=sorted(list(ents)),
                                            aliases_mentioned=sorted(list(als)),
                                            summary=summary
                                        ))
                                else:
                                    summary = (
                                        f"Communication in {did} between {ent_a} and '{al}', but moniker '{al}' "
                                        f"is not resolved to {ent_b} in cited evidence."
                                    )
                                    alias_communication_unresolved.append({
                                        "doc_id": did,
                                        "details": summary
                                    })
                                    findings.append(VerificationFinding(
                                        doc_id=did,
                                        doc_type=dtype,
                                        finding_type="alias_communication",
                                        entities_mentioned=sorted(list(ents)),
                                        aliases_mentioned=sorted(list(als)),
                                        summary=summary
                                    ))
                            elif other == ent_b:
                                if al in alias_resolutions:
                                    resolved_ent, res_doc = alias_resolutions[al]
                                    if resolved_ent == ent_a:
                                        summary = (
                                            f"Communication logged in {did} between {ent_b} and '{al}', "
                                            f"where '{al}' is established as {ent_a} in document {res_doc}."
                                        )
                                        alias_communication_resolved.append({
                                            "doc_id": did,
                                            "details": summary
                                        })
                                        findings.append(VerificationFinding(
                                            doc_id=did,
                                            doc_type=dtype,
                                            finding_type="alias_communication",
                                            entities_mentioned=sorted(list(ents)),
                                            aliases_mentioned=sorted(list(als)),
                                            summary=summary
                                        ))
                                    else:
                                        summary = (
                                            f"Contradictory alias communication in {did} between {ent_b} and '{al}', "
                                            f"where '{al}' is resolved to {resolved_ent} (in {res_doc}), contradicting {ent_a}."
                                        )
                                        incident_contradictions.append({
                                            "doc_id": did,
                                            "details": summary
                                        })
                                        findings.append(VerificationFinding(
                                            doc_id=did,
                                            doc_type=dtype,
                                            finding_type="contradictory_attribution",
                                            entities_mentioned=sorted(list(ents)),
                                            aliases_mentioned=sorted(list(als)),
                                            summary=summary
                                        ))
                                else:
                                    summary = (
                                        f"Communication in {did} between {ent_b} and '{al}', but moniker '{al}' "
                                        f"is not resolved to {ent_a} in cited evidence."
                                    )
                                    alias_communication_unresolved.append({
                                        "doc_id": did,
                                        "details": summary
                                    })
                                    findings.append(VerificationFinding(
                                        doc_id=did,
                                        doc_type=dtype,
                                        finding_type="alias_communication",
                                        entities_mentioned=sorted(list(ents)),
                                        aliases_mentioned=sorted(list(als)),
                                        summary=summary
                                    ))

            # Record independent or unrelated mentions
            existing_doc_findings = [f for f in findings if f.doc_id == did]
            if not existing_doc_findings:
                if ent_a in ents and ent_b not in ents:
                    independent_mentions.append((ent_a, did))
                    findings.append(VerificationFinding(
                        doc_id=did,
                        doc_type=dtype,
                        finding_type="independent_activity",
                        entities_mentioned=sorted(list(ents)),
                        aliases_mentioned=sorted(list(als)),
                        summary=f"Documents activity in {did} for {ent_a} only; no joint burglary link to {ent_b}."
                    ))
                elif ent_b in ents and ent_a not in ents:
                    independent_mentions.append((ent_b, did))
                    findings.append(VerificationFinding(
                        doc_id=did,
                        doc_type=dtype,
                        finding_type="independent_activity",
                        entities_mentioned=sorted(list(ents)),
                        aliases_mentioned=sorted(list(als)),
                        summary=f"Documents activity in {did} for {ent_b} only; no joint burglary link to {ent_a}."
                    ))
                else:
                    findings.append(VerificationFinding(
                        doc_id=did,
                        doc_type=dtype,
                        finding_type="unrelated_evidence",
                        entities_mentioned=sorted(list(ents)),
                        aliases_mentioned=sorted(list(als)),
                        summary=f"Document {did} does not document co-offending or communication between {ent_a} and {ent_b}."
                    ))

        # 4. DECISION SYNTHESIS FOR BENCHMARK TARGET RELATIONSHIP
        # Target: Two entities share at least one documented solved burglary case within the evaluation window.

        # Level 1: Global Contradiction (logically rules out benchmark target across the full window)
        if global_contradictions:
            status: VerificationStatus = "Unsupported"
            evidence_class: EvidenceClassification = "contradictory"
            gc = global_contradictions[0]
            rationale = (
                f"Global contradictory evidence: {gc['details']} "
                f"Logically rules out the benchmark target relationship across the evaluation window."
            )

        # Level 2: Direct Solved Burglary Co-offending
        elif direct_burglary_solved:
            status = "Supported"
            evidence_class = "direct"
            d = direct_burglary_solved[0]
            corrob = ""
            if direct_communication:
                cdr_ids = ", ".join(c["doc_id"] for c in direct_communication)
                corrob = f" Corroborating telecommunication logged in {cdr_ids}."
            rationale = f"Direct evidence: {d['details']}{corrob}"

        # Level 3: Indirect Resolved Solved Burglary Co-offending
        elif alias_burglary_resolved_solved:
            status = "Supported"
            evidence_class = "indirect_resolved"
            ir = alias_burglary_resolved_solved[0]
            corrob = ""
            if direct_communication or alias_communication_resolved:
                corrob = " Corroborating telecommunication is also documented."
            rationale = f"Indirect resolved evidence: {ir['details']}{corrob}"

        # Level 4: Incident-Specific Contradictions
        # Refutes a specific incident candidate, but does not establish the global negative claim.
        elif incident_contradictions:
            status = "Insufficient Evidence"
            evidence_class = "insufficient"
            ic = incident_contradictions[0]
            rationale = (
                f"Insufficient evidence (incident-level contradiction): {ic['details']} "
                f"An explicit exclusion or contradictory alias attribution for a specific incident "
                f"does not establish that the pair shares no other solved burglary case across the evaluation window. "
                f"Because the evidence does not establish the global negative claim, status is Insufficient Evidence."
            )

        # Level 5: Joint Burglary Reported but Unsolved or Unknown Solved Status (or Outside Evaluation Window)
        elif direct_burglary_unsolved_or_unknown or alias_burglary_resolved_unsolved_or_unknown:
            status = "Insufficient Evidence"
            evidence_class = "insufficient"
            item = (direct_burglary_unsolved_or_unknown + alias_burglary_resolved_unsolved_or_unknown)[0]
            if item.get("solved_status") == "out_of_window":
                rationale = (
                    f"Insufficient evidence (incident outside evaluation window): {item['details']} "
                    f"Under the benchmark definition, 'Supported' strictly requires evidence of a shared solved burglary case "
                    f"within the defined evaluation window ({EVALUATION_WINDOW_START} to {EVALUATION_WINDOW_END})."
                )
            else:
                rationale = (
                    f"Insufficient evidence (unsolved/unverified case status): {item['details']} "
                    f"Under the benchmark definition, 'Supported' strictly requires evidence of a shared *solved* burglary case. "
                    f"A burglary report or co-occurrence alone without confirmed clearance or apprehension does not satisfy the benchmark target."
                )

        # Level 6: Burglary with Unresolved Alias
        elif alias_burglary_unresolved:
            status = "Insufficient Evidence"
            evidence_class = "indirect_unresolved"
            iu = alias_burglary_unresolved[0]
            rationale = (
                f"Insufficient evidence (unresolved alias): {iu['details']} "
                f"An alias mention alone does not establish identity or shared burglary participation."
            )

        # Level 7: Direct Communication Alone
        elif direct_communication:
            status = "Insufficient Evidence"
            evidence_class = "insufficient"
            cdr_str = ", ".join(c["doc_id"] for c in direct_communication)
            rationale = (
                f"Insufficient evidence: Document {cdr_str} establishes direct telecommunication "
                f"between {ent_a} and {ent_b}, but no qualifying shared solved burglary incident is documented. "
                f"Communication alone does not establish the benchmark target relationship of shared burglary co-offending."
            )

        # Level 8: Alias Communication Resolved Alone
        elif alias_communication_resolved:
            status = "Insufficient Evidence"
            evidence_class = "insufficient"
            rationale = (
                f"Insufficient evidence: Cited documents establish telecommunication between {ent_a} and {ent_b} "
                f"(via an alias resolution), but no qualifying shared solved burglary incident is documented. "
                f"Communication and alias mapping alone do not establish shared burglary participation."
            )

        # Level 9: Alias Resolution Alone
        elif alias_resolutions_only:
            status = "Insufficient Evidence"
            evidence_class = "insufficient"
            res = alias_resolutions_only[0]
            rationale = (
                f"Insufficient evidence: Document {res['doc_id']} establishes that {res['entity']} "
                f"uses moniker '{res['alias']}', but no qualifying joint solved burglary incident is documented. "
                f"An alias resolution alone does not establish shared burglary participation."
            )

        # Level 10: Independent Activity
        elif independent_mentions:
            status = "Insufficient Evidence"
            evidence_class = "insufficient"
            doc_str = ", ".join(f"{ent} in {did}" for ent, did in independent_mentions)
            rationale = (
                f"Insufficient evidence: Cited documents establish independent activity ({doc_str}) "
                f"without documented co-participation in a shared solved burglary. "
                f"Temporal or geographic proximity alone does not establish a co-offending relationship."
            )

        # Level 11: Unrelated / Distractor / Absence of Evidence
        else:
            status = "Insufficient Evidence"
            evidence_class = "insufficient"
            rationale = (
                f"Insufficient evidence: None of the cited documents establish shared solved burglary co-offending "
                f"between {ent_a} and {ent_b}. The absence of a retrieved record cannot be interpreted "
                f"as proof that a relationship does not exist."
            )

        return VerificationResult(
            entity_a=ent_a,
            entity_b=ent_b,
            status=status,
            evidence_class=evidence_class,
            cited_evidence_ids=evidence_ids,
            rationale=rationale,
            findings=findings
        )



# Global singleton verifier
_DEFAULT_VERIFIER: Optional[HypothesisVerifier] = None


def get_default_verifier() -> HypothesisVerifier:
    """Returns the default HypothesisVerifier singleton, initializing once if needed."""
    global _DEFAULT_VERIFIER
    if _DEFAULT_VERIFIER is None:
        _DEFAULT_VERIFIER = HypothesisVerifier()
    return _DEFAULT_VERIFIER


def verify_hypothesis(
    entity_a: str,
    entity_b: str,
    evidence_ids: List[str],
    verifier: Optional[HypothesisVerifier] = None,
    corpus_path: Optional[str] = None
) -> VerificationResult:
    """
    Public hypothesis verification function for SPYDER investigative agents.

    Evaluates whether entity_a and entity_b share at least one documented solved
    burglary case within the evaluation window.

    Args:
        entity_a: First entity canonical ID (e.g. 'OID#4418').
        entity_b: Second entity canonical ID (e.g. 'OID#8864').
        evidence_ids: List of document IDs retrieved from the evidence corpus.
        verifier: Optional pre-initialized HypothesisVerifier instance.
        corpus_path: Optional path to a specific retrieval corpus file.

    Returns:
        Structured VerificationResult with status in {'Supported', 'Unsupported', 'Insufficient Evidence'},
        evidence classification, cited document IDs, grounded rationale, and per-document findings.
    """
    if verifier is not None:
        return verifier.verify(
            entity_a=entity_a,
            entity_b=entity_b,
            evidence_ids=evidence_ids
        )
    if corpus_path is not None:
        return HypothesisVerifier(corpus_path=corpus_path).verify(
            entity_a=entity_a,
            entity_b=entity_b,
            evidence_ids=evidence_ids
        )
    return get_default_verifier().verify(
        entity_a=entity_a,
        entity_b=entity_b,
        evidence_ids=evidence_ids
    )
