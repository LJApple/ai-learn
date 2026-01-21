"""Document ingestion service - parsing, chunking, and indexing."""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, SourceType
from app.services.llm import embedding_service
from app.services.vector import milvus_service


class ParserType(str, Enum):
    """Supported document parser types."""

    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


class DocumentParser:
    """Document parser for various file types."""

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """Parse PDF document.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            text_parts = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    print(f"Error extracting text from page {i+1} of {file_path}: {e}")
                    # Skip problematic page
                    continue
            return "\n\n".join(text_parts)
        except ImportError:
            raise ImportError("pypdf is required for PDF parsing")

    @staticmethod
    def parse_word(file_path: str) -> str:
        """Parse Word document.

        Args:
            file_path: Path to Word file

        Returns:
            Extracted text content
        """
        try:
            from docx import Document

            doc = Document(file_path)
            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text_parts.append(paragraph.text)
            return "\n\n".join(text_parts)
        except ImportError:
            raise ImportError("python-docx is required for Word parsing")

    @staticmethod
    def parse_markdown(file_path: str) -> str:
        """Parse Markdown document.

        Args:
            file_path: Path to Markdown file

        Returns:
            File content as string
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def parse_text(file_path: str) -> str:
        """Parse plain text document.

        Args:
            file_path: Path to text file

        Returns:
            File content as string
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def parse_html(file_path: str) -> str:
        """Parse HTML document.

        Args:
            file_path: Path to HTML file

        Returns:
            Extracted text content
        """
        try:
            from bs4 import BeautifulSoup

            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                return soup.get_text(separator="\n\n", strip=True)
        except ImportError:
            raise ImportError("beautifulsoup4 is required for HTML parsing")

    @classmethod
    def parse(cls, file_path: str, source_type: SourceType) -> str:
        """Parse document based on source type.

        Args:
            file_path: Path to document
            source_type: Type of document

        Returns:
            Extracted text content
        """
        parser_map = {
            SourceType.PDF: cls.parse_pdf,
            SourceType.WORD: cls.parse_word,
            SourceType.MARKDOWN: cls.parse_markdown,
            SourceType.TEXT: cls.parse_text,
            SourceType.HTML: cls.parse_html,
        }

        parser = parser_map.get(source_type)
        if not parser:
            raise ValueError(f"Unsupported source type: {source_type}")

        return parser(file_path)


class TextChunker:
    """Text chunking service."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        """Initialize chunker.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # Main text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n## ",  # Headers
                "\n\n### ",
                "\n\n#### ",
                "\n\n",  # Paragraphs
                "\n",  # Lines
                ". ",  # Sentences
                " ",  # Words
                "",
            ],
        )

        # Markdown-specific splitter
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                ("####", "Header 4"),
            ]
        )

    def chunk(
        self,
        text: str,
        source_type: SourceType = SourceType.TEXT,
        metadata: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Split text into chunks.

        Args:
            text: Input text
            source_type: Source type of text
            metadata: Optional metadata to include

        Returns:
            List of chunks with metadata
        """
        if not text or not text.strip():
            return []

        chunks = []

        # For markdown, use markdown splitter first
        if source_type == SourceType.MARKDOWN:
            md_chunks = self.markdown_splitter.split_text(text)
            for md_chunk in md_chunks:
                sub_chunks = self.splitter.split_documents([md_chunk])
                for i, sub_chunk in enumerate(sub_chunks):
                    chunks.append(
                        {
                            "content": sub_chunk.page_content,
                            "metadata": {
                                **(metadata or {}),
                                **sub_chunk.metadata,
                                "chunk_index": i,
                            },
                        }
                    )
        else:
            # Use recursive splitter
            split_chunks = self.splitter.split_text(text)
            for i, chunk_text in enumerate(split_chunks):
                chunks.append(
                    {
                        "content": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": i,
                        },
                    }
                )

        return chunks


class DocumentIndexer:
    """Document indexing service."""

    def __init__(self) -> None:
        """Initialize indexer."""
        self.parser = DocumentParser()
        self.chunker = TextChunker()

    async def index_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Index a document into vector database.

        Args:
            db: Database session
            document_id: Document ID to index

        Returns:
            Indexing result with stats
        """
        # Get document
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document not found: {document_id}")

        if not document.file_path:
            raise ValueError(f"Document has no file path: {document_id}")

        # Parse document
        try:
            text = self.parser.parse(document.file_path, document.source_type)
        except Exception as e:
            document.status = "failed"
            document.error_message = str(e)
            await db.commit()
            raise

        # Chunk text
        chunks = self.chunker.chunk(
            text,
            document.source_type,
            metadata={
                "document_id": str(document_id),
                "title": document.title,
                "source_type": document.source_type.value,
            },
        )

        if not chunks:
            document.status = "indexed"
            document.chunk_count = 0
            await db.commit()
            return {
                "document_id": str(document_id),
                "chunk_count": 0,
                "status": "indexed",
            }

        # Generate embeddings
        texts = [chunk["content"] for chunk in chunks]
        embeddings = await embedding_service.aencode(texts)

        # Prepare vector DB data
        vector_chunks = []
        now = int(datetime.now().timestamp())

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            vector_chunks.append(
                {
                    "id": chunk_id,
                    "document_id": str(document_id),
                    "content": chunk["content"],
                    "embedding": embedding,
                    "department_id": str(document.department_id) if document.department_id else "",
                    "permission_level": document.permission_level.value,
                    "owner_id": str(document.owner_id) if document.owner_id else "",
                    "chunk_index": chunk["metadata"].get("chunk_index", i),
                    "created_at": now,
                }
            )

        # Insert into vector DB
        milvus_service.connect()
        try:
            milvus_service.insert_chunks(vector_chunks)
            milvus_service.flush()
        finally:
            milvus_service.disconnect()

        # Update document
        document.status = "indexed"
        document.chunk_count = len(chunks)
        document.indexed_at = datetime.now()

        await db.commit()

        return {
            "document_id": str(document_id),
            "chunk_count": len(chunks),
            "status": "indexed",
        }

    async def delete_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> None:
        """Delete document from vector database.

        Args:
            db: Database session
            document_id: Document ID to delete
        """
        milvus_service.connect()
        try:
            milvus_service.delete_by_document(str(document_id))
            milvus_service.flush()
        finally:
            milvus_service.disconnect()

    async def reindex_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Re-index a document (delete and re-insert).

        Args:
            db: Database session
            document_id: Document ID to re-index

        Returns:
            Indexing result
        """
        await self.delete_document(db, document_id)
        return await self.index_document(db, document_id)


# Global service instance
document_indexer = DocumentIndexer()
