"""Record how the configured chat model's claim citations survive server-side checks.

Generation-stage smoke only: BM25 over one processed corpus file (no embedding model or
Qdrant), then the configured chat provider, parser and claim-citation checks.

    uv run python -m scripts.smoke_claim_citations --max-tokens 4096

Writes a JSON record (no credentials) so reported numbers can be traced to raw output.
The record keeps the model's raw proposal and the server's filtered result apart: a
filtered response can never contain unknown IDs, so only the raw proposal shows whether
the model invented any.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.providers.chat import ChatOptions
from app.providers.errors import InvalidModelResponseError
from app.providers.factory import create_chat_model
from app.schemas.qa import ClaimSupport, VehicleQARequest
from app.services.generation.answer_parser import VehicleAnswerParser
from app.services.generation.claim_citations import (
    describe_citation_check,
    resolve_claim_citations,
)
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.knowledge.corpus_loader import load_chunks
from app.services.retrieval.bm25 import BM25Retriever

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/processed/hella_air_mass_sensor.chunks.json"
FIXTURE = ROOT / "tests/fixtures/vehicle_qa_request.json"

# English questions: the corpus is English and BM25 has no cross-lingual matching.
# P0420 is deliberately outside the corpus topic, to see what gets cited anyway.
QUESTIONS = [
    "What does the air mass sensor measure and how does it work?",
    "What does fault code P0101 mean and what usually causes it?",
    "How should I check an air mass sensor that reports implausible values?",
    "Why is my catalytic converter efficiency below threshold (P0420)?",
]


async def run_one(
    question: str,
    settings: Settings,
    retriever: BM25Retriever,
    base_payload: dict[str, Any],
    max_tokens: int,
) -> dict[str, Any]:
    request = VehicleQARequest.model_validate({**base_payload, "question": question})
    sources = await retriever.search(question, k=5)
    chat_request, selected = VehicleQAPromptBuilder(
        options=ChatOptions(max_output_tokens=max_tokens)
    ).build_with_selection(request, sources=sources)
    record: dict[str, Any] = {
        "question": question,
        "evidence_chunk_ids": [source.chunk_id for source in selected],
    }
    if not selected:
        record["status"] = "no_evidence"
        return record
    try:
        result = await create_chat_model(settings).generate(chat_request)
        generated = VehicleAnswerParser().parse(result)
    except InvalidModelResponseError as exc:
        record["status"] = f"model_error:{exc.code}"
        return record

    evidence = {source.chunk_id: source.text for source in selected}
    citations = resolve_claim_citations(generated.claims, evidence)
    record.update(
        status="ok",
        finish_reason=result.finish_reason,
        output_tokens=result.output_tokens,
        answer=generated.answer,
        citation_check=describe_citation_check(citations),
        raw_claims=[claim.model_dump(mode="json") for claim in generated.claims],
        response_claims=[claim.model_dump(mode="json") for claim in citations.claims],
        raw_proposal={
            "cited_ids": sum(len(claim.source_chunk_ids) for claim in generated.claims),
            "ids_outside_evidence": citations.rejected_citation_count,
            "quotes": sum(1 for claim in generated.claims if claim.quote),
            "quotes_not_found": citations.unverified_quote_count,
        },
    )
    return record


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [record for record in records if record.get("status") == "ok"]
    support_counts = {support.value: 0 for support in ClaimSupport}
    for record in ok:
        for claim in record["response_claims"]:
            support_counts[claim["support"]] += 1
    return {
        "questions": len(records),
        "answered": len(ok),
        "claims": sum(support_counts.values()),
        "support_counts": support_counts,
        "raw_cited_ids": sum(r["raw_proposal"]["cited_ids"] for r in ok),
        "raw_ids_outside_evidence": sum(r["raw_proposal"]["ids_outside_evidence"] for r in ok),
        "raw_quotes": sum(r["raw_proposal"]["quotes"] for r in ok),
        "raw_quotes_not_found": sum(r["raw_proposal"]["quotes_not_found"] for r in ok),
    }


def print_record(record: dict[str, Any]) -> None:
    print("=" * 80)
    print("Q:", record["question"], "| status:", record["status"])
    for claim in record.get("response_claims", []):
        print(f"- [{claim['claim_id']}] {claim['kind']:<10} {claim['support']:<12} {claim['text']}")
        if claim["quote"]:
            print(f"      quote in {claim['quote_chunk_id']}: {' '.join(claim['quote'].split())!r}")
    if "citation_check" in record:
        print("check:", record["citation_check"])


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    settings = Settings(model_max_attempts=1, model_timeout_seconds=120)
    retriever = BM25Retriever(load_chunks([CORPUS]))
    base_payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for question in QUESTIONS:
        record = await run_one(question, settings, retriever, base_payload, args.max_tokens)
        print_record(record)
        records.append(record)

    started = datetime.now(UTC)
    report = {
        "run_at": started.isoformat(timespec="seconds"),
        "provider": settings.model_provider.value,
        "model": settings.llm_model,
        "max_output_tokens": args.max_tokens,
        "retrieval": "bm25 top-5 over " + CORPUS.name,
        "summary": summarise(records),
        "records": records,
    }
    output = args.output or (
        ROOT / "docs/evaluation" / f"claim_citation_smoke_{started:%Y%m%d}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("=" * 80)
    print(json.dumps(report["summary"], indent=2))
    print("written:", output.relative_to(ROOT) if output.is_relative_to(ROOT) else output)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
