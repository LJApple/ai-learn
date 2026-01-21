"""Chat API endpoints."""

from datetime import datetime
import uuid

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DBSession
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest
from app.services.retrieval import qa_service

router = APIRouter()


@router.post("/completions", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Generate chat completion using RAG.

    Args:
        request: Chat request with query and parameters
        current_user: Authenticated user
        db: Database session

    Returns:
        Chat response with answer and sources
    """
    result = await qa_service.ask(
        db=db,
        query=request.query,
        user=current_user,
        conversation_id=request.conversation_id,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
        use_rerank=request.use_rerank,
    )

    return ChatResponse(
        id=uuid.uuid4(),
        answer=result["answer"],
        sources=result["sources"],
        conversation_id=result["conversation_id"],
        has_context=result["has_context"],
        created_at=datetime.now(),
    )


@router.post("/{message_id}/feedback")
async def submit_feedback(
    message_id: uuid.UUID,
    request: FeedbackRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Submit feedback for a message.

    Args:
        message_id: Message ID to give feedback on
        request: Feedback request with rating
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    # TODO: Implement feedback storage
    return {"message": "Feedback received", "message_id": str(message_id)}


@router.get("/stream")
async def chat_stream():
    """Stream chat completion (SSE endpoint).

    This would implement Server-Sent Events for streaming responses.
    TODO: Implement streaming endpoint
    """
    return {"message": "Streaming not yet implemented"}
