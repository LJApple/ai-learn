"""RAG retrieval and QA service."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.services.llm import embedding_service, rerank_service, llm_service
from app.services.vector import milvus_service


class RetrievalService:
    """Document retrieval service."""

    async def retrieve(
        self,
        query: str,
        user: User,
        top_k: int | None = None,
        score_threshold: float | None = None,
        use_rerank: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents for a query.

        Args:
            query: Search query
            user: User making the request (for permission filtering)
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            use_rerank: Whether to use reranking

        Returns:
            List of retrieved chunks with scores
        """
        top_k = top_k or settings.TOP_K_RETRIEVAL
        score_threshold = score_threshold or settings.SCORE_THRESHOLD

        # Generate query embedding
        query_embedding = await embedding_service.aencode(query)
        if isinstance(query_embedding, list) and len(query_embedding) > 0 and isinstance(query_embedding[0], list):
            query_embedding = query_embedding[0]

        # Build permission filters
        filters = self._build_permission_filters(user)

        # Search vector DB
        milvus_service.connect()
        try:
            results = milvus_service.search(
                embedding=query_embedding,
                top_k=top_k * 2 if use_rerank else top_k,
                filters=filters,
            )
        finally:
            milvus_service.disconnect()

        # Filter by score threshold
        results = [r for r in results if r["score"] >= score_threshold]

        if use_rerank and results:
            # Rerank results
            results = await rerank_service.arerank(
                query=query,
                documents=results,
                top_k=top_k,
            )

        return results

    def _build_permission_filters(self, user: User) -> dict[str, Any]:
        """Build permission filters for user.

        Args:
            user: User to build filters for

        Returns:
            Filter dictionary
        """
        filters = {}

        if user.is_superuser:
            # No filters for superuser
            return filters

        # Get public and department-level documents
        filters["public_or_department"] = True

        # Add department filter if user has one
        if user.department_id:
            filters["department_id"] = str(user.department_id)

        # TODO: Add explicit document permissions from DB

        return filters


class QAService:
    """Question answering service using RAG."""

    def __init__(self) -> None:
        """Initialize QA service."""
        self.retrieval = RetrievalService()
        self.system_prompt = """你是一个企业知识库助手，负责回答员工的问题。

请根据提供的知识库内容回答问题。如果知识库中没有相关信息，请明确告知，不要编造答案。

回答时请注意：
1. 基于提供的知识库内容给出准确答案
2. 如果信息不足，说明需要哪些额外信息
3. 保持回答简洁明了
4. 可以适当引用知识库来源

知识库内容：
{context}"""

        self.no_answer_prompt = """抱歉，我在知识库中没有找到相关信息来回答您的问题。

您可以：
1. 尝试重新表述您的问题
2. 联系相关部门或人员
3. 在公司 Wiki 或文档中继续查找"""

    async def ask(
        self,
        db: AsyncSession,
        query: str,
        user: User,
        conversation_id: uuid.UUID | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
        use_rerank: bool = True,
    ) -> dict[str, Any]:
        """Answer a question using RAG.

        Args:
            db: Database session
            query: User question
            user: User asking the question
            conversation_id: Optional conversation ID
            top_k: Number of documents to retrieve
            score_threshold: Minimum similarity score
            use_rerank: Whether to use reranking

        Returns:
            Answer dictionary with sources
        """
        # Retrieve relevant documents
        docs = await self.retrieval.retrieve(
            query=query,
            user=user,
            top_k=top_k,
            score_threshold=score_threshold,
            use_rerank=use_rerank,
        )

        # Generate answer
        if docs:
            context = self._format_context(docs)
            answer = await self._generate_answer(query, context)
        else:
            answer = self.no_answer_prompt

        # Get or create conversation
        if conversation_id:
            result = await db.execute(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if not conversation:
                conversation = await self._create_conversation(db, user, query)
        else:
            conversation = await self._create_conversation(db, user, query)

        # Save messages
        await self._save_messages(
            db=db,
            conversation=conversation,
            query=query,
            answer=answer,
            docs=docs,
        )

        # Format sources with HTML content
        sources = await self._format_sources(db, docs)

        return {
            "answer": answer,
            "sources": sources,
            "conversation_id": str(conversation.id),
            "has_context": len(docs) > 0,
        }

    async def _generate_answer(
        self,
        query: str,
        context: str,
    ) -> str:
        """Generate answer using LLM.

        Args:
            query: User question
            context: Retrieved context

        Returns:
            Generated answer
        """
        messages = [
            {
                "role": "system",
                "content": self.system_prompt.format(context=context),
            },
            {
                "role": "user",
                "content": query,
            },
        ]

        response = await llm_service.acomplete(messages)
        return response or "抱歉，生成答案时出现问题。"

    def _format_context(self, docs: list[dict[str, Any]]) -> str:
        """Format retrieved documents into context.

        Args:
            docs: Retrieved documents

        Returns:
            Formatted context string
        """
        parts = []
        for i, doc in enumerate(docs, 1):
            parts.append(f"[文档 {i}]")
            parts.append(doc.get("content", ""))
        return "\n\n".join(parts)

    async def _format_sources(
        self,
        db: AsyncSession,
        docs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Format sources for response.

        Args:
            db: Database session
            docs: Retrieved documents

        Returns:
            Formatted sources list with HTML content
        """
        sources = []
        seen_docs = set()

        # Collect unique document IDs
        doc_ids = [doc.get("document_id") for doc in docs if doc.get("document_id")]
        doc_ids = list(set(doc_ids))

        # Batch query document metadata
        if doc_ids:
            result = await db.execute(
                select(Document).where(Document.id.in_(doc_ids))
            )
            documents_map = {str(doc.id): doc for doc in result.scalars().all()}

        for doc in docs:
            doc_id = doc.get("document_id")
            if doc_id and doc_id not in seen_docs:
                source_data = {
                    "document_id": doc_id,
                    "chunk_id": doc.get("chunk_id"),
                    "score": doc.get("score", 0),
                    "rerank_score": doc.get("rerank_score"),
                }

                # Add HTML content from document metadata if available
                if doc_id in documents_map:
                    document = documents_map[doc_id]
                    if document.doc_metadata:
                        source_data["title"] = document.title
                        # Get original HTML from metadata
                        original_html = document.doc_metadata.get("original_html", "")
                        if original_html:
                            source_data["html_content"] = original_html
                            source_data["has_images"] = document.doc_metadata.get("has_images", False)

                sources.append(source_data)
                seen_docs.add(doc_id)

        return sources

    async def _create_conversation(
        self,
        db: AsyncSession,
        user: User,
        first_message: str,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            db: Database session
            user: User creating conversation
            first_message: First message for title

        Returns:
            Created conversation
        """
        # Generate title from first message (max 50 chars)
        title = first_message[:50] + "..." if len(first_message) > 50 else first_message

        conversation = Conversation(
            user_id=user.id,
            title=title,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return conversation

    async def _save_messages(
        self,
        db: AsyncSession,
        conversation: Conversation,
        query: str,
        answer: str,
        docs: list[dict[str, Any]],
    ) -> None:
        """Save user and assistant messages.

        Args:
            db: Database session
            conversation: Conversation to save to
            query: User query
            answer: Assistant answer
            docs: Retrieved documents for sources
        """
        sources = await self._format_sources(db, docs)

        # User message
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=query,
        )
        db.add(user_msg)

        # Assistant message
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            sources=sources,
        )
        db.add(assistant_msg)

        await db.commit()

    async def get_conversation_history(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user: User,
    ) -> list[dict[str, Any]]:
        """Get conversation history.

        Args:
            db: Database session
            conversation_id: Conversation ID
            user: User requesting history

        Returns:
            List of messages
        """
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return []

        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "sources": msg.sources,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in conversation.messages
        ]

    async def list_conversations(
        self,
        db: AsyncSession,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List user's conversations.

        Args:
            db: Database session
            user: User to list conversations for
            limit: Maximum number to return
            offset: Pagination offset

        Returns:
            List of conversations
        """
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        conversations = result.scalars().all()

        return [
            {
                "id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
            for conv in conversations
        ]


# Global service instances
retrieval_service = RetrievalService()
qa_service = QAService()
