import chromadb
from pathlib import Path
import sys

# Setup paths
script_dir = Path("backend").resolve()
db_dir = script_dir / "chroma_db"

print(f"Checking ChromaDB at: {db_dir}")

try:
    client = chromadb.PersistentClient(path=str(db_dir))
    coll = client.get_collection("gov_knowledge_base")
    
    target_keyword = "C-4"
    
    # Simplified dictionary construction
    query_filter = {"$contains": target_keyword}
    
    keyword_results = coll.get(
        where_document=query_filter,
        limit=5
    )
    print(f"Found {len(keyword_results['ids'])} documents containing '{target_keyword}'")

except Exception as e:
    print(f"Error: {e}")
