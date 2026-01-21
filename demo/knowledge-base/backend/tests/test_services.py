"""Service layer tests."""

import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestEmbeddingService:
    """Embedding service tests."""

    @pytest.mark.asyncio
    async def test_encode_single_text(self):
        """Test encoding a single text."""
        with patch('app.services.llm.SentenceTransformer') as mock_model:
            from app.services.llm import EmbeddingService

            # Mock the model
            mock_instance = Mock()
            mock_instance.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_model.return_value = mock_instance

            service = EmbeddingService()
            result = service.encode("test text")

            assert isinstance(result, list)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_encode_multiple_texts(self):
        """Test encoding multiple texts."""
        with patch('app.services.llm.SentenceTransformer') as mock_model:
            from app.services.llm import EmbeddingService

            mock_instance = Mock()
            mock_instance.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            mock_model.return_value = mock_instance

            service = EmbeddingService()
            result = service.encode(["text1", "text2"])

            assert isinstance(result, list)
            assert len(result) == 2


class TestTextChunker:
    """Text chunker tests."""

    def test_chunk_empty_text(self):
        """Test chunking empty text returns empty list."""
        from app.services.ingestion import TextChunker
        from app.models.document import SourceType

        chunker = TextChunker()
        result = chunker.chunk("", SourceType.TEXT)

        assert result == []

    def test_chunk_text_returns_chunks(self):
        """Test that chunking text returns chunks."""
        from app.services.ingestion import TextChunker
        from app.models.document import SourceType

        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "This is a test. " * 20  # Create longer text

        result = chunker.chunk(text, SourceType.TEXT)

        assert len(result) > 0
        assert "content" in result[0]
        assert "metadata" in result[0]


class TestDocumentParser:
    """Document parser tests."""

    def test_parse_text_file(self, tmp_path):
        """Test parsing a text file."""
        from app.services.ingestion import DocumentParser
        from app.models.document import SourceType

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is test content")

        result = DocumentParser.parse(str(test_file), SourceType.TEXT)

        assert result == "This is test content"

    def test_parse_markdown_file(self, tmp_path):
        """Test parsing a markdown file."""
        from app.services.ingestion import DocumentParser
        from app.models.document import SourceType

        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Title\n\nThis is content")

        result = DocumentParser.parse(str(test_file), SourceType.MARKDOWN)

        assert "# Title" in result
        assert "This is content" in result
