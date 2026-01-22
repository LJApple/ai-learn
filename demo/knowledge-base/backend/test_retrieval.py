"""Test retrieval from inside backend container."""
import asyncio
import os
import sys

# Ensure we're in the right directory
os.chdir('/app')
sys.path.insert(0, '/app')

from pymilvus import connections, utility, Collection
from app.core.config import settings
from app.services.llm import embedding_service


async def main():
    print("=" * 60)
    print("RETRIEVAL TEST FROM CONTAINER")
    print("=" * 60)

    # 1. Config
    print(f"\n[CONFIG]")
    print(f"  Collection: {settings.MILVUS_COLLECTION_NAME}")
    print(f"  Host: {settings.MILVUS_HOST}")
    print(f"  Threshold: {settings.SCORE_THRESHOLD}")
    print(f"  Embedding Model: {settings.EMBEDDING_MODEL}")

    # 2. Test Milvus connection
    print(f"\n[MILVUS CONNECTION]")
    try:
        connections.connect(alias='default', host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
        print("  Connected OK")
    except Exception as e:
        print(f"  FAILED: {e}")
        return

    # 3. Check collection
    print(f"\n[COLLECTION CHECK]")
    if not utility.has_collection(settings.MILVUS_COLLECTION_NAME):
        print(f"  Collection '{settings.MILVUS_COLLECTION_NAME}' does NOT exist!")
        return

    collection = Collection(settings.MILVUS_COLLECTION_NAME)
    collection.load()
    print(f"  Collection exists with {collection.num_entities} entities")

    if collection.num_entities == 0:
        print("  ERROR: Collection is EMPTY!")
        return

    # 4. Test embedding
    print(f"\n[EMBEDDING TEST]")
    try:
        query = "公司有什么福利"
        embedding = await embedding_service.aencode(query)
        if isinstance(embedding, list) and len(embedding) > 0:
            if isinstance(embedding[0], list):
                embedding = embedding[0]
        print(f"  Query: {query}")
        print(f"  Embedding dimension: {len(embedding)}")
        print(f"  Expected dimension: {settings.MILVUS_DIMENSION}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Test search without filter
    print(f"\n[SEARCH TEST - NO FILTER]")
    try:
        results = collection.search(
            data=[embedding],
            anns_field='embedding',
            param={'metric_type': 'IP', 'params': {'ef': 64}},
            limit=10,
            expr=None,  # No filter
            output_fields=['document_id', 'content', 'permission_level', 'department_id'],
        )
        print(f"  Returned {len(results[0])} results")
        for i, hit in enumerate(results[0][:3]):
            print(f"    [{i+1}] Score={hit.score:.4f}, Perm={hit.entity.get('permission_level')}")
            print(f"        Content: {hit.entity.get('content', '')[:50]}...")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # 6. Test search with permission filter
    print(f"\n[SEARCH TEST - WITH PERMISSION FILTER]")
    try:
        filter_expr = '(permission_level == "public")'
        print(f"  Filter: {filter_expr}")
        results = collection.search(
            data=[embedding],
            anns_field='embedding',
            param={'metric_type': 'IP', 'params': {'ef': 64}},
            limit=10,
            expr=filter_expr,
            output_fields=['document_id', 'content', 'permission_level', 'department_id'],
        )
        print(f"  Returned {len(results[0])} results")
        for i, hit in enumerate(results[0][:3]):
            print(f"    [{i+1}] Score={hit.score:.4f}, Perm={hit.entity.get('permission_level')}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()

    # 7. Apply score threshold
    print(f"\n[SCORE THRESHOLD TEST]")
    print(f"  Threshold: {settings.SCORE_THRESHOLD}")
    passed = [r for r in results[0] if r.score >= settings.SCORE_THRESHOLD]
    print(f"  Results before threshold: {len(results[0])}")
    print(f"  Results after threshold: {len(passed)}")

    connections.disconnect('default')


if __name__ == "__main__":
    asyncio.run(main())
