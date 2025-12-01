import os
import sys
import logging
import chromadb
import json
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup
script_dir = Path(__file__).resolve().parent
load_dotenv(dotenv_path=script_dir.parent / ".env.local")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
LLM_MODEL = os.getenv("LLM_REASONING_MODEL", "gemini-2.5-flash")
model = genai.GenerativeModel(LLM_MODEL)

# Initialize Chroma
DB_DIR = script_dir / "chroma_db"
client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_or_create_collection(
    name="gov_knowledge_base", embedding_function=None
)


def extract_relationships(text: str, source_id: str) -> List[Dict]:
    prompt = f"""Analyze this legal text and extract relationships to OTHER documents, acts, or entities.
    
    Text: "{text[:4000]}"
    
    Return JSON list of relationships. 
    Format: {{"source": "{source_id}", "target": "Target Entity Name", "type": "AMENDS" | "CITES" | "DEFINES" | "REPEALS" | "RELATED_TO"}}
    
    Rules:
    - Target must be a specific Act, Bill, or Regulation (e.g. "Criminal Code", "Bill C-13").
    - Ignore generic references like "this Act".
    - If no relationships, return [].
    
    Output JSON only:"""

    try:
        response = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        logger.warning(f"Extraction failed for {source_id}: {e}")
        return []


def build_graph():
    logger.info("Scanning knowledge base for relationships...")

    # Fetch all documents (limit to 300 for better coverage)
    results = collection.get(limit=300, include=["documents", "metadatas"])

    nodes = {}
    links = []

    if not results["ids"]:
        logger.warning("No documents found in ChromaDB.")
        return

    ids = results["ids"]
    docs = results["documents"]
    metas = results["metadatas"]

    logger.info(f"Analyzing {len(ids)} documents...")

    for i, doc_id in enumerate(tqdm(ids)):
        content = docs[i]
        meta = metas[i]

        # 1. Add Node (Source)
        source_label = meta.get("source_title", doc_id)

        # Heuristic: Improve label for CSV rows identified by "-row-" in their ID
        if "-row-" in doc_id and "|" in content:
            # Ingest.py formats CSV rows as "Title | Question | Response..."
            potential_title = content.split("|")[0].strip()
            if (
                len(potential_title) > 3 and len(potential_title) < 100
            ):  # Ensure it's a meaningful title
                tqdm.write(
                    f"Changing label for {doc_id} from '{source_label}' to '{potential_title}'"
                )
                source_label = potential_title

        if doc_id not in nodes:
            nodes[doc_id] = {
                "id": doc_id,
                "label": source_label,
                "type": meta.get("category", "Document"),
                "group": 1,
            }

        # 2. Extract Relationships (LLM)
        # Heuristic: Only extract if content mentions "Act", "Code", "Bill" to save tokens
        if any(k in content for k in ["Act", "Code", "Bill", "Loi"]):
            rels = extract_relationships(content, source_label)

            for rel in rels:
                target = rel.get("target")
                rel_type = rel.get("type")

                if target and target != source_label:
                    # Add Target Node (if new)
                    target_id = target.replace(" ", "_").lower()  # Simple ID gen
                    if target_id not in nodes:
                        nodes[target_id] = {
                            "id": target_id,
                            "label": target,
                            "type": "External",
                            "group": 2,
                        }

                    # Add Link
                    links.append(
                        {
                            "source": doc_id,
                            "target": target_id,
                            "relationship": rel_type,
                        }
                    )

    # Format for frontend (d3/force-graph)
    graph_data = {"nodes": list(nodes.values()), "links": links}

    output_path = script_dir / "graph_data.json"
    with open(output_path, "w") as f:
        json.dump(graph_data, f, indent=2)

    logger.info(f"Graph data saved to {output_path}")
    logger.info(f"Nodes: {len(nodes)}, Links: {len(links)}")


if __name__ == "__main__":
    build_graph()
