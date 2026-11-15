from app.schemas.generation import ClaimKind, GeneratedClaim
from app.schemas.qa import ClaimSupport
from app.services.generation.claim_citations import (
    claim_findings,
    claim_recommendations,
    describe_citation_check,
    resolve_claim_citations,
)


def claim(text: str, kind: ClaimKind, *chunk_ids: str) -> GeneratedClaim:
    return GeneratedClaim(text=text, kind=kind, source_chunk_ids=list(chunk_ids))


def test_keeps_citations_to_supplied_evidence_only() -> None:
    result = resolve_claim_citations(
        [
            claim("P0101 means MAF range/performance.", ClaimKind.DEFINITION, "maf-1"),
            claim("A dirty MAF element can skew readings.", ClaimKind.CAUSE, "maf-2", "made-up"),
            claim("The catalytic converter has failed.", ClaimKind.CAUSE, "made-up"),
            claim("Inspect the intake for leaks.", ClaimKind.CHECK),
        ],
        ["maf-1", "maf-2"],
    )

    assert [item.claim_id for item in result.claims] == ["c1", "c2", "c3", "c4"]
    assert [item.support for item in result.claims] == [
        ClaimSupport.CITED,
        ClaimSupport.CITED,
        ClaimSupport.UNSUPPORTED,
        ClaimSupport.UNSUPPORTED,
    ]
    assert result.claims[1].source_chunk_ids == ["maf-2"]
    assert result.claims[2].source_chunk_ids == []
    assert result.rejected_citation_count == 2


def test_duplicate_citations_are_collapsed_without_counting_as_rejected() -> None:
    result = resolve_claim_citations(
        [claim("Definition.", ClaimKind.DEFINITION, "maf-1", "maf-1")],
        ["maf-1"],
    )

    assert result.claims[0].source_chunk_ids == ["maf-1"]
    assert result.rejected_citation_count == 0


def test_without_evidence_every_claim_is_unsupported() -> None:
    result = resolve_claim_citations([claim("Definition.", ClaimKind.DEFINITION, "maf-1")], [])

    assert result.claims[0].support is ClaimSupport.UNSUPPORTED
    assert describe_citation_check(result) == (
        "0 of 1 claims cite supplied evidence; rejected 1 citations to unknown chunks."
    )


def test_legacy_lists_split_check_claims_from_other_claims() -> None:
    result = resolve_claim_citations(
        [
            claim("Definition.", ClaimKind.DEFINITION),
            claim("Cause.", ClaimKind.CAUSE),
            claim("Check.", ClaimKind.CHECK),
        ],
        [],
    )

    assert claim_findings(result.claims) == ["Definition.", "Cause."]
    assert claim_recommendations(result.claims) == ["Check."]
