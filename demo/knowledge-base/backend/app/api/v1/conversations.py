"""Conversation API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DBSession
from app.schemas.chat import ConversationResponse, MessageResponse
from app.services.retrieval import qa_service

router = APIRouter()


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = 20,
    offset: int = 0,
):
    """List user's conversations.

    Args:
        current_user: Authenticated user
        db: Database session
        limit: Maximum number to return
        offset: Pagination offset

    Returns:
        List of conversations
    """
    conversations = await qa_service.list_conversations(
        db=db,
        user=current_user,
        limit=limit,
        offset=offset,
    )

    return [ConversationResponse(**conv) for conv in conversations]


@router.get("/{conversation_id}", response_model=list[MessageResponse])
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get conversation messages.

    Args:
        conversation_id: Conversation ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of messages
    """
    messages = await qa_service.get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        user=current_user,
    )

    return [MessageResponse(**msg) for msg in messages]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Delete a conversation.

    Args:
        conversation_id: Conversation ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    from app.models.conversation import Conversation
    from sqlalchemy import select

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    await db.delete(conversation)
    await db.commit()

    return {"message": "Conversation deleted"}
