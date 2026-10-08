import asyncio

from app.schemas.knowledge import KnowledgeChunk
from app.services.retrieval.bm25 import BM25Retriever, tokenize_for_bm25


def chunk(chunk_id: str, text: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        doc_id="doc",
        title="Guide",
        section_title="Checks",
        source_url="https://example.com",
        text=text,
    )


def test_tokenizer_preserves_dtc_and_creates_chinese_bigrams() -> None:
    tokens = tokenize_for_bm25("检查 P0171 燃油修正")

    assert "p0171" in tokens
    assert "燃油" in tokens
    assert "修正" in tokens


def test_bm25_ranks_exact_diagnostic_terms_first() -> None:
    retriever = BM25Retriever(
        [
            chunk("fuel", "P0171 表示混合气过稀，检查燃油修正"),
            chunk("coolant", "检查冷却液温度传感器"),
        ]
    )

    results = asyncio.run(retriever.search("P0171 燃油修正", k=2))

    assert results[0].chunk_id == "fuel"
    assert results[0].score > 0


def test_bm25_rejects_blank_query() -> None:
    retriever = BM25Retriever([chunk("a", "evidence")])

    try:
        asyncio.run(retriever.search(" ", k=1))
    except ValueError as exc:
        assert "blank" in str(exc)
    else:
        raise AssertionError("blank query must fail")
