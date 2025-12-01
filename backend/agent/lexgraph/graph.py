from langgraph.graph import StateGraph, END
from typing import Literal

from .nodes import (
    retrieve_node,
    extract_rules_node,
    resolve_subjective_terms_node,
    analyze_citations_node,
    synthesize_node,
    map_legislation_node,
)
from .state import LegalResearchState

# --- NEURO-SYMBOLIC PIPELINE WITH LEGISLATIVE SOURCE INTEGRATION ---
# 1. RETRIEVE           → Get relevant legislative documents from ChromaDB
# 2. EXTRACT RULES      → LLM reads documents and extracts rules as JSON (NEURO)
# 3. RESOLVE THRESHOLDS → LLM resolves subjective terms to concrete thresholds (NEURO)
# 4. MAP LEGISLATION    → Categorize legislation into primary, related, definitions
# 5. EXTRACT FACTS      → LLM extracts facts from user scenario (NEURO)
# 6. EVALUATE           → Deterministic rule engine evaluates facts against rules (SYMBOLIC)
#
# As you ingest more documents, the system automatically extracts more rules!
# Subjective terms like "genuine salary" get resolved dynamically!
# Legislative excerpts and decision trees provide full traceability!

# Build the graph
workflow = StateGraph(LegalResearchState)

# Add Nodes
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("extract_rules", extract_rules_node)  # Extract rules from legislation
workflow.add_node("resolve_thresholds", resolve_subjective_terms_node)  # Resolve subjective terms
workflow.add_node("map_legislation", map_legislation_node)  # Categorize legislation for UI
workflow.add_node("extract_facts", analyze_citations_node)  # Extract facts from user scenario
workflow.add_node("evaluate", synthesize_node)  # Deterministic rule engine

# Define Edges (Sequential Pipeline)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "extract_rules")
workflow.add_edge("extract_rules", "resolve_thresholds")
workflow.add_edge("resolve_thresholds", "map_legislation")
workflow.add_edge("map_legislation", "extract_facts")
workflow.add_edge("extract_facts", "evaluate")
workflow.add_edge("evaluate", END)

# Compile the graph
app_graph = workflow.compile()
