"""Document related schemas."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Document source types."""

    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class PermissionLevel(str, Enum):
    """Document permission levels."""

    PUBLIC = "public"
    DEPARTMENT = "department"
    PRIVATE = "private"


class DocumentCreate(BaseModel):
    """Document creation schema."""

    title: str = Field(..., min_length=1, max_length=500)
    source_type: SourceType
    source_url: str | None = None
    permission_level: PermissionLevel = PermissionLevel.DEPARTMENT


class DocumentUpdate(BaseModel):
    """Document update schema."""

    title: str | None = Field(None, min_length=1, max_length=500)
    permission_level: PermissionLevel | None = None


class DocumentResponse(BaseModel):
    """Document response schema."""

    id: uuid.UUID
    title: str
    source_type: SourceType
    source_url: str | None
    permission_level: PermissionLevel
    status: DocumentStatus
    chunk_count: int
    owner_id: uuid.UUID | None
    department_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Document upload response schema."""

    document_id: uuid.UUID
    status: DocumentStatus
    message: str
