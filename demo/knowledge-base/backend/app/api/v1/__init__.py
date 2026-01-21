"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import chat, documents, conversations

router = APIRouter()

router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
