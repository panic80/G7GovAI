from typing import List, Dict, Any, Optional, Literal, ForwardRef
from pydantic import BaseModel


class Decision(BaseModel):
    eligible: bool
    effective_date: str


class TraceStep(BaseModel):
    clause: str
    reason: str
    version: str
    source_id: str
    confidence: Optional[str] = None  # "HIGH", "MEDIUM", "LOW" - for subjective term resolution


class RulesResponse(BaseModel):
    decision: Decision
    explanation: Optional[str] = None  # LLM-generated summary of why the decision was made
    trace: List[TraceStep]
    sources: List[str]


# --- Legislative Source Integration Models ---

class LegislativeExcerpt(BaseModel):
    """Verbatim legislative text that supports a rule or decision."""
    text: str                                    # Verbatim legislative text
    citation: str                                # Full citation (e.g., "IRPA s. 12(1)(a)")
    act_name: str                                # Full act name
    section_title: Optional[str] = None          # Section heading if available
    plain_language: Optional[str] = None         # Plain language explanation
    confidence: Optional[str] = None             # "HIGH", "MEDIUM", "LOW"


class DecisionTreeNode(BaseModel):
    """Node in the decision tree visualization."""
    id: str
    type: Literal["condition", "decision"]
    label: str                                   # Short description for display
    condition_text: Optional[str] = None         # e.g., "salary_offer >= 66000"
    legislative_excerpt: Optional[LegislativeExcerpt] = None
    result: Optional[Literal["pass", "fail", "unknown"]] = None
    children: List["DecisionTreeNode"] = []


# Enable self-referencing for DecisionTreeNode.children
DecisionTreeNode.model_rebuild()


class LegislationMap(BaseModel):
    """Map of all legislation relevant to a scenario."""
    primary: List[LegislativeExcerpt] = []       # Directly applicable legislation
    related: List[LegislativeExcerpt] = []       # Contextual/secondary legislation
    definitions: List[LegislativeExcerpt] = []   # Relevant definitions from legislation


class EnhancedRulesResponse(BaseModel):
    """Enhanced response with full legislative context and decision tree."""
    decision: Decision
    explanation: Optional[str] = None
    trace: List[TraceStep]
    sources: List[str]
    # New fields for legislative source integration
    decision_tree: Optional[DecisionTreeNode] = None
    legislation_map: Optional[LegislationMap] = None


# Other models can be added here as needed for other modules
