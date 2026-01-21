"""Chat related schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    """Source information for RAG."""

    document_id: str
    chunk_id: str | None = None
    score: float
    rerank_score: float | None = None


class ChatRequest(BaseModel):
    """Chat request schema."""

    query: str = Field(..., min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None
    top_k: int | None = Field(None, ge=1, le=50)
    score_threshold: float | None = Field(None, ge=0, le=1)
    use_rerank: bool = True


class ChatResponse(BaseModel):
    """Chat response schema."""

    id: uuid.UUID
    answer: str
    sources: list[SourceInfo]
    conversation_id: str
    has_context: bool
    created_at: datetime


class ConversationCreate(BaseModel):
    """Conversation creation schema."""

    title: str | None = Field(None, max_length=200)


class ConversationResponse(BaseModel):
    """Conversation response schema."""

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Message response schema."""

    id: uuid.UUID
    role: str
    content: str
    sources: list[SourceInfo] | None
    created_at: datetime


class FeedbackRequest(BaseModel):
    """Feedback request schema."""

    feedback: int = Field(..., ge=-1, le=1)  # -1: thumbs down, 0: neutral, 1: thumbs up
