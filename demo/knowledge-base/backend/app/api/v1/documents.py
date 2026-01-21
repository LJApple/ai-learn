"""Document API endpoints."""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.models.document import Document, SourceType, DocumentStatus
from app.schemas.common import PaginationParams, PaginatedResponse
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
)
from app.services.ingestion import document_indexer

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    source_type: Annotated[str, Form()],
    current_user: CurrentUser,
    db: DBSession,
    permission_level: Annotated[str, Form()] = "department",
):
    """Upload a document to the knowledge base.

    Args:
        file: Uploaded file
        title: Document title
        source_type: Type of document (pdf, word, etc.)
        permission_level: Access permission level
        current_user: Authenticated user
        db: Database session

    Returns:
        Upload response with document ID
    """
    # Validate source type
    try:
        doc_source_type = SourceType(source_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_type: {source_type}",
        )

    # Create storage directory
    storage_path = Path(settings.STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)

    # Save file
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    file_path = storage_path / f"{file_id}{file_extension}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create document record
    document = Document(
        title=title,
        source_type=doc_source_type,
        file_path=str(file_path),
        file_size=len(content),
        permission_level=permission_level,
        owner_id=current_user.id,
        department_id=current_user.department_id,
        status=DocumentStatus.PENDING,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Trigger indexing asynchronously
    # In production, use background tasks or message queue
    try:
        await document_indexer.index_document(db, document.id)
    except Exception as e:
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        await db.commit()

    return DocumentUploadResponse(
        document_id=document.id,
        status=document.status,
        message="Document uploaded and processing",
    )


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    current_user: CurrentUser,
    db: DBSession,
    pagination: PaginationParams = Depends(),
):
    """List documents accessible to the user.

    Args:
        pagination: Pagination parameters
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of documents
    """
    # Build query with permission filtering
    query = select(Document)

    if not current_user.is_superuser:
        # Public documents or user's own department
        query = query.where(
            (Document.permission_level == "public")
            | (Document.department_id == current_user.department_id)
            | (Document.owner_id == current_user.id)
        )

    # Order by updated date
    query = query.order_by(Document.updated_at.desc())

    # Get total count
    count_result = await db.execute(select(Document.id).where(query.whereclause))  # type: ignore
    total = len(count_result.all())

    # Get paginated results
    result = await db.execute(
        query.offset(pagination.offset).limit(pagination.limit)
    )
    documents = result.scalars().all()

    items = [DocumentResponse.model_validate(doc) for doc in documents]

    return PaginatedResponse.create(items, total, pagination)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get a document by ID.

    Args:
        document_id: Document ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Document details
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check permission
    if not document.is_accessible_by(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document",
        )

    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Delete a document.

    Args:
        document_id: Document ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check permission (only owner or superuser can delete)
    if document.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only document owner can delete",
        )

    # Delete from vector DB
    await document_indexer.delete_document(db, document_id)

    # Delete file
    if document.file_path:
        try:
            Path(document.file_path).unlink(missing_ok=True)
        except Exception:
            pass

    # Delete from database
    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Re-index a document.

    Args:
        document_id: Document ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Re-indexing result
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    result = await document_indexer.reindex_document(db, document_id)

    return result
