import re
import json
import datetime
import logging
from typing import List, Dict, Any, Optional
from langchain_core.prompts import PromptTemplate
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
# API key is managed via model_config (Governance Dashboard)

from embeddings import get_embedding
from database import get_collection
from .state import LegalResearchState
from models import (
    RulesResponse, Decision, TraceStep,
    LegislativeExcerpt, DecisionTreeNode, LegislationMap, EnhancedRulesResponse
)

from rules import (
    Rule,
    RuleCondition,
    RuleMetadata,
    evaluate_rules,
    DynamicFacts,
    EvaluationResult,
)

from agent.core import get_llm, clean_json_response, get_language_instruction
from core.model_state import model_config
from config.thresholds import get_salary_thresholds_prompt

# Lazy LLM initialization - created on first use
def get_langchain_llm():
    """Get LangChain LLM lazily (only when API key is configured)."""
    return get_llm(model=model_config.get_model("fast"), temperature=0).langchain


# --- NODE 1: RETRIEVE ---
def retrieve_node(state: LegalResearchState) -> Dict[str, Any]:
    """
    Retrieves relevant legislative documents from ChromaDB.
    """
    logger.debug("--- RETRIEVE DOCUMENTS ---")
    query = state["query"]
    language = state.get("language", "en")

    try:
        collection = get_collection()
        query_emb = get_embedding(query)
        if not query_emb:
            return {
                "documents": [],
                "trace_log": ["Warning: Embedding generation failed. Skipping retrieval."],
            }

        # Get more documents for rule extraction
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=10,
            where={"language": language}
        )

        documents = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                content = results["documents"][0][i]
                # Include metadata if available
                metadata = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
                source_title = metadata.get("source_title", "Unknown Source")
                documents.append(f"[Source: {source_title}] [ID: {doc_id}]\n{content}")

        return {
            "documents": documents,
            "trace_log": [f"Retrieved {len(documents)} legislative documents."],
        }
    except Exception as e:
        logger.error(f"Retrieval Error: {type(e).__name__}")
        return {"documents": [], "trace_log": [f"Retrieval error: {str(e)}"]}


# --- NODE 2: COMBINED EXTRACT + RESOLVE RULES (Optimized - Single LLM Call) ---
def extract_and_resolve_rules_node(state: LegalResearchState) -> Dict[str, Any]:
    """
    Combined node that extracts rules AND resolves subjective thresholds in one LLM call.
    This eliminates one full LLM round-trip for ~3-4 second speedup.
    """
    logger.debug("--- EXTRACT AND RESOLVE RULES ---")

    documents = state.get("documents", [])
    user_query = state["query"]

    if not documents:
        return {
            "resolved_rules": "[]",
            "trace_log": ["No documents retrieved. Cannot extract rules."],
        }

    docs_context = "\n\n---\n\n".join(documents[:5])

    # Enhanced prompt with legislative excerpts and citations
    combined_prompt = f"""Extract immigration rules from these documents with VERBATIM legislative excerpts and precise citations.

SCENARIO: {user_query}

DOCUMENTS:
{docs_context}

MANDATORY REQUIREMENTS:
1. Include salary_offer threshold condition in at least one rule
2. Include VERBATIM source_excerpt text from the document that supports each rule
3. Provide precise source_citation (e.g., "s. 12(1)(a)" or "Article 5.2")
4. Include plain_language explanation of what the rule means

{get_salary_thresholds_prompt()}

FACT KEYS: applicant_role, has_job_offer, salary_offer, years_experience, education_level, target_country, sector
OPERATORS: eq (equals), gte (>=), contains (substring match)

Output 2-3 rules as JSON with legislative excerpts:
{{"resolved_rules":[
  {{
    "rule_id":"salary-threshold-check",
    "description":"Job offer must meet minimum salary",
    "source_document":"Immigration and Refugee Protection Regulations",
    "source_section":"s. 203(1)(a)",
    "source_excerpt":"A work permit may be issued to a foreign national who intends to perform work that would create or maintain significant economic benefit to Canada...",
    "source_citation":"IRPR s. 203(1)(a)",
    "act_name":"Immigration and Refugee Protection Regulations",
    "plain_language":"Your job offer must provide significant economic benefit to Canada, which typically means meeting minimum salary thresholds for your occupation.",
    "conditions":[{{"fact_key":"salary_offer","operator":"gte","value":66000,"confidence":"MEDIUM"}}],
    "outcome":{{"eligible":true,"program":"Work Permit","details":"Meets wage requirements"}}
  }}
]}}

IMPORTANT:
- source_excerpt MUST be actual text copied from the documents above
- If you cannot find exact text, quote the most relevant passage
- source_citation should use standard legal citation format

JSON:"""

    try:
        model = genai.GenerativeModel(model_config.get_model("fast"))  # Test with flash-lite for speed
        response = model.generate_content(combined_prompt)
        response_text = response.text.strip()

        # Clean JSON from markdown
        response_text = clean_json_response(response_text)
        result = json.loads(response_text)
        resolved_rules = result.get("resolved_rules", [])
        summary = result.get("extraction_summary", "No summary provided")

        # Count confidence levels
        high_conf = sum(1 for r in resolved_rules for c in r.get("conditions", []) if c.get("confidence") == "HIGH")
        med_conf = sum(1 for r in resolved_rules for c in r.get("conditions", []) if c.get("confidence") == "MEDIUM")
        low_conf = sum(1 for r in resolved_rules for c in r.get("conditions", []) if c.get("confidence") == "LOW")

        # Extract legislative excerpts from rules
        legislative_excerpts = []
        for rule in resolved_rules:
            if rule.get("source_excerpt"):
                legislative_excerpts.append({
                    "text": rule.get("source_excerpt", ""),
                    "citation": rule.get("source_citation", rule.get("source_section", "")),
                    "act_name": rule.get("act_name", rule.get("source_document", "")),
                    "section_title": rule.get("description", ""),
                    "plain_language": rule.get("plain_language", ""),
                    "confidence": rule.get("conditions", [{}])[0].get("confidence") if rule.get("conditions") else None,
                    "rule_id": rule.get("rule_id", "")
                })

        trace_msg = f"Extracted and resolved {len(resolved_rules)} rules: {high_conf} HIGH, {med_conf} MEDIUM, {low_conf} LOW confidence."
        if summary:
            trace_msg += f"\n{summary}"

        return {
            "resolved_rules": json.dumps(resolved_rules),
            "legislative_excerpts": legislative_excerpts,
            "trace_log": [trace_msg],
        }

    except json.JSONDecodeError as e:
        logger.warning(f"JSON Parse Error in combined extraction: {type(e).__name__}")
        return {
            "resolved_rules": "[]",
            "trace_log": [f"Rule extraction failed: Could not parse LLM response as JSON"],
        }
    except Exception as e:
        logger.exception(f"Combined Extraction Error: {type(e).__name__}")
        return {
            "resolved_rules": "[]",
            "trace_log": [f"Rule extraction error: {str(e)}"],
        }


# --- MAP LEGISLATION NODE: Categorize legislation into primary, related, definitions ---
def map_legislation_node(state: LegalResearchState) -> Dict[str, Any]:
    """
    Analyzes retrieved documents and categorizes them into:
    - Primary: Directly applicable legislation for the scenario
    - Related: Contextual/secondary legislation
    - Definitions: Relevant legal definitions

    This builds the LegislationMap for the UI to display.
    """
    logger.debug("--- MAP LEGISLATION ---")

    documents = state.get("documents", [])
    user_query = state["query"]
    legislative_excerpts = state.get("legislative_excerpts", [])

    if not documents:
        return {
            "legislation_map": {"primary": [], "related": [], "definitions": []},
            "trace_log": ["No documents to map."],
        }

    docs_context = "\n\n---\n\n".join(documents[:8])

    map_prompt = f"""Analyze the legislative documents and categorize them for the user's scenario.

USER SCENARIO: {user_query}

DOCUMENTS:
{docs_context}

TASK: Categorize the legislation into three groups with excerpts:

1. PRIMARY LEGISLATION: Documents that DIRECTLY determine eligibility for this scenario
2. RELATED LEGISLATION: Documents that provide context but don't directly determine eligibility
3. DEFINITIONS: Legal definitions relevant to understanding the requirements

OUTPUT FORMAT (JSON):
{{
  "primary": [
    {{
      "text": "Verbatim excerpt from the legislation",
      "citation": "Precise citation (e.g., IRPA s. 12(1)(a))",
      "act_name": "Full act name",
      "section_title": "Section heading if available",
      "plain_language": "What this means in plain English"
    }}
  ],
  "related": [...],
  "definitions": [...]
}}

INSTRUCTIONS:
- Extract 2-4 primary excerpts that are most relevant to the scenario
- Extract 1-2 related excerpts for context
- Extract any relevant definitions (terms like "foreign national", "work permit", etc.)
- Each excerpt should be a meaningful passage, not just a phrase
- Plain language should help non-experts understand the legal text

JSON:"""

    try:
        model = genai.GenerativeModel(model_config.get_model("fast"))
        response = model.generate_content(map_prompt)
        response_text = response.text.strip()

        # Clean JSON from markdown
        response_text = clean_json_response(response_text)
        legislation_map = json.loads(response_text)

        # Ensure all required keys exist
        legislation_map.setdefault("primary", [])
        legislation_map.setdefault("related", [])
        legislation_map.setdefault("definitions", [])

        primary_count = len(legislation_map.get("primary", []))
        related_count = len(legislation_map.get("related", []))
        def_count = len(legislation_map.get("definitions", []))

        return {
            "legislation_map": legislation_map,
            "trace_log": [f"Mapped legislation: {primary_count} primary, {related_count} related, {def_count} definitions."],
        }

    except json.JSONDecodeError as e:
        logger.warning(f"JSON Parse Error in map_legislation: {type(e).__name__}")
        return {
            "legislation_map": {"primary": [], "related": [], "definitions": []},
            "trace_log": ["Failed to parse legislation map from LLM response."],
        }
    except Exception as e:
        logger.error(f"Map Legislation Error: {type(e).__name__}")
        return {
            "legislation_map": {"primary": [], "related": [], "definitions": []},
            "trace_log": [f"Legislation mapping error: {str(e)}"],
        }


# --- NODE 2 (LEGACY): EXTRACT RULES FROM DOCUMENTS ---
def extract_rules_node(state: LegalResearchState) -> Dict[str, Any]:
    """
    Uses LLM to extract applicable rules from retrieved legislative documents.
    This is the key innovation - rules are dynamically extracted, not hardcoded.
    """
    logger.debug("--- EXTRACT RULES FROM LEGISLATION ---")

    documents = state.get("documents", [])
    user_query = state["query"]

    if not documents:
        return {
            "extracted_rules": "[]",
            "trace_log": ["No documents retrieved. Cannot extract rules."],
        }

    # Combine documents into context
    docs_context = "\n\n---\n\n".join(documents[:5])  # Limit to 5 docs to avoid token limits

    extraction_prompt = f"""You are a Legal Rule Extraction Agent. Extract applicable rules from legislative documents as structured JSON.

USER'S SCENARIO: {user_query}

LEGISLATIVE DOCUMENTS:
{docs_context}

TASK: Extract rules that could apply to the user's scenario.

OUTPUT FORMAT (JSON):
{{
  "rules": [
    {{
      "rule_id": "unique identifier (e.g., 'IRPR-s205-tech-worker')",
      "description": "What this rule does",
      "source_document": "Document ID or title",
      "source_section": "Section/article number",
      "conditions": [
        {{"fact_key": "key_name", "operator": "eq|neq|gt|gte|lt|lte|contains", "value": ...}}
      ],
      "outcome": {{"eligible": true/false, "program": "Program name", "details": "..."}}
    }}
  ],
  "required_facts": ["list", "of", "all", "fact_keys", "used"]
}}

FACT KEY GUIDELINES:
- Use descriptive snake_case keys (e.g., has_job_offer, salary_offer, revenue_loss_percent)
- Common keys: has_job_offer, salary_offer, years_experience, education_level, citizenship, target_country, age, income, savings
- Domain-specific keys are allowed (e.g., has_small_business, disability_type, household_size)
- Be consistent with naming across rules

OPERATORS: eq (equals), neq (not equals), gt (greater than), gte (greater or equal), lt (less than), lte (less or equal), contains (string contains)

INSTRUCTIONS:
1. Extract rules ACTUALLY STATED in the documents
2. Use any fact_key that accurately represents the condition
3. Include source document reference for traceability
4. Extract 1-5 most relevant rules

JSON Output:"""

    try:
        model = genai.GenerativeModel(model_config.get_model("reasoning"))
        response = model.generate_content(extraction_prompt)
        response_text = response.text.strip()

        # Clean up response - extract JSON from markdown if needed
        response_text = clean_json_response(response_text)

        # Parse to validate JSON
        rules_data = json.loads(response_text)
        rules_list = rules_data.get("rules", [])

        rule_summaries = [f"- {r.get('rule_id', 'unknown')}: {r.get('description', '')[:50]}..." for r in rules_list]
        summary = "\n".join(rule_summaries) if rule_summaries else "No rules extracted"

        return {
            "extracted_rules": json.dumps(rules_list),
            "trace_log": [f"Extracted {len(rules_list)} rules from legislation:\n{summary}"],
        }
    except json.JSONDecodeError as e:
        logger.warning(f"JSON Parse Error: {type(e).__name__}")
        return {
            "extracted_rules": "[]",
            "trace_log": [f"Rule extraction failed: Could not parse LLM response as JSON"],
        }
    except Exception as e:
        logger.error(f"Rule Extraction Error: {type(e).__name__}")
        return {
            "extracted_rules": "[]",
            "trace_log": [f"Rule extraction error: {str(e)}"],
        }


# --- NODE 3: EXTRACT FACTS FROM USER SCENARIO (DYNAMIC) ---
def analyze_citations_node(state: LegalResearchState) -> Dict[str, Any]:
    """
    Extracts facts from the user's scenario based on what the rules require.
    Fully dynamic - no hardcoded schema.
    """
    logger.debug("--- EXTRACT FACTS FROM SCENARIO ---")

    user_query = state["query"]

    # Get required fact_keys from extracted/resolved rules
    required_facts = set()
    rules_json = state.get("resolved_rules") or state.get("extracted_rules", "[]")
    try:
        rules = json.loads(rules_json)
        for rule in rules:
            for cond in rule.get("conditions", []):
                fact_key = cond.get("fact_key", "")
                if fact_key:
                    required_facts.add(fact_key)
    except (json.JSONDecodeError, TypeError):
        pass

    # If no rules extracted, we can't know what facts to extract
    if not required_facts:
        return {
            "generated_queries": [json.dumps({"facts": {}, "extraction_confidence": 0.5, "missing_fields": []})],
            "trace_log": ["No rules found - no facts to extract"],
        }

    # Build dynamic extraction prompt based on required facts
    facts_list = "\n".join(f"- {fact}" for fact in sorted(required_facts))

    extraction_prompt = f"""You are a Fact Extraction Agent. Extract ONLY the specified facts from the user's scenario.

USER SCENARIO: {user_query}

FACTS TO EXTRACT (only these):
{facts_list}

OUTPUT FORMAT (JSON):
{{
  "facts": {{
    "fact_key": value,
    ...
  }},
  "extraction_confidence": 0.0-1.0,
  "missing_fields": ["fields", "not", "found"]
}}

INSTRUCTIONS:
- Extract ONLY the facts listed above
- Use null for facts not mentioned in the scenario
- Convert currency to numbers (e.g. "$95,000" -> 95000)
- Infer boolean values (e.g. "I have a job offer" -> has_job_offer: true)
- Include in missing_fields any required facts not found in scenario
- Set extraction_confidence based on how clearly facts are stated

JSON Output:"""

    try:
        model = genai.GenerativeModel(model_config.get_model("fast"))
        response = model.generate_content(extraction_prompt)
        response_text = response.text.strip()

        # Clean up JSON from markdown
        response_text = clean_json_response(response_text)

        result = json.loads(response_text)
        facts = result.get("facts", {})
        confidence = result.get("extraction_confidence", 0.8)
        missing = result.get("missing_fields", [])

        # Build output in DynamicFacts format
        output = {
            "facts": facts,
            "extraction_confidence": confidence,
            "missing_fields": missing
        }

        fact_summary = ", ".join(f"{k}={v}" for k, v in facts.items() if v is not None)

        return {
            "generated_queries": [json.dumps(output)],
            "trace_log": [f"Extracted Facts: {fact_summary}"],
        }
    except Exception as e:
        logger.error(f"Fact extraction error: {type(e).__name__}")
        return {
            "generated_queries": [json.dumps({"facts": {}, "extraction_confidence": 0.5, "missing_fields": list(required_facts)})],
            "trace_log": [f"Fact Extraction Failed: {e}"],
        }


# --- HELPER: Build Decision Tree from Rules and Trace ---
def build_decision_tree(
    rules_data: List[dict],
    trace_steps: List[TraceStep],
    decision_eligible: bool,
    legislative_excerpts: Optional[List[dict]]
) -> dict:
    """
    Builds a hierarchical decision tree from rules and evaluation trace.

    Structure:
    - Root: "Eligibility Check"
    - Children: Each rule condition as a node
    - Leaves: Final decision (ELIGIBLE/INELIGIBLE)
    """
    # Map rule_id to legislative excerpt for lookup
    excerpt_map = {}
    if legislative_excerpts:
        excerpt_map = {e.get("rule_id", ""): e for e in legislative_excerpts if e.get("rule_id")}

    # Build condition nodes from trace
    condition_nodes = []
    for i, step in enumerate(trace_steps):
        # Determine result from trace reason
        result = "unknown"
        if "PASS" in step.reason.upper():
            result = "pass"
        elif "FAIL" in step.reason.upper():
            result = "fail"

        # Find matching excerpt
        excerpt = None
        for rule in rules_data:
            rule_id = rule.get("rule_id", "")
            if rule_id in excerpt_map:
                excerpt_data = excerpt_map[rule_id]
                excerpt = {
                    "text": excerpt_data.get("text", ""),
                    "citation": excerpt_data.get("citation", ""),
                    "act_name": excerpt_data.get("act_name", ""),
                    "section_title": excerpt_data.get("section_title", ""),
                    "plain_language": excerpt_data.get("plain_language", ""),
                    "confidence": excerpt_data.get("confidence")
                }
                break

        condition_node = {
            "id": f"condition-{i}",
            "type": "condition",
            "label": step.clause,
            "condition_text": step.clause,
            "legislative_excerpt": excerpt,
            "result": result,
            "children": []
        }
        condition_nodes.append(condition_node)

    # Build tree: chain conditions together, last one leads to decision
    if condition_nodes:
        # Link conditions in sequence
        for i in range(len(condition_nodes) - 1):
            condition_nodes[i]["children"] = [condition_nodes[i + 1]]

        # Add final decision as leaf of last condition
        decision_node = {
            "id": "decision-final",
            "type": "decision",
            "label": "ELIGIBLE" if decision_eligible else "INELIGIBLE",
            "condition_text": None,
            "legislative_excerpt": None,
            "result": "pass" if decision_eligible else "fail",
            "children": []
        }
        condition_nodes[-1]["children"] = [decision_node]

        # Root node
        root = {
            "id": "root",
            "type": "condition",
            "label": "Eligibility Evaluation",
            "condition_text": None,
            "legislative_excerpt": None,
            "result": None,
            "children": [condition_nodes[0]]
        }
    else:
        # No conditions - just show decision
        root = {
            "id": "root",
            "type": "decision",
            "label": "ELIGIBLE" if decision_eligible else "INELIGIBLE",
            "condition_text": None,
            "legislative_excerpt": None,
            "result": "pass" if decision_eligible else "fail",
            "children": []
        }

    return root


# --- NODE 4: EVALUATE RULES (The "Symbolic" Step) ---
def synthesize_node(state: LegalResearchState) -> Dict[str, Any]:
    """
    Runs the DETERMINISTIC RULE ENGINE with dynamically extracted rules.
    This ensures consistent, traceable decisions.
    """
    logger.debug("--- EVALUATE RULES ---")

    try:
        # 1. Load Facts (now using DynamicFacts)
        if not state.get("generated_queries"):
            raise ValueError("No facts extracted from previous step.")

        facts_json = state["generated_queries"][0]
        facts_data = json.loads(facts_json)

        # Create DynamicFacts from extracted data
        facts = DynamicFacts(
            facts=facts_data.get("facts", facts_data),  # Support both {"facts": {...}} and flat dict
            extraction_confidence=facts_data.get("extraction_confidence", 0.8),
            missing_fields=facts_data.get("missing_fields", [])
        )

        # 2. Load Resolved Rules (with concrete thresholds) - fall back to extracted if not available
        resolved_rules_json = state.get("resolved_rules") or state.get("extracted_rules", "[]")
        extracted_rules_data = json.loads(resolved_rules_json)

        # Convert JSON rules to Rule objects - NO FILTERING (fully dynamic)
        engine_rules = []
        confidence_map = {}  # Maps (rule_id, fact_key) -> confidence
        for r in extracted_rules_data:
            try:
                conditions = []
                rule_id = r.get("rule_id", "unknown")
                for c in r.get("conditions", []):
                    fact_key = c.get("fact_key", "")
                    if not fact_key:
                        continue
                    conditions.append(
                        RuleCondition(
                            fact_key=fact_key,
                            operator=c["operator"],
                            value=c["value"]
                        )
                    )
                    # Store confidence for each condition
                    if c.get("confidence"):
                        confidence_map[(rule_id, fact_key)] = c.get("confidence")

                if not conditions:
                    continue

                rule = Rule(
                    rule_id=rule_id,
                    description=r.get("description", ""),
                    metadata=RuleMetadata(
                        source_id=r.get("source_document", "Extracted from legislation"),
                        section=r.get("source_section", ""),
                        effective_start=datetime.date(2020, 1, 1),
                        jurisdiction="Extracted",
                        doc_type="Legislation",
                        priority=100,
                    ),
                    conditions=conditions,
                    outcome=r.get("outcome", {"eligible": False}),
                )
                engine_rules.append(rule)
            except Exception as rule_error:
                logger.warning(f"Error parsing rule: {type(rule_error).__name__}")
                continue

        if not engine_rules:
            # Fallback message if no rules were extracted
            return {
                "final_answer": json.dumps({
                    "decision": {"eligible": False, "effective_date": state.get("effective_date", "2025-01-01")},
                    "trace": [{"clause": "No Rules Found", "reason": "No applicable rules could be extracted from the legislation. Try ingesting more relevant documents.", "version": "", "source_id": "System"}],
                    "sources": []
                }),
                "eligible": False,
                "decision_trace": [],
                "trace_log": state.get("trace_log", []) + ["No rules extracted from documents. Cannot evaluate eligibility."],
            }

        # 3. Run Engine
        eval_date = state.get("effective_date", "2025-01-01")
        result: EvaluationResult = evaluate_rules(facts, engine_rules, eval_date)

        # 4. Convert to Frontend Response Format (with confidence levels)
        frontend_trace = []
        for step in result.trace:
            # Try to extract rule_id and fact_key from step info
            # The step format is typically "Check fact_key operator value"
            confidence = None
            step_parts = step.step.split()
            if len(step_parts) >= 2 and step_parts[0] == "Check":
                fact_key = step_parts[1]
                # Look up confidence for this fact_key across all rules
                for (rule_id, fk), conf in confidence_map.items():
                    if fk == fact_key:
                        confidence = conf
                        break

            frontend_trace.append(
                TraceStep(
                    clause=step.step,
                    reason=f"Value: {step.value} -> {step.result.upper()}",
                    version=eval_date,
                    source_id=step.source,
                    confidence=confidence,
                )
            )

        if result.status in ["insufficient_facts", "pending_more_info"]:
            frontend_trace.append(
                TraceStep(
                    clause="Additional Info Needed",
                    reason=f"Missing fields for complete evaluation: {', '.join(result.missing_facts[:5])}",
                    version=eval_date,
                    source_id="System",
                )
            )

        decision_eligible = result.decision.get("eligible", False) if result.decision else False
        program_name = result.decision.get("program", "Unknown") if result.decision else "Unknown"

        # Generate LLM explanation for the decision
        explanation = None
        try:
            # Build a summary of conditions for the prompt
            trace_summary = "\n".join([
                f"- {t.clause}: {t.reason}" for t in frontend_trace[:10]
            ])
            facts_summary = json.dumps(facts.facts, indent=2) if facts.facts else "{}"

            explanation_prompt = f"""Based on the rule evaluation results, explain in 1-2 clear sentences why the applicant is {"ELIGIBLE" if decision_eligible else "INELIGIBLE"}.

Facts extracted from the scenario:
{facts_summary}

Conditions evaluated:
{trace_summary}

Decision: {"ELIGIBLE" if decision_eligible else "INELIGIBLE"}

Provide a concise, natural language explanation that summarizes the key factors. Be specific about what passed or failed."""

            model = genai.GenerativeModel(model_config.get_model("reasoning"))
            response = model.generate_content(explanation_prompt)
            explanation = response.text.strip()
        except Exception as exp_error:
            logger.warning(f"Failed to generate explanation: {type(exp_error).__name__}")
            explanation = None

        # Build decision tree from rules and trace
        legislative_excerpts = state.get("legislative_excerpts", [])
        decision_tree = build_decision_tree(
            extracted_rules_data,
            frontend_trace,
            decision_eligible,
            legislative_excerpts
        )

        # Get legislation map from state (populated by map_legislation_node)
        legislation_map = state.get("legislation_map") or {"primary": [], "related": [], "definitions": []}

        # Build enhanced response with decision tree and legislation map
        # Handle potential None values safely
        decision_tree_obj = None
        if decision_tree:
            try:
                decision_tree_obj = DecisionTreeNode(**decision_tree)
            except Exception as dt_error:
                logger.warning(f"Failed to create DecisionTreeNode: {dt_error}")

        legislation_map_obj = None
        if legislation_map and isinstance(legislation_map, dict):
            try:
                legislation_map_obj = LegislationMap(**legislation_map)
            except Exception as lm_error:
                logger.warning(f"Failed to create LegislationMap: {lm_error}")

        final_response = EnhancedRulesResponse(
            decision=Decision(eligible=decision_eligible, effective_date=eval_date),
            explanation=explanation,
            trace=frontend_trace,
            sources=[t.source_id for t in frontend_trace if t.source_id != "System"],
            decision_tree=decision_tree_obj,
            legislation_map=legislation_map_obj,
        )

        status_msg = f"Rule Engine Finished. Status: {result.status}"
        if decision_eligible:
            status_msg += f" | Program: {program_name}"

        return {
            "final_answer": final_response.model_dump_json(),
            "eligible": decision_eligible,
            "decision_trace": [t.model_dump() for t in frontend_trace],
            "decision_tree": decision_tree,
            "legislation_map": legislation_map,
            "trace_log": state.get("trace_log", []) + [status_msg],
        }

    except Exception as e:
        logger.exception(f"Rule Engine Failed: {type(e).__name__}")
        return {
            "final_answer": "{}",
            "eligible": False,
            "trace_log": state.get("trace_log", []) + [f"Error: {e}"],
        }


# --- NODE 5: RESOLVE SUBJECTIVE TERMS (Dynamic Threshold Resolution) ---
def resolve_subjective_terms_node(state: LegalResearchState) -> Dict[str, Any]:
    """
    Resolves subjective terms in extracted rules by:
    1. Identifying terms like 'genuine', 'prevailing', 'appropriate'
    2. Using LLM to derive concrete thresholds from context
    3. Assigning confidence levels based on source quality

    This is the key innovation - subjective legal terms get resolved dynamically!
    """
    logger.debug("--- RESOLVE SUBJECTIVE TERMS ---")

    extracted_rules_json = state.get("extracted_rules", "[]")
    user_query = state["query"]
    documents = state.get("documents", [])

    try:
        extracted_rules = json.loads(extracted_rules_json)
    except json.JSONDecodeError:
        extracted_rules = []

    if not extracted_rules:
        return {
            "resolved_rules": "[]",
            "trace_log": ["No rules to resolve. Skipping threshold resolution."],
        }

    # Combine documents for context
    docs_context = "\n\n---\n\n".join(documents[:5]) if documents else "No additional context available."

    # Default safety floors by country (used when LLM can't derive threshold)
    default_floors = """
COUNTRY-SPECIFIC DEFAULT FLOORS (use when no threshold can be derived from sources):
- Canada: salary >= $35,000 CAD, experience >= 2 years, education >= bachelor
- UK: salary >= £26,200 GBP (minimum for skilled worker), experience >= 2 years
- Germany: salary >= €45,300 EUR (Blue Card minimum), experience >= 2 years
- France: salary >= €35,000 EUR, experience >= 2 years
- Italy: salary >= €25,000 EUR, experience >= 2 years
- Japan: salary >= ¥3,000,000 JPY (~$20,000 USD), experience >= 3 years
- USA: salary >= $60,000 USD (H-1B prevailing wage floor), experience >= 2 years
"""

    resolution_prompt = f"""You are a Legal Threshold Resolver. Your task is to convert subjective legal terms into concrete, evaluable conditions.

EXTRACTED RULES (from legislation):
{json.dumps(extracted_rules, indent=2)}

USER SCENARIO:
{user_query}

LEGISLATIVE CONTEXT:
{docs_context}

{default_floors}

TASK: For each rule, identify subjective terms and resolve them to concrete thresholds:

1. IDENTIFY subjective terms (e.g., "genuine salary", "prevailing wage", "appropriate skills", "going rate")
2. SEARCH the legislative context for definitions, thresholds, or criteria
3. DERIVE a concrete threshold or condition based on:
   - Explicit values in the legislation (HIGH confidence)
   - Inferred from context like occupation or industry standards (MEDIUM confidence)
   - Default floors from the table above (LOW confidence)
4. PRESERVE conditions that already have concrete values (just pass them through)

OUTPUT FORMAT (JSON):
{{
  "resolved_rules": [
    {{
      "rule_id": "original rule ID",
      "description": "original description",
      "source_document": "original source",
      "source_section": "original section",
      "conditions": [
        {{
          "fact_key": "salary_offer",
          "operator": "gte",
          "value": 85000,
          "confidence": "HIGH|MEDIUM|LOW",
          "source": "Where this threshold came from",
          "original_term": "The original subjective term if resolved, null if already concrete"
        }}
      ],
      "outcome": {{ "eligible": true/false, "program": "...", "details": "..." }},
      "unresolved_terms": ["list of terms that couldn't be resolved - flag for human review"]
    }}
  ],
  "resolution_summary": "Brief explanation of key resolutions made"
}}

RESOLUTION STRATEGIES:
- "genuine salary" / "prevailing wage" / "going rate":
  → Search for occupation-specific salary data, or use 80% of typical market rate
  → For software engineers in Canada: ~$70,000-$120,000 range, use $66,000 as floor
  → For UK skilled worker: minimum £38,700 (general), or going rate from SOC code

- "substantial experience" / "significant work history":
  → Look for year requirements, default to 2-3 years if not found

- "appropriate skills" / "suitable qualifications":
  → Map to education_level: bachelor's degree minimum for most skilled worker visas

- "genuinely intend" / "genuine need":
  → Convert to boolean: has_job_offer = true, has_sponsor = true

- Terms with NO context and NO reasonable default:
  → Add to "unresolved_terms" and flag for human review

IMPORTANT:
- Pass through conditions that already have concrete numeric values (don't change them)
- For subjective wage terms, ALWAYS resolve to a numeric threshold (use defaults if needed)
- Include confidence level for EVERY resolved condition

JSON Output:"""

    try:
        model = genai.GenerativeModel(model_config.get_model("reasoning"))
        response = model.generate_content(resolution_prompt)
        response_text = response.text.strip()

        # Clean up response - extract JSON from markdown if needed
        response_text = clean_json_response(response_text)

        # Parse to validate JSON
        resolution_data = json.loads(response_text)
        resolved_rules = resolution_data.get("resolved_rules", [])
        resolution_summary = resolution_data.get("resolution_summary", "No summary provided")

        # Count resolutions by confidence
        high_conf = sum(1 for r in resolved_rules for c in r.get("conditions", []) if c.get("confidence") == "HIGH")
        med_conf = sum(1 for r in resolved_rules for c in r.get("conditions", []) if c.get("confidence") == "MEDIUM")
        low_conf = sum(1 for r in resolved_rules for c in r.get("conditions", []) if c.get("confidence") == "LOW")
        unresolved = sum(len(r.get("unresolved_terms", [])) for r in resolved_rules)

        trace_msg = f"Resolved {len(resolved_rules)} rules: {high_conf} HIGH, {med_conf} MEDIUM, {low_conf} LOW confidence. {unresolved} terms unresolved."
        if resolution_summary:
            trace_msg += f"\nSummary: {resolution_summary}"

        return {
            "resolved_rules": json.dumps(resolved_rules),
            "trace_log": [trace_msg],
        }

    except json.JSONDecodeError as e:
        logger.warning(f"JSON Parse Error in resolve_subjective_terms: {type(e).__name__}")
        # Fall back to using extracted rules as-is
        return {
            "resolved_rules": extracted_rules_json,
            "trace_log": [f"Threshold resolution failed (JSON error). Using raw extracted rules."],
        }
    except Exception as e:
        logger.exception(f"Threshold Resolution Error: {type(e).__name__}")
        # Fall back to using extracted rules as-is
        return {
            "resolved_rules": extracted_rules_json,
            "trace_log": [f"Threshold resolution error: {str(e)}. Using raw extracted rules."],
        }
