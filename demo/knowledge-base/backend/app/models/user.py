"""User related models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import Document, DocumentPermission
    from app.models.conversation import Conversation, Message
    from app.models.audit import AuditLog


class Role(Base, UUIDMixin, TimestampMixin):
    """Role model."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "UserRole", back_populates="role", lazy="selectin"
    )


class User(Base, UUIDMixin, TimestampMixin):
    """User model."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "UserRole", back_populates="user", lazy="selectin"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="owner", lazy="selectin"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", lazy="selectin"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="selectin"
    )

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role.

        Args:
            role_name: Name of the role to check

        Returns:
            bool: True if user has the role
        """
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: Permission string to check

        Returns:
            bool: True if user has the permission
        """
        if self.is_superuser:
            return True
        # Check roles for permission
        for role in self.roles:
            if hasattr(role, "permissions") and permission in role.permissions:
                return True
        return False


class UserRole(Base, TimestampMixin):
    """User-Role association table."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="roles", lazy="selectin"
    )
    role: Mapped["Role"] = relationship(
        "Role", back_populates="users", lazy="selectin"
    )
