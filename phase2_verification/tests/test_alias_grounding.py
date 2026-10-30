"""Alias support must follow explicit, unambiguous evidence, independent of citation order."""

import json
from pathlib import Path

import pytest

from phase2_ground_truth_vault.schemas import SanitizedRetrievalDocument
from phase2_verification.verifier import HypothesisVerifier, extract_document_facts


def document(number, text):
    return SanitizedRetrievalDocument(doc_id=f"DOC_IR_{number:08x}", doc_type="incident_report",
                                      timestamp="2020-03-01 12:00:00", text_content=text)


def verify(tmp_path, docs, order=None):
    path = tmp_path / "corpus.jsonl"
    path.write_text("\n".join(d.model_dump_json() for d in docs), encoding="utf-8")
    return HypothesisVerifier(str(path)).verify("OID#100", "OID#200", order or [d.doc_id for d in docs])


def incident(alias="The Scout", solved=True):
    return document(1, f"CASE INC-2020-1234\nEntry Method: residential burglary\n"
                    f"Suspects/Persons of Interest: OID#100, '{alias}'\n"
                    + ("Case cleared by arrest." if solved else "Case remains unsolved."))


def interview(extra="", attribution=None):
    return document(2, "Field intelligence interview. Verified subject OID#200 was identified operating vehicle. "
                    + (attribution or "Departmental intelligence confirms subject operates under street moniker 'The Scout'.")
                    + extra)


def test_subject_reference_requires_single_verified_entity(tmp_path):
    assert verify(tmp_path, [incident(), interview()]).status == "Supported"
    assert extract_document_facts(interview())["is_field_interview"]
    assert verify(tmp_path, [incident(), interview(" Witness OID#300 attended.")]).status == "Insufficient Evidence"


@pytest.mark.parametrize("text", [
    "Departmental intelligence does not confirm subject operates under street moniker 'The Scout'.",
    "Unverified claim: subject operates under street moniker 'The Scout'.",
])
def test_negative_or_unverified_attributions_are_not_identity_proof(tmp_path, text):
    assert verify(tmp_path, [incident(), interview(attribution=text)]).status == "Insufficient Evidence"


def test_alias_case_spacing_and_direct_operates_wording(tmp_path):
    field = document(2, "Field interview. OID#200 operates under street moniker 'the   SCOUT'.")
    assert verify(tmp_path, [incident(), field]).status == "Supported"
    assert verify(tmp_path, [incident(solved=False), field]).status == "Insufficient Evidence"
    assert verify(tmp_path, [field]).status == "Insufficient Evidence"


def test_conflicting_attributions_do_not_depend_on_citation_order(tmp_path):
    docs = [incident(), interview(), document(3, "Field interview. OID#300 known as 'the scout'.")]
    for order in ([d.doc_id for d in docs], [d.doc_id for d in reversed(docs)]):
        assert verify(tmp_path, docs, order).status == "Insufficient Evidence"


def test_conflicting_attributions_within_one_document(tmp_path):
    field = document(2, "Field interview. OID#200 known as 'The Scout'. OID#300 known as 'The Scout'.")
    assert extract_document_facts(field)["alias_resolutions"] == {}
    assert verify(tmp_path, [incident(), field]).status == "Insufficient Evidence"


def test_full_corpus_resolution_record_grammar():
    # A compatibility diagnostic of existing text, not tuning against hidden labels.
    path = Path(__file__).resolve().parents[2] / "phase2_corpus" / "test_retrieval_documents.jsonl"
    docs = [SanitizedRetrievalDocument.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()]
    records = [d for d in docs if "operates under" in d.text_content]
    assert len(records) == 40
    assert all(len(extract_document_facts(d)["alias_resolutions"]) == 1 for d in records)
