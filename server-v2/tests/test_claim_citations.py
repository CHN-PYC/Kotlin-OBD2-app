import pytest

from app.schemas.generation import ClaimKind, GeneratedClaim
from app.schemas.qa import ClaimSupport
from app.services.generation.claim_citations import (
    claim_findings,
    claim_recommendations,
    describe_citation_check,
    find_quote,
    resolve_claim_citations,
)

EVIDENCE = {
    "maf-1": "Air-mass sensor function\nThe air-mass sensor measures the intake  air mass.",
    "maf-2": "Possible causes include contact faults at the electrical connections.",
}


def claim(
    text: str,
    kind: ClaimKind,
    *chunk_ids: str,
    quote: str | None = None,
    uses_vehicle_data: bool = False,
) -> GeneratedClaim:
    return GeneratedClaim(
        text=text,
        kind=kind,
        source_chunk_ids=list(chunk_ids),
        quote=quote,
        uses_vehicle_data=uses_vehicle_data,
    )


def test_support_levels_follow_mechanical_checks() -> None:
    result = resolve_claim_citations(
        [
            claim(
                "The sensor measures intake air mass.",
                ClaimKind.DEFINITION,
                "maf-1",
                quote="The air-mass sensor measures the intake air mass.",
            ),
            claim(
                "Loose connectors can cause faults.",
                ClaimKind.CAUSE,
                "maf-2",
                "made-up",
                quote="Loose plugs are the most common cause.",
            ),
            claim("Coolant reached 108 C.", ClaimKind.CAUSE, uses_vehicle_data=True),
            claim("The catalytic converter has failed.", ClaimKind.CAUSE, "made-up"),
        ],
        EVIDENCE,
    )

    assert [item.claim_id for item in result.claims] == ["c1", "c2", "c3", "c4"]
    assert [item.support for item in result.claims] == [
        ClaimSupport.QUOTED,
        ClaimSupport.CITED,
        ClaimSupport.VEHICLE_DATA,
        ClaimSupport.UNSUPPORTED,
    ]
    # The returned quote is the exact evidence span, so a client can highlight it directly.
    assert result.claims[0].quote == "The air-mass sensor measures the intake  air mass."
    assert result.claims[0].quote_chunk_id == "maf-1"
    assert result.claims[1].quote is None
    assert result.claims[1].source_chunk_ids == ["maf-2"]
    assert result.rejected_citation_count == 2
    assert result.unverified_quote_count == 1


def test_document_citation_takes_precedence_over_vehicle_data_flag() -> None:
    result = resolve_claim_citations(
        [claim("Mixed basis.", ClaimKind.CAUSE, "maf-2", uses_vehicle_data=True)],
        EVIDENCE,
    )

    assert result.claims[0].support is ClaimSupport.CITED


def test_quote_is_searched_in_every_valid_cited_chunk() -> None:
    result = resolve_claim_citations(
        [
            claim(
                "Contact faults are a cause.",
                ClaimKind.CAUSE,
                "maf-1",
                "maf-2",
                quote="contact faults at the electrical connections",
            )
        ],
        EVIDENCE,
    )

    assert result.claims[0].support is ClaimSupport.QUOTED
    assert result.claims[0].quote_chunk_id == "maf-2"


@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("“The air-mass sensor measures the intake air mass.”", True),
        ("THE AIR-MASS SENSOR MEASURES", True),
        ("air mass", False),  # too short to verify anything
        ("The sensor measures the intake air mass.", False),  # paraphrase
        (None, False),
    ],
)
def test_find_quote_tolerates_case_whitespace_and_wrappers_only(
    quote: str | None, expected: bool
) -> None:
    assert (find_quote(quote, EVIDENCE["maf-1"]) is not None) is expected


def test_duplicate_citations_are_collapsed_without_counting_as_rejected() -> None:
    result = resolve_claim_citations(
        [claim("Definition.", ClaimKind.DEFINITION, "maf-1", "maf-1")],
        EVIDENCE,
    )

    assert result.claims[0].source_chunk_ids == ["maf-1"]
    assert result.rejected_citation_count == 0


def test_without_evidence_every_document_citation_is_rejected() -> None:
    result = resolve_claim_citations([claim("Definition.", ClaimKind.DEFINITION, "maf-1")], {})

    assert result.claims[0].support is ClaimSupport.UNSUPPORTED
    assert describe_citation_check(result) == (
        "1 claims (quoted=0, cited=0, vehicle_data=0, unsupported=1); "
        "rejected 1 citations to unknown chunks; 0 quotes not found in cited evidence."
    )


def test_legacy_lists_split_check_claims_from_other_claims() -> None:
    result = resolve_claim_citations(
        [
            claim("Definition.", ClaimKind.DEFINITION),
            claim("Cause.", ClaimKind.CAUSE),
            claim("Check.", ClaimKind.CHECK),
        ],
        {},
    )

    assert claim_findings(result.claims) == ["Definition.", "Cause."]
    assert claim_recommendations(result.claims) == ["Check."]
