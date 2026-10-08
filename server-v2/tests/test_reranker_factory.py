from app.core.config import RerankerProvider, Settings
from app.providers.factory import create_reranker
from app.services.retrieval.reranking import PassThroughReranker, ResilientReranker


def test_factory_uses_pass_through_by_default() -> None:
    reranker = create_reranker(Settings(_env_file=None))

    assert isinstance(reranker, PassThroughReranker)


def test_factory_builds_resilient_fastembed_reranker_without_loading_model() -> None:
    reranker = create_reranker(
        Settings(
            _env_file=None,
            reranker_provider=RerankerProvider.FASTEMBED,
            reranker_model="BAAI/bge-reranker-base",
        )
    )

    assert isinstance(reranker, ResilientReranker)
