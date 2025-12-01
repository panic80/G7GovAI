import os
import sys
from dotenv import load_dotenv
from collections import Counter

sys.path.append(os.getcwd())
load_dotenv()

# Attempt to import from agent.govlens.nodes, handling potential path issues
try:
    from agent.govlens.nodes import retrieve_node
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from agent.govlens.nodes import retrieve_node

def test_retrieval_dominance():
    query = "what kind of laws, legislations or bills exist to protect canadians from harmful foods?"
    print(f"--- Testing Retrieval Dominance for query: '{query}' ---")

    # 1. Test Simple Retrieval (Baseline)
    print("\n--- Simple Retrieval (Relevance) ---")
    state_simple = {
        "query": query,
        "generated_queries": [query],
        "language": "en",
        "search_strategy": "simple",
        "loop_count": 0,
    }
    
    try:
        res_simple = retrieve_node(state_simple)
        docs_simple = res_simple["documents"]
        print(f"Retrieved {len(docs_simple)} docs.")
        
        # Analyze Sources
        sources_simple = []
        for i, d in enumerate(docs_simple):
            # Parse source from the formatted string "Content... [Source: Title]"
            if "Source:" in d:
                parts = d.split("Source:")
                if len(parts) > 1:
                    src = parts[1].split("]")[0].strip()
                    sources_simple.append(src)
                    print(f"{i+1}. {src}")
                else:
                    print(f"{i+1}. (Source not found in string)")
            else:
                print(f"{i+1}. (No Source tag)")

        # Count occurrences
        counts = Counter(sources_simple)
        print("\n--- Source Distribution (Top 20) ---")
        for source, count in counts.most_common(20):
            print(f"{source}: {count}")

        if not sources_simple:
            print("\nWARNING: No sources found. The database might be empty or the query returned no results.")

    except Exception as e:
        print(f"Error during retrieval: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_retrieval_dominance()
