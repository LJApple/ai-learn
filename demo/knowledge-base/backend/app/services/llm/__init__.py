"""LLM and Embedding services."""

import asyncio
from functools import lru_cache
from typing import Any

import torch
from openai import AsyncOpenAI, OpenAI
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM

from app.core.config import settings


class EmbeddingService:
    """Embedding service using sentence-transformers."""

    def __init__(self) -> None:
        """Initialize embedding service."""
        self.model_name = settings.EMBEDDING_MODEL
        self.device = settings.EMBEDDING_DEVICE
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Get lazy-loaded model."""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
        return self._model

    def encode(
        self,
        texts: list[str] | str,
        normalize: bool = True,
    ) -> list[list[float]] | list[float]:
        """Encode texts to embeddings.

        Args:
            texts: Single text or list of texts
            normalize: Whether to normalize embeddings

        Returns:
            Embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            batch_size=self.batch_size,
            show_progress_bar=len(texts) > 100,
        )

        return embeddings.tolist()

    async def aencode(
        self,
        texts: list[str] | str,
        normalize: bool = True,
    ) -> list[list[float]] | list[float]:
        """Async encode texts to embeddings.

        Args:
            texts: Single text or list of texts
            normalize: Whether to normalize embeddings

        Returns:
            Embedding vectors
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.encode(texts, normalize),
        )

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()


class RerankService:
    """Reranking service for search results."""

    def __init__(self) -> None:
        """Initialize rerank service."""
        self.model_name = settings.RERANK_MODEL
        self.device = settings.RERANK_DEVICE
        self.top_k = settings.RERANK_TOP_K
        self._model: torch.nn.Module | None = None

    @property
    def model(self) -> torch.nn.Module:
        """Get lazy-loaded model."""
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
            )
        return self._model

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """Rerank documents by query relevance.

        Args:
            query: Search query
            documents: List of documents with 'content' field
            top_k: Number of top results to return (defaults to self.top_k)

        Returns:
            Reranked document list with scores
        """
        if not documents:
            return []

        if top_k is None:
            top_k = min(self.top_k, len(documents))

        # Prepare pairs
        pairs = [[query, doc.get("content", "")] for doc in documents]

        # Compute scores
        scores = self.model.predict(pairs)

        # Add scores and sort
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        # Sort by score descending
        documents.sort(key=lambda x: x["rerank_score"], reverse=True)

        return documents[:top_k]

    async def arerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """Async rerank documents.

        Args:
            query: Search query
            documents: List of documents
            top_k: Number of top results to return

        Returns:
            Reranked document list
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.rerank(query, documents, top_k),
        )


class LLMService:
    """LLM service for text generation."""

    def __init__(self) -> None:
        """Initialize LLM service."""
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.top_p = settings.LLM_TOP_P

        # Async client
        self._async_client: AsyncOpenAI | None = None
        self._sync_client: OpenAI | None = None

    @property
    def async_client(self) -> AsyncOpenAI:
        """Get async OpenAI client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "not-needed",
            )
        return self._async_client

    @property
    def sync_client(self) -> OpenAI:
        """Get sync OpenAI client."""
        if self._sync_client is None:
            self._sync_client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "not-needed",
            )
        return self._sync_client

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stream: bool = False,
    ) -> str | Any:
        """Generate chat completion.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            top_p: Nucleus sampling parameter
            stream: Whether to stream responses

        Returns:
            Generated text or stream iterator
        """
        response = self.sync_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            top_p=top_p or self.top_p,
            stream=stream,
        )

        if stream:
            return response
        return response.choices[0].message.content

    async def acomplete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stream: bool = False,
    ) -> str | Any:
        """Async generate chat completion.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            top_p: Nucleus sampling parameter
            stream: Whether to stream responses

        Returns:
            Generated text or stream iterator
        """
        if self.api_key == "MOCK":
            print("Using Mock LLM response")
            mock_response = "这是一个模拟的回答。由于未配置有效的 LLM 服务，系统使用了 Mock 模式。请检查后端配置。"
            if stream:
                # 简单的 Mock 流式响应
                async def mock_stream():
                    for char in mock_response:
                        yield type('obj', (object,), {'choices': [type('obj', (object,), {'delta': type('obj', (object,), {'content': char})})]})()
                        await asyncio.sleep(0.05)
                return mock_stream()
            return mock_response

        print(f"Calling LLM at {self.base_url} with model {self.model}")
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                top_p=top_p or self.top_p,
                stream=stream,
            )

            if stream:
                return response
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM call failed: {e}")
            raise e
        return response.choices[0].message.content

    async def acomplete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ):
        """Async stream chat completion.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            top_p: Nucleus sampling parameter

        Yields:
            Stream chunks
        """
        stream = await self.acomplete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# Global service instances
@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Get cached embedding service."""
    return EmbeddingService()


@lru_cache
def get_rerank_service() -> RerankService:
    """Get cached rerank service."""
    return RerankService()


@lru_cache
def get_llm_service() -> LLMService:
    """Get cached LLM service."""
    return LLMService()


# Convenience exports
embedding_service = get_embedding_service()
rerank_service = get_rerank_service()
llm_service = get_llm_service()
