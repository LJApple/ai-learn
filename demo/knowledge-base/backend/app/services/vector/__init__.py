"""Vector database service."""

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.core.config import settings


class MilvusService:
    """Milvus vector database service."""

    def __init__(self) -> None:
        """Initialize Milvus service."""
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dimension = settings.MILVUS_DIMENSION
        self._collection: Collection | None = None

    def connect(self) -> None:
        """Connect to Milvus."""
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port,
        )

    def disconnect(self) -> None:
        """Disconnect from Milvus."""
        connections.disconnect("default")

    @property
    def collection(self) -> Collection:
        """Get or create collection."""
        if self._collection is None:
            if not utility.has_collection(self.collection_name):
                self._create_collection()
            self._collection = Collection(self.collection_name)
        return self._collection

    def _create_collection(self) -> None:
        """Create collection with schema."""
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                max_length=36,
                is_primary=True,
                description="Chunk ID",
            ),
            FieldSchema(
                name="document_id",
                dtype=DataType.VARCHAR,
                max_length=36,
                description="Document ID",
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Chunk content",
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dimension,
                description="Content embedding",
            ),
            FieldSchema(
                name="department_id",
                dtype=DataType.VARCHAR,
                max_length=36,
                description="Department ID for permission filtering",
            ),
            FieldSchema(
                name="permission_level",
                dtype=DataType.VARCHAR,
                max_length=20,
                description="Permission level: public, department, private",
            ),
            FieldSchema(
                name="owner_id",
                dtype=DataType.VARCHAR,
                max_length=36,
                description="Owner user ID",
            ),
            FieldSchema(
                name="chunk_index",
                dtype=DataType.INT64,
                description="Chunk index in document",
            ),
            FieldSchema(
                name="created_at",
                dtype=DataType.INT64,
                description="Creation timestamp",
            ),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Knowledge base document chunks",
            enable_dynamic_field=True,
        )

        collection = Collection(
            name=self.collection_name,
            schema=schema,
        )

        # Create index on embedding field
        index_params = {
            "index_type": "HNSW",  # Hierarchical Navigable Small World
            "metric_type": "IP",  # Inner Product
            "params": {
                "M": 16,  # Maximum number of outgoing edges in node
                "efConstruction": 256,  # Depth of search during construction
            },
        }

        collection.create_index(
            field_name="embedding",
            index_params=index_params,
        )

        # Create index on filter fields
        collection.create_index(
            field_name="document_id",
            index_params={"index_type": "INVERTED"},
        )
        collection.create_index(
            field_name="department_id",
            index_params={"index_type": "INVERTED"},
        )
        collection.create_index(
            field_name="permission_level",
            index_params={"index_type": "INVERTED"},
        )

    def insert_chunks(
        self,
        chunks: list[dict],
    ) -> list[str]:
        """Insert chunks into vector database.

        Args:
            chunks: List of chunk dictionaries containing:
                - id: str
                - document_id: str
                - content: str
                - embedding: list[float]
                - department_id: str | None
                - permission_level: str
                - owner_id: str
                - chunk_index: int
                - created_at: int

        Returns:
            List of inserted chunk IDs
        """
        data = [
            [c["id"] for c in chunks],
            [c["document_id"] for c in chunks],
            [c["content"] for c in chunks],
            [c["embedding"] for c in chunks],
            [c.get("department_id", "") for c in chunks],
            [c.get("permission_level", "department") for c in chunks],
            [c.get("owner_id", "") for c in chunks],
            [c.get("chunk_index", 0) for c in chunks],
            [c.get("created_at", 0) for c in chunks],
        ]

        self.collection.insert(data)
        return [c["id"] for c in chunks]

    def search(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search for similar chunks.

        Args:
            embedding: Query vector embedding
            top_k: Number of results to return
            filters: Optional filters for search:
                - document_ids: list[str]
                - department_id: str
                - permission_level: str
                - owner_id: str

        Returns:
            List of search results with scores
        """
        # Load collection before search
        self.collection.load()

        # Build filter expression
        filter_expr = self._build_filter_expr(filters) if filters else None

        # Search parameters
        search_params = {
            "metric_type": "IP",
            "params": {"ef": 64},  # Search depth
        }

        results = self.collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=[
                "document_id",
                "content",
                "department_id",
                "permission_level",
                "owner_id",
                "chunk_index",
            ],
        )

        # Format results
        formatted_results = []
        for hit in results[0]:
            formatted_results.append(
                {
                    "chunk_id": hit.id,
                    "score": float(hit.score),
                    "document_id": hit.entity.get("document_id"),
                    "content": hit.entity.get("content"),
                    "department_id": hit.entity.get("department_id"),
                    "permission_level": hit.entity.get("permission_level"),
                    "owner_id": hit.entity.get("owner_id"),
                    "chunk_index": hit.entity.get("chunk_index"),
                }
            )

        return formatted_results

    def _build_filter_expr(self, filters: dict) -> str | None:
        """Build filter expression from filters dict.

        Args:
            filters: Dictionary of filter conditions

        Returns:
            Filter expression string or None
        """
        conditions = []

        if "document_ids" in filters:
            doc_ids = ", ".join(f'"{did}"' for did in filters["document_ids"])
            conditions.append(f"document_id in [{doc_ids}]")

        if "owner_id" in filters:
            conditions.append(f'owner_id == "{filters["owner_id"]}"')

        # Handle permission filtering
        if "public_or_department" in filters and filters["public_or_department"]:
            # Special case: Allow public documents OR department documents for the specific department
            # This handles the case where public documents have empty department_id
            perm_conditions = ['permission_level == "public"']
            
            if "department_id" in filters:
                dept_id = filters["department_id"]
                perm_conditions.append(f'(permission_level == "department" and department_id == "{dept_id}")')
            
            conditions.append(f"({' or '.join(perm_conditions)})")
            
        else:
            # Standard filtering
            if "department_id" in filters:
                conditions.append(f'department_id == "{filters["department_id"]}"')

            if "permission_level" in filters:
                perm = filters["permission_level"]
                conditions.append(f'permission_level == "{perm}"')

        return " and ".join(conditions) if conditions else None

    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID to delete

        Returns:
            Number of deleted chunks
        """
        self.collection.delete(
            expr=f'document_id == "{document_id}"'
        )
        # Note: Milvus doesn't return delete count easily
        return 0

    def flush(self) -> None:
        """Flush pending operations."""
        self.collection.flush()

    def get_stats(self) -> dict:
        """Get collection statistics.

        Returns:
            Dictionary with stats
        """
        self.collection.load()
        return {
            "name": self.collection_name,
            "count": self.collection.num_entities,
            "dimension": self.dimension,
        }


# Global service instance
milvus_service = MilvusService()
