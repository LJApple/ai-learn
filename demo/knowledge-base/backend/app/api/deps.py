"""API dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from token.

    Args:
        credentials: HTTP bearer credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # TODO: Implement proper JWT verification
    # For now, accept any token and return a dummy user
    # In production, decode JWT and fetch user from DB

    # Placeholder: return first user (remove in production)
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()

    if not user:
        # Create default user for development
        user = User(
            username="admin",
            email="admin@example.com",
            is_superuser=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User | None:
    """Get current user if authenticated, otherwise None.

    Args:
        credentials: Optional HTTP bearer credentials
        db: Database session

    Returns:
        Current user or None
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
