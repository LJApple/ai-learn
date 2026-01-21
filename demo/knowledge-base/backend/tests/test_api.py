"""API endpoint tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.config import settings


# Test database URL (use separate test DB)
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/knowledge_base",
    "/knowledge_base_test"
)

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
async def db_session():
    """Create a test database session."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client():
    """Create a test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


class TestHealth:
    """Health check endpoint tests."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestChat:
    """Chat API tests."""

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client: AsyncClient):
        """Test that chat requires authentication."""
        response = await client.post(
            "/api/v1/chat/completions",
            json={"query": "test query"}
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403]


class TestDocuments:
    """Document API tests."""

    @pytest.mark.asyncio
    async def test_list_documents_requires_auth(self, client: AsyncClient):
        """Test that listing documents requires authentication."""
        response = await client.get("/api/v1/documents")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403]


class TestConversations:
    """Conversation API tests."""

    @pytest.mark.asyncio
    async def test_list_conversations_requires_auth(self, client: AsyncClient):
        """Test that listing conversations requires authentication."""
        response = await client.get("/api/v1/conversations")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403]
