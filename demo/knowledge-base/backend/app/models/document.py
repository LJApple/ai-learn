"""Document related models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, Text, Enum as SQLEnum, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.conversation import Message


class SourceType(str, Enum):
    """Document source types."""

    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"
    WIKI = "wiki"
    CONFLUENCE = "confluence"
    NOTION = "notion"
    WEB = "web"


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


class Document(Base, UUIDMixin, TimestampMixin):
    """Document model."""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[SourceType] = mapped_column(
        SQLEnum(SourceType), nullable=False, index=True
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    permission_level: Mapped[PermissionLevel] = mapped_column(
        SQLEnum(PermissionLevel),
        default=PermissionLevel.DEPARTMENT,
        nullable=False,
        index=True,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Indexes
    __table_args__ = (
        Index("ix_documents_owner_permission", "owner_id", "permission_level"),
        Index("ix_documents_department_permission", "department_id", "permission_level"),
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User", back_populates="documents", lazy="selectin"
    )
    permissions: Mapped[list["DocumentPermission"]] = relationship(
        "DocumentPermission",
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def is_accessible_by(self, user: "User") -> bool:
        """Check if document is accessible by user.

        Args:
            user: User to check access for

        Returns:
            bool: True if user can access this document
        """
        # Superuser can access everything
        if user.is_superuser:
            return True

        # Owner can access
        if self.owner_id == user.id:
            return True

        # Public documents
        if self.permission_level == PermissionLevel.PUBLIC:
            return True

        # Department level
        if (
            self.permission_level == PermissionLevel.DEPARTMENT
            and self.department_id
            and self.department_id == user.department_id
        ):
            return True

        # Check explicit permissions
        for perm in self.permissions:
            if perm.user_id == user.id:
                return True
            # Check role-based permissions
            if perm.role_id and user.has_role_id(perm.role_id):
                return True

        return False


class DocumentPermission(Base, UUIDMixin, TimestampMixin):
    """Document permission model for explicit access control."""

    __tablename__ = "document_permissions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    permission_type: Mapped[str] = mapped_column(
        String(20), default="read", nullable=False
    )  # read, write, admin

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="permissions", lazy="selectin"
    )
