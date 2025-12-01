import os
import sys
import asyncio
import pytest
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from agent.govlens.nodes import retrieve_node, router_node


@pytest.mark.asyncio
async def test_retrieval():
    print("--- Testing Retrieval for 'what is bill c-3' ---")

    # 1. Test Router Classification
    state_router = {"query": "what is bill c-3"}
    try:
        route_res = await router_node(state_router)
        print(f"\nRouter Decision: {route_res.get('search_strategy')}")
    except Exception as e:
        print(f"Router Error: {e}")

    # 2. Test Simple Retrieval (Baseline)
    print("\n--- Simple Retrieval (Relevance) ---")
    state_simple = {
        "query": "what is bill c-3",
        "generated_queries": ["what is bill c-3"],
        "language": "en",
        "search_strategy": "simple",
        "loop_count": 0,
    }
    res_simple = await retrieve_node(state_simple)
    docs_simple = res_simple["documents"]
    print(f"Retrieved {len(docs_simple)} docs.")
    # Extract Sources
    sources_simple = []
    for d in docs_simple[:10]:  # Check top 10
        # simplistic parsing of the formatted string
        if "Source:" in d:
            src = d.split("Source:")[1].split("]")[0].strip()
            sources_simple.append(src)
    print(f"Top 10 Sources: {sources_simple}")

    # 3. Test Complex Retrieval (Diversity)
    print("\n--- Complex Retrieval (Diversity) ---")
    state_complex = {
        "query": "what is bill c-3",
        "generated_queries": ["what is bill c-3"],
        "language": "en",
        "search_strategy": "complex",  # FORCE COMPLEX
        "loop_count": 0,
    }
    res_complex = await retrieve_node(state_complex)
    docs_complex = res_complex["documents"]
    print(f"Retrieved {len(docs_complex)} docs.")

    sources_complex = []
    for d in docs_complex[:10]:
        if "Source:" in d:
            src = d.split("Source:")[1].split("]")[0].strip()
            sources_complex.append(src)
    print(f"Top 10 Sources: {sources_complex}")


if __name__ == "__main__":
    test_retrieval()
