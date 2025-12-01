from typing import TypedDict, List, Annotated, Literal, Optional
import operator
from pydantic import BaseModel


class GovLensState(TypedDict):
    query: str  # Original user query
    language: str  # User language
    search_strategy: str  # "simple" or "complex" (determined by router)
    categories: Optional[List[str]]  # Filter by document categories
    themes: Optional[List[str]]  # Filter by themes

    generated_queries: Annotated[List[str], operator.add]  # Trace of search queries
    documents: Annotated[List[str], operator.add]  # Accumulated content
    doc_metadata: Optional[dict]  # Mapping of doc_id -> {source_title, category, ...}

    trace_log: Annotated[List[str], operator.add]  # "Thinking" log for UI
    loop_count: int  # Safety break

    final_answer: str  # Raw JSON response

    # Structured output fields (parsed from final_answer)
    answer_text: Optional[str]
    citations: Optional[List[dict]]
    bullets: Optional[List[str]]
    confidence: Optional[float]
    abstained: Optional[bool]
