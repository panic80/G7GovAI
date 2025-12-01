import os
import sys
import re
from collections import defaultdict

# Fix paths for Docker
sys.path.append(os.getcwd())

from database import get_collection


def deep_scan():
    print("--- Deep Scan for 'Bill C-3' ---")
    try:
        collection = get_collection()

        # Fetch ALL documents (limit to 10000 for safety, though demo is likely smaller)
        # metadata usually contains 'source_title'
        all_docs = collection.get(limit=10000, include=["documents", "metadatas"])

        total_docs = len(all_docs["ids"])
        print(f"Total Documents in DB: {total_docs}")

        c3_hits = []

        # Regex for Bill C-3 variants
        # Matches: "Bill C-3", "Bill C3", "C-3", "C3" (with word boundaries)
        pattern = re.compile(r"\b(Bill\s*)?C-?3\b", re.IGNORECASE)

        for i, doc_text in enumerate(all_docs["documents"]):
            if pattern.search(doc_text):
                meta = all_docs["metadatas"][i]
                # Try to extract a "snippet" around the match
                matches = list(pattern.finditer(doc_text))
                for m in matches:
                    start = max(0, m.start() - 50)
                    end = min(len(doc_text), m.end() + 100)
                    snippet = doc_text[start:end].replace("\n", " ").strip()

                    c3_hits.append(
                        {
                            "id": all_docs["ids"][i],
                            "source": meta.get("source_title", "Unknown"),
                            "date_meta": meta.get("effective_date_start", "Unknown"),
                            "snippet": snippet,
                            "full_text": doc_text,  # Keep for clustering analysis if needed
                        }
                    )

        print(f"Total 'C-3' Mentions Found: {len(c3_hits)}")

        # Simple Clustering by Content Similarity (or just printing unique snippets)
        # We group by the "Source Title" + "Snippet start" to dedupe exact duplicates
        unique_sightings = defaultdict(list)

        for hit in c3_hits:
            # Create a rough "topic" key from the snippet (first 30 chars of snippet usually distinct enough)
            # Or better, use the full text to categorize
            unique_sightings[hit["source"]].append(hit)

        print("\n--- Detailed Findings ---")
        for source, hits in unique_sightings.items():
            print(f"\nSource: {source}")
            # Deduplicate snippets for display
            seen_snippets = set()
            for h in hits:
                if h["snippet"] not in seen_snippets:
                    print(f"  - [{h['date_meta']}] ...{h['snippet']}...")
                    seen_snippets.add(h["snippet"])

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Error: {e}")


if __name__ == "__main__":
    deep_scan()
