import re
from collections import Counter
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generation import ClaimKind, GeneratedClaim
from app.schemas.qa import ClaimSupport, ResponseClaim

# 太短的摘录（例如 "the sensor"）几乎在任何片段里都能匹配，不能作为核查依据。
MIN_QUOTE_CHARACTERS = 12
_QUOTE_WRAPPERS = "\"'“”‘’「」"


class ClaimCitationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ResponseClaim] = Field(default_factory=list)
    rejected_citation_count: int = Field(default=0, ge=0)
    unverified_quote_count: int = Field(default=0, ge=0)


def find_quote(quote: str | None, text: str) -> str | None:
    """Return the exact span of ``text`` matching ``quote``, ignoring case and whitespace runs."""
    if quote is None:
        return None
    words = quote.strip().strip(_QUOTE_WRAPPERS).split()
    if len(" ".join(words)) < MIN_QUOTE_CHARACTERS:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(0) if match else None


def resolve_claim_citations(
    claims: list[GeneratedClaim],
    evidence_text_by_chunk_id: Mapping[str, str],
) -> ClaimCitationResult:
    """Keep only citations to evidence actually sent in this call and verify quoted spans."""
    # LEARNING: 模型输出的 chunk_id 和摘录都是提议；只有能在本次证据中找到的才算数。
    resolved: list[ResponseClaim] = []
    rejected = 0
    unverified_quotes = 0
    for index, claim in enumerate(claims, start=1):
        kept: list[str] = []
        for chunk_id in claim.source_chunk_ids:
            if chunk_id not in evidence_text_by_chunk_id:
                rejected += 1
            elif chunk_id not in kept:
                kept.append(chunk_id)

        quote: str | None = None
        quote_chunk_id: str | None = None
        for chunk_id in kept:
            quote = find_quote(claim.quote, evidence_text_by_chunk_id[chunk_id])
            if quote is not None:
                quote_chunk_id = chunk_id
                break
        if claim.quote is not None and quote is None:
            unverified_quotes += 1

        if quote is not None:
            support = ClaimSupport.QUOTED
        elif kept:
            support = ClaimSupport.CITED
        elif claim.uses_vehicle_data:
            support = ClaimSupport.VEHICLE_DATA
        else:
            support = ClaimSupport.UNSUPPORTED
        resolved.append(
            ResponseClaim(
                claim_id=f"c{index}",
                text=claim.text,
                kind=claim.kind,
                support=support,
                source_chunk_ids=kept,
                quote=quote,
                quote_chunk_id=quote_chunk_id,
            )
        )
    return ClaimCitationResult(
        claims=resolved,
        rejected_citation_count=rejected,
        unverified_quote_count=unverified_quotes,
    )


def claim_findings(claims: list[ResponseClaim]) -> list[str]:
    """Flatten definition/cause claims for clients that read the legacy findings list."""
    return [claim.text for claim in claims if claim.kind is not ClaimKind.CHECK]


def claim_recommendations(claims: list[ResponseClaim]) -> list[str]:
    """Flatten check claims for clients that read the legacy recommendations list."""
    return [claim.text for claim in claims if claim.kind is ClaimKind.CHECK]


def describe_citation_check(result: ClaimCitationResult) -> str:
    counts = Counter(claim.support for claim in result.claims)
    breakdown = ", ".join(f"{support.value}={counts[support]}" for support in ClaimSupport)
    return (
        f"{len(result.claims)} claims ({breakdown}); "
        f"rejected {result.rejected_citation_count} citations to unknown chunks; "
        f"{result.unverified_quote_count} quotes not found in cited evidence."
    )
