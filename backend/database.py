import os
import functools
from pathlib import Path
import chromadb
from dotenv import load_dotenv

# Determine environment paths
script_dir = Path(__file__).resolve().parent
env_path_local = script_dir.parent / ".env.local"
env_path_main = script_dir.parent / ".env"

# Load Environment
if env_path_local.exists():
    load_dotenv(dotenv_path=env_path_local)
elif env_path_main.exists():
    load_dotenv(dotenv_path=env_path_main)
else:
    load_dotenv()

# Database Configuration
DB_DIR = script_dir / "chroma_db"


@functools.lru_cache()
def get_chroma_client():
    return chromadb.PersistentClient(path=str(DB_DIR))


def get_collection():
    client = get_chroma_client()
    # Use get_or_create to ensure resilience
    return client.get_or_create_collection(
        name="gov_knowledge_base", embedding_function=None
    )
