import datetime
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import operator

logger = logging.getLogger(__name__)


# --- 1. Dynamic Facts Schema (Domain-Agnostic) ---


class DynamicFacts(BaseModel):
    """
    Generic facts container - accepts any key-value pairs.
    Replaces hardcoded BenefitEligibilityFactSchemaV1.

    This allows the system to handle any domain:
    - Immigration: has_job_offer, salary_offer, education_level
    - COVID benefits: has_small_business, revenue_loss_percent
    - Disability: disability_type, has_medical_certificate
    - Housing: household_income, household_size
    """
    facts: Dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: float = Field(default=1.0)
    missing_fields: List[str] = Field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a fact value by key."""
        return self.facts.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return self.facts.copy()


# --- 2. Rule Definitions & Metadata ---


class RuleCondition(BaseModel):
    fact_key: str
    operator: str  # "eq", "neq", "gt", "gte", "lt", "lte", "contains", "in_list"
    value: Any


class RuleMetadata(BaseModel):
    source_id: str  # e.g. "Immigration-Act-2024"
    section: str  # e.g. "Section 23(b)"
    effective_start: datetime.date
    effective_end: Optional[datetime.date] = None
    jurisdiction: str  # e.g. "Federal", "Provincial"
    doc_type: str  # "Act", "Regulation", "Policy"
    priority: int  # Higher number = higher precedence


class Rule(BaseModel):
    rule_id: str
    description: str
    metadata: RuleMetadata
    conditions: List[RuleCondition]
    outcome: Dict[str, Any]  # e.g. {"eligible": True, "program": "..."}


# --- 3. Trace & Result Schema ---


class TraceStep(BaseModel):
    step: str  # Description of the check (e.g., "income > 50000")
    value: Any  # The actual value found in facts
    result: str  # "pass", "fail", "skipped"
    source: str  # Citation (e.g., "SOR-99-12 s.12")


class EvaluationResult(BaseModel):
    decision: Optional[Dict[str, Any]]  # None if abstained/insufficient
    trace: List[TraceStep]
    status: str  # "success", "insufficient_facts", "no_match_found", "confidence_too_low"
    missing_facts: List[str] = []


# --- 4. Deterministic Engine (Pure Functions) ---

OPERATORS = {
    "eq": operator.eq,
    "neq": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "contains": lambda a, b: (str(b).lower() in str(a).lower()) if a else False,
    "in_list": lambda a, b: (a in b) if isinstance(b, list) else False,
    "in": lambda a, b: (a in b) if isinstance(b, list) else False,  # Alias for in_list
    "exists": lambda a, b: a is not None,  # Check if fact exists (is not None)
    "not_exists": lambda a, b: a is None,  # Check if fact does not exist
    "is_true": lambda a, b: bool(a) is True,  # Check if fact is truthy
    "is_false": lambda a, b: bool(a) is False,  # Check if fact is falsy
}


def evaluate_condition(fact_val: Any, condition: RuleCondition) -> bool:
    op_func = OPERATORS.get(condition.operator)
    if not op_func:
        raise ValueError(f"Unknown operator: {condition.operator}")

    try:
        # Case-insensitive string comparison
        if isinstance(condition.value, str) and isinstance(fact_val, str):
            return op_func(fact_val.lower(), condition.value.lower())
        return op_func(fact_val, condition.value)
    except (TypeError, ValueError, AttributeError) as e:
        logger.debug(f"Condition evaluation failed for {condition.fact_key}: {e}")
        return False


def evaluate_rules(
    facts: DynamicFacts,
    rules: List[Rule],
    eval_date_str: str,
    min_confidence: float = 0.7,
    filter_jurisdiction: Optional[str] = None,
    allowed_jurisdictions: Optional[List[str]] = None,
    allowed_doc_types: Optional[List[str]] = None,
) -> EvaluationResult:
    """
    Pure function to evaluate facts against a list of rules.
    Facts are now a dynamic dict, not a fixed schema.
    """
    trace_log: List[TraceStep] = []

    # 0. Parse Evaluation Date safely
    try:
        eval_date = datetime.date.fromisoformat(eval_date_str)
    except (ValueError, TypeError):
        return EvaluationResult(
            decision=None,
            trace=[
                TraceStep(
                    step="Date Parse",
                    value=eval_date_str,
                    result="fail",
                    source="System",
                )
            ],
            status="invalid_eval_date",
            missing_facts=[],
        )

    # 1. Confidence Check
    if facts.extraction_confidence < min_confidence:
        return EvaluationResult(
            decision=None,
            trace=[
                TraceStep(
                    step="Confidence Check",
                    value=facts.extraction_confidence,
                    result="fail",
                    source="System",
                )
            ],
            status="confidence_too_low",
            missing_facts=[],
        )

    # 2. Filter Rules (Date & Jurisdiction/Doc Type)
    active_rules = []
    jurisdictions_filter = allowed_jurisdictions or (
        [] if not filter_jurisdiction else [filter_jurisdiction]
    )
    for r in rules:
        # Jurisdiction Filter
        if jurisdictions_filter and r.metadata.jurisdiction.lower() not in [
            j.lower() for j in jurisdictions_filter
        ]:
            continue
        if allowed_doc_types and r.metadata.doc_type.lower() not in [
            d.lower() for d in allowed_doc_types
        ]:
            continue

        # Date Filter
        start = r.metadata.effective_start
        end = r.metadata.effective_end

        if start <= eval_date:
            if end is None or end >= eval_date:
                active_rules.append(r)

    # Sort: Priority Descending
    active_rules.sort(key=lambda x: x.metadata.priority, reverse=True)

    missing_facts_set = set(facts.missing_fields)
    passed_rules = []
    all_failed_conditions = []
    all_traces = []

    # EVALUATE ALL RULES
    for rule in active_rules:
        rule_passed = True
        local_trace = []

        local_trace.append(
            TraceStep(
                step=f"Evaluating Rule: {rule.rule_id}",
                value="N/A",
                result="info",
                source=f"{rule.metadata.source_id} {rule.metadata.section}",
            )
        )

        # Evaluate Conditions
        for cond in rule.conditions:
            # Use dict access instead of getattr
            fact_val = facts.get(cond.fact_key)

            # Check if fact is missing
            if fact_val is None:
                rule_passed = False
                missing_facts_set.add(cond.fact_key)
                local_trace.append(
                    TraceStep(
                        step=f"Check {cond.fact_key}",
                        value="MISSING",
                        result="fail",
                        source=f"{rule.metadata.source_id} {rule.metadata.section}",
                    )
                )
                continue

            # Check condition
            passed = evaluate_condition(fact_val, cond)
            local_trace.append(
                TraceStep(
                    step=f"Check {cond.fact_key} {cond.operator} {cond.value}",
                    value=fact_val,
                    result="pass" if passed else "fail",
                    source=f"{rule.metadata.source_id} {rule.metadata.section}",
                )
            )

            if not passed:
                rule_passed = False
                all_failed_conditions.append((cond, fact_val, rule))

        all_traces.extend(local_trace)

        if rule_passed:
            passed_rules.append(rule)

    trace_log.extend(all_traces)

    # DECISION LOGIC:
    # Fail if user PROVIDED a value that doesn't meet a threshold
    # (Dynamic - no hardcoded "critical_facts" list)
    for failed_cond, fact_val, rule in all_failed_conditions:
        # If user provided a value and it failed, return ineligible
        if fact_val is not None:
            return EvaluationResult(
                decision={
                    "eligible": False,
                    "program": "Not Eligible",
                    "details": f"Failed requirement: {failed_cond.fact_key} must be {failed_cond.operator} {failed_cond.value} (your value: {fact_val})"
                },
                trace=trace_log,
                status="failed_requirement",
                missing_facts=list(missing_facts_set),
            )

    # If we have passed rules, return the highest priority one
    if passed_rules:
        best_rule = passed_rules[0]
        return EvaluationResult(
            decision=best_rule.outcome,
            trace=trace_log,
            status="success",
            missing_facts=[],
        )

    # No explicit failures - user may be eligible pending more information
    # If no provided facts failed, return POTENTIALLY ELIGIBLE
    if missing_facts_set:
        return EvaluationResult(
            decision={
                "eligible": True,  # Optimistic: no explicit failures
                "program": "Potentially Eligible",
                "details": f"Based on provided information, you appear potentially eligible. Additional information needed: {', '.join(list(missing_facts_set)[:5])}"
            },
            trace=trace_log,
            status="pending_more_info",
            missing_facts=list(missing_facts_set),
        )

    return EvaluationResult(
        decision=None, trace=trace_log, status="no_match_found", missing_facts=[]
    )
