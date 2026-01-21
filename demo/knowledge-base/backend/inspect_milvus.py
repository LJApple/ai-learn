
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get backend directory (where this script is)
backend_dir = Path(__file__).parent.absolute()

# Add backend directory to sys.path so we can import app
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load .env file explicitly
env_path = backend_dir / ".env"
print(f"Loading .env from {env_path}")
load_dotenv(env_path)

from app.services.vector import milvus_service
from app.services.llm import embedding_service
import asyncio

async def inspect():
    print("Connecting to Milvus...")
    milvus_service.connect()
    
    print(f"Collection: {milvus_service.collection_name}")
    stats = milvus_service.get_stats()
    print(f"Stats: {stats}")
    
    query = "中建三局"
    print(f"\nGenerating embedding for query: '{query}'...")
    embedding = await embedding_service.aencode(query)
    if isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], list):
        embedding = embedding[0]
        
    print(f"Embedding vector length: {len(embedding)}")
    
    # 1. Search with NO filters
    print("\n1. Searching with NO filters:")
    results = milvus_service.search(
        embedding=embedding,
        top_k=5
    )
    
    if not results:
        print("No results found.")
    else:
        for i, res in enumerate(results):
            print(f"[{i+1}] Score: {res['score']:.4f}, DocID: {res['document_id']}, Content: {res['content'][:50]}...")

    # 2. Search with Public Filter (simulating user with no department)
    print("\n2. Searching with Public Filter (permission_level == 'public'):")
    filters = {"public_or_department": True}
    results_filtered = milvus_service.search(
        embedding=embedding,
        top_k=5,
        filters=filters
    )
    
    if not results_filtered:
        print("No results found with filter.")
    else:
        for i, res in enumerate(results_filtered):
            print(f"[{i+1}] Score: {res['score']:.4f}, DocID: {res['document_id']}, Content: {res['content'][:50]}...")

if __name__ == "__main__":
    asyncio.run(inspect())
