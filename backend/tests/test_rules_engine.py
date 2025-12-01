import datetime
from rules import (
    DynamicFacts,
    Rule,
    RuleMetadata,
    RuleCondition,
    evaluate_rules,
)


def test_engine():
    print("--- Testing Deterministic Rule Engine ---")

    # 1. Setup Rules (Same as Demo KB)
    rules = [
        Rule(
            rule_id="GTS-001",
            description="Global Talent Stream Eligibility",
            metadata=RuleMetadata(
                source_id="Immigration-Act-2024",
                section="s.23(b)",
                effective_start=datetime.date(2024, 1, 1),
                effective_end=datetime.date(2026, 12, 31),
                jurisdiction="Federal",
                doc_type="Regulation",
                priority=100,
            ),
            conditions=[
                RuleCondition(fact_key="has_job_offer", operator="eq", value=True),
                RuleCondition(
                    fact_key="applicant_role", operator="contains", value="engineer"
                ),
            ],
            outcome={"eligible": True, "program": "Global Talent Stream"},
        )
    ]

    # 2. Test Case A: Success
    facts_pass = DynamicFacts(
        facts={
            "applicant_role": "Software Engineer",
            "has_job_offer": True,
            "income": 90000,
        },
        extraction_confidence=0.95,
    )

    result_pass = evaluate_rules(facts_pass, rules, "2025-06-01")
    print(f"\n[Test A] Expect Success: {result_pass.status}")
    assert result_pass.status == "success"
    assert result_pass.decision["eligible"] is True

    # 3. Test Case B: Missing Fact (has_job_offer)
    facts_missing = DynamicFacts(
        facts={
            "applicant_role": "Software Engineer",
            # has_job_offer is MISSING
            "income": 90000,
        },
        extraction_confidence=0.95,
    )

    result_missing = evaluate_rules(facts_missing, rules, "2025-06-01")
    print(f"\n[Test B] Expect Pending More Info: {result_missing.status}")
    print(f"Missing Fields: {result_missing.missing_facts}")
    # New behavior: missing facts returns "pending_more_info" with optimistic eligibility
    assert result_missing.status == "pending_more_info"
    assert "has_job_offer" in result_missing.missing_facts

    # 4. Test Case C: Condition Not Met (role doesn't contain "engineer")
    facts_fail = DynamicFacts(
        facts={
            "applicant_role": "Artist",  # Not an engineer
            "has_job_offer": True,
        },
        extraction_confidence=0.95,
    )

    result_fail = evaluate_rules(facts_fail, rules, "2025-06-01")
    print(f"\n[Test C] Expect Failed Requirement: {result_fail.status}")
    # New behavior: explicit failure returns "failed_requirement"
    assert result_fail.status == "failed_requirement"
    assert result_fail.decision["eligible"] is False

    # 5. Test Case D: Low Confidence
    facts_low_conf = DynamicFacts(
        facts={
            "applicant_role": "Engineer?",
            "has_job_offer": True,
        },
        extraction_confidence=0.4,  # Too low
    )

    result_low_conf = evaluate_rules(
        facts_low_conf, rules, "2025-06-01", min_confidence=0.7
    )
    print(f"\n[Test D] Expect Confidence Failure: {result_low_conf.status}")
    assert result_low_conf.status == "confidence_too_low"

    print("\nAll deterministic tests passed!")


if __name__ == "__main__":
    test_engine()
