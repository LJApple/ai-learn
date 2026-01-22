"""Knowledge base retrieval diagnostic script."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pymilvus import connections, utility, Collection
from app.core.config import settings
from app.services.llm import embedding_service


async def diagnose():
    """Run diagnostic checks."""
    print("=" * 60)
    print("KNOWLEDGE BASE RETRIEVAL DIAGNOSTIC")
    print("=" * 60)

    # 1. Configuration
    print("\n[1] CONFIGURATION")
    print(f"  MILVUS_HOST: {settings.MILVUS_HOST}")
    print(f"  MILVUS_PORT: {settings.MILVUS_PORT}")
    print(f"  MILVUS_COLLECTION_NAME: {settings.MILVUS_COLLECTION_NAME}")
    print(f"  MILVUS_DIMENSION: {settings.MILVUS_DIMENSION}")
    print(f"  EMBEDDING_MODEL: {settings.EMBEDDING_MODEL}")
    print(f"  EMBEDDING_DEVICE: {settings.EMBEDDING_DEVICE}")
    print(f"  SCORE_THRESHOLD: {settings.SCORE_THRESHOLD}")
    print(f"  TOP_K_RETRIEVAL: {settings.TOP_K_RETRIEVAL}")

    # Check actual embedding dimension
    try:
        actual_dim = embedding_service.dimension
        print(f"  ACTUAL EMBEDDING DIMENSION: {actual_dim}")
        if actual_dim != settings.MILVUS_DIMENSION:
            print(f"  ⚠️  WARNING: Dimension mismatch! Config={settings.MILVUS_DIMENSION}, Actual={actual_dim}")
    except Exception as e:
        print(f"  ⚠️  ERROR getting embedding dimension: {e}")

    # 2. Milvus Connection
    print("\n[2] MILVUS CONNECTION")
    try:
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        print("  ✓ Connected to Milvus successfully")
    except Exception as e:
        print(f"  ✗ FAILED to connect to Milvus: {e}")
        return

    # 3. Check Collections
    print("\n[3] MILVUS COLLECTIONS")
    try:
        all_collections = utility.list_collections()
        print(f"  All collections: {all_collections}")

        # Check if target collection exists
        target_collection = settings.MILVUS_COLLECTION_NAME
        if utility.has_collection(target_collection):
            print(f"  ✓ Target collection '{target_collection}' exists")

            collection = Collection(target_collection)
            collection.load()

            # Get collection info
            num_entities = collection.num_entities
            print(f"    - Number of entities: {num_entities}")

            if num_entities == 0:
                print(f"  ⚠️  WARNING: Collection is EMPTY! No documents indexed.")
            else:
                print(f"    - Sample query...")

                # Get schema
                schema = collection.schema
                print(f"    - Fields: {[f.name for f in schema.fields]}")

                # Try a simple search
                try:
                    test_query = "测试查询"
                    query_embedding = await embedding_service.aencode(test_query)
                    if isinstance(query_embedding, list) and len(query_embedding) > 0:
                        if isinstance(query_embedding[0], list):
                            query_embedding = query_embedding[0]

                    print(f"    - Query embedding dimension: {len(query_embedding)}")

                    results = collection.search(
                        data=[query_embedding],
                        anns_field="embedding",
                        param={"metric_type": "IP", "params": {"ef": 64}},
                        limit=5,
                        output_fields=["content", "document_id", "department_id", "permission_level"],
                    )

                    print(f"    - Search returned {len(results[0])} results")

                    for i, hit in enumerate(results[0]):
                        print(f"      [{i+1}] Score={hit.score:.4f}, Doc={hit.entity.get('document_id')}")
                        content_preview = hit.entity.get('content', '')[:50]
                        print(f"          Content: {content_preview}...")

                except Exception as e:
                    print(f"    ✗ Search failed: {e}")
                    import traceback
                    traceback.print_exc()

        else:
            print(f"  ✗ Target collection '{target_collection}' does NOT exist")
            print(f"  ⚠️  You need to create and index documents first!")

        # Check alternative collection names
        alt_names = ["knowledge_chunks", "knowledge_chunks_v2"]
        for alt_name in alt_names:
            if utility.has_collection(alt_name) and alt_name != target_collection:
                print(f"  ⚠️  Found alternative collection '{alt_name}' with data!")
                alt_collection = Collection(alt_name)
                alt_collection.load()
                print(f"    - Entities: {alt_collection.num_entities}")

    except Exception as e:
        print(f"  ✗ ERROR checking collections: {e}")
        import traceback
        traceback.print_exc()

    # 4. Test Embedding Service
    print("\n[4] EMBEDDING SERVICE TEST")
    try:
        test_text = "这是一段测试文本"
        embedding = await embedding_service.aencode(test_text)
        if isinstance(embedding, list) and len(embedding) > 0:
            if isinstance(embedding[0], list):
                embedding = embedding[0]
        print(f"  ✓ Embedding generated successfully")
        print(f"    - Dimension: {len(embedding)}")
        print(f"    - Sample values (first 3): {embedding[:3]}")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    # 5. Check permission filter logic
    print("\n[5] PERMISSION FILTER LOGIC")
    print("  Filter expression for non-superuser with department:")
    filters = {"public_or_department": True, "department_id": "test-dept-123"}
    conditions = []
    perm_conditions = ['permission_level == "public"']
    perm_conditions.append(f'(permission_level == "department" and department_id == "{filters["department_id"]}")')
    conditions.append(f"({' or '.join(perm_conditions)})")
    filter_expr = " and ".join(conditions)
    print(f"    Expression: {filter_expr}")

    # Cleanup
    connections.disconnect("default")

    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(diagnose())
