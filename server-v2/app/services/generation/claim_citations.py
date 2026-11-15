from collections.abc import Collection

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generation import ClaimKind, GeneratedClaim
from app.schemas.qa import ClaimSupport, ResponseClaim


class ClaimCitationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ResponseClaim] = Field(default_factory=list)
    rejected_citation_count: int = Field(default=0, ge=0)


def resolve_claim_citations(
    claims: list[GeneratedClaim],
    available_chunk_ids: Collection[str],
) -> ClaimCitationResult:
    """Keep only citations that point at evidence actually sent in this call."""
    # LEARNING: 模型输出的 chunk_id 是提议；只有出现在本次 prompt 证据里的 ID 才算引用。
    available = set(available_chunk_ids)
    resolved: list[ResponseClaim] = []
    rejected = 0
    for index, claim in enumerate(claims, start=1):
        kept: list[str] = []
        for chunk_id in claim.source_chunk_ids:
            if chunk_id in available and chunk_id not in kept:
                kept.append(chunk_id)
            elif chunk_id not in available:
                rejected += 1
        resolved.append(
            ResponseClaim(
                claim_id=f"c{index}",
                text=claim.text,
                kind=claim.kind,
                support=ClaimSupport.CITED if kept else ClaimSupport.UNSUPPORTED,
                source_chunk_ids=kept,
            )
        )
    return ClaimCitationResult(claims=resolved, rejected_citation_count=rejected)


def claim_findings(claims: list[ResponseClaim]) -> list[str]:
    """Flatten definition/cause claims for clients that read the legacy findings list."""
    return [claim.text for claim in claims if claim.kind is not ClaimKind.CHECK]


def claim_recommendations(claims: list[ResponseClaim]) -> list[str]:
    """Flatten check claims for clients that read the legacy recommendations list."""
    return [claim.text for claim in claims if claim.kind is ClaimKind.CHECK]


def describe_citation_check(result: ClaimCitationResult) -> str:
    cited = sum(1 for claim in result.claims if claim.support is ClaimSupport.CITED)
    return (
        f"{cited} of {len(result.claims)} claims cite supplied evidence; "
        f"rejected {result.rejected_citation_count} citations to unknown chunks."
    )
