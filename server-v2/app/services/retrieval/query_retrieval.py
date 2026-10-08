from app.providers.embedding import EmbeddingModel, EmbeddingRequest
from app.schemas.reranking import RerankedSource
from app.services.retrieval.embedding_validation import validate_embedding_result
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline


class QueryRetrievalService:
    def __init__(
        self,
        *,
        embedding_model: EmbeddingModel,
        pipeline: RetrievalPipeline,
        expected_dimension: int,
        candidate_multiplier: int = 2,
    ) -> None:
        if type(expected_dimension) is not int or expected_dimension <= 0:
            raise ValueError("expected_dimension must be a positive integer")
        if type(candidate_multiplier) is not int or candidate_multiplier <= 0:
            raise ValueError("candidate_multiplier must be a positive integer")
        self._embedding_model = embedding_model
        self._pipeline = pipeline
        self._expected_dimension = expected_dimension
        self._candidate_multiplier = candidate_multiplier

    async def retrieve(self, query_text: str, *, final_k: int) -> list[RerankedSource]:
        request = EmbeddingRequest(texts=[query_text])
        result = validate_embedding_result(
            request,
            await self._embedding_model.embed(request),
            expected_dimension=self._expected_dimension,
        )
        return await self._pipeline.retrieve(
            query_text,
            result.vectors[0],
            candidate_k=final_k * self._candidate_multiplier,
            final_k=final_k,
        )
