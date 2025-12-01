from typing import TypedDict, List, Annotated, Optional
import operator


class LegalResearchState(TypedDict):
    query: str  # The original user scenario
    language: str  # Language of the query (e.g., "en", "fr")
    effective_date: str  # YYYY-MM-DD for date-aware evaluation
    generated_queries: Annotated[
        List[str], operator.add
    ]  # Used to transport extracted facts JSON
    documents: Annotated[
        List[str], operator.add
    ]  # Accumulated content from laws (Context)
    citations_found: Annotated[
        List[str], operator.add
    ]  # IDs of laws we found referenced
    trace_log: Annotated[
        List[str], operator.add
    ]  # Log of agent's thinking process for UI
    loop_count: int  # Safety break
    final_answer: str  # The final decision/summary (raw JSON)
    eligible: Optional[bool]  # The final eligibility decision
    decision_trace: Optional[List[dict]]  # The parsed trace
    extracted_rules: Optional[str]  # JSON string of rules extracted from documents
    resolved_rules: Optional[str]  # JSON string of rules with resolved subjective thresholds
    # Legislative source integration
    legislative_excerpts: Optional[List[dict]]  # Extracted legislative excerpts with citations
    decision_tree: Optional[dict]  # Hierarchical decision tree structure
    legislation_map: Optional[dict]  # Primary, related, and definition excerpts
