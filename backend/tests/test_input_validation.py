"""
Input Validation Tests for GovAI API Schemas.

Tests all Pydantic schema validation rules.
Target: 100% coverage on api/schemas.py validation
"""

import pytest
from pydantic import ValidationError


class TestSearchRequestValidation:
    """Tests for SearchRequest schema validation."""

    def test_valid_search_request(self):
        """Valid search request should pass validation."""
        from api.schemas import SearchRequest

        request = SearchRequest(
            query="test query",
            language="en",
            limit=10,
            reference_date="2024-01-15",
            strategy="relevance",
            diversity_lambda=0.5,
        )
        assert request.query == "test query"
        assert request.language == "en"
        assert request.limit == 10

    def test_query_min_length(self):
        """Query must have at least 1 character."""
        from api.schemas import SearchRequest

        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="")
        assert "min_length" in str(exc_info.value) or "at least 1" in str(exc_info.value).lower()

    def test_query_max_length(self):
        """Query must not exceed 2000 characters."""
        from api.schemas import SearchRequest

        with pytest.raises(ValidationError):
            SearchRequest(query="x" * 2001)

    def test_language_enum(self):
        """Language must be 'en' or 'fr'."""
        from api.schemas import SearchRequest

        # Valid
        assert SearchRequest(query="test", language="en").language == "en"
        assert SearchRequest(query="test", language="fr").language == "fr"

        # Invalid
        with pytest.raises(ValidationError):
            SearchRequest(query="test", language="de")

    def test_limit_range(self):
        """Limit must be between 1 and 100."""
        from api.schemas import SearchRequest

        # Valid
        assert SearchRequest(query="test", limit=1).limit == 1
        assert SearchRequest(query="test", limit=100).limit == 100

        # Invalid - too low
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=0)

        # Invalid - too high
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=101)

    def test_reference_date_pattern(self):
        """Reference date must match YYYY-MM-DD pattern."""
        from api.schemas import SearchRequest

        # Valid
        assert SearchRequest(query="test", reference_date="2024-01-15").reference_date == "2024-01-15"

        # Invalid patterns
        invalid_dates = ["2024/01/15", "01-15-2024", "2024-1-15", "not-a-date"]
        for date in invalid_dates:
            with pytest.raises(ValidationError):
                SearchRequest(query="test", reference_date=date)

    def test_strategy_enum(self):
        """Strategy must be 'relevance' or 'diverse'."""
        from api.schemas import SearchRequest

        # Valid
        assert SearchRequest(query="test", strategy="relevance").strategy == "relevance"
        assert SearchRequest(query="test", strategy="diverse").strategy == "diverse"

        # Invalid
        with pytest.raises(ValidationError):
            SearchRequest(query="test", strategy="other")

    def test_diversity_lambda_range(self):
        """Diversity lambda must be between 0.0 and 1.0."""
        from api.schemas import SearchRequest

        # Valid
        assert SearchRequest(query="test", diversity_lambda=0.0).diversity_lambda == 0.0
        assert SearchRequest(query="test", diversity_lambda=1.0).diversity_lambda == 1.0
        assert SearchRequest(query="test", diversity_lambda=0.5).diversity_lambda == 0.5

        # Invalid - too low
        with pytest.raises(ValidationError):
            SearchRequest(query="test", diversity_lambda=-0.1)

        # Invalid - too high
        with pytest.raises(ValidationError):
            SearchRequest(query="test", diversity_lambda=1.1)

    def test_categories_and_themes_limits(self):
        """Categories and themes lists should have max length."""
        from api.schemas import SearchRequest

        # Valid - within limits
        request = SearchRequest(
            query="test",
            categories=["cat1", "cat2", "cat3"],
            themes=["theme1", "theme2"]
        )
        assert len(request.categories) == 3
        assert len(request.themes) == 2


class TestGovLensAgentRequestValidation:
    """Tests for GovLensAgentRequest schema validation."""

    def test_valid_govlens_request(self):
        """Valid GovLens request should pass validation."""
        from api.schemas import GovLensAgentRequest

        request = GovLensAgentRequest(
            query="What are the immigration requirements?",
            language="en",
            categories=["immigration"],
            themes=["work permit"]
        )
        assert request.query == "What are the immigration requirements?"

    def test_query_required(self):
        """Query is required."""
        from api.schemas import GovLensAgentRequest

        with pytest.raises(ValidationError):
            GovLensAgentRequest()

    def test_query_length_limits(self):
        """Query must be within length limits."""
        from api.schemas import GovLensAgentRequest

        # Too short
        with pytest.raises(ValidationError):
            GovLensAgentRequest(query="")

        # Too long
        with pytest.raises(ValidationError):
            GovLensAgentRequest(query="x" * 2001)


class TestAgentSearchRequestValidation:
    """Tests for AgentSearchRequest (LexGraph) schema validation."""

    def test_valid_agent_search_request(self):
        """Valid agent search request should pass validation."""
        from api.schemas import AgentSearchRequest

        request = AgentSearchRequest(
            query="Am I eligible for benefits?",
            language="fr",
            effective_date="2024-06-01"
        )
        assert request.effective_date == "2024-06-01"

    def test_effective_date_required(self):
        """Effective date is required."""
        from api.schemas import AgentSearchRequest

        with pytest.raises(ValidationError):
            AgentSearchRequest(query="test")

    def test_effective_date_format(self):
        """Effective date must be YYYY-MM-DD."""
        from api.schemas import AgentSearchRequest

        # Invalid format
        with pytest.raises(ValidationError):
            AgentSearchRequest(query="test", effective_date="2024/06/01")


class TestCapitalPlanRequestValidation:
    """Tests for CapitalPlanRequest schema validation."""

    def test_valid_capital_plan_request(self):
        """Valid capital plan request should pass validation."""
        from api.schemas import CapitalPlanRequest

        request = CapitalPlanRequest(
            budget=1000000,
            priorities={"risk": 0.6, "impact": 0.4}
        )
        assert request.budget == 1000000

    def test_budget_positive(self):
        """Budget must be positive."""
        from api.schemas import CapitalPlanRequest

        with pytest.raises(ValidationError):
            CapitalPlanRequest(budget=0, priorities={"risk": 1.0})

        with pytest.raises(ValidationError):
            CapitalPlanRequest(budget=-1000, priorities={"risk": 1.0})

    def test_budget_max_limit(self):
        """Budget must not exceed 1 trillion."""
        from api.schemas import CapitalPlanRequest

        # Valid - at limit
        request = CapitalPlanRequest(
            budget=1_000_000_000_000,
            priorities={"risk": 1.0}
        )
        assert request.budget == 1_000_000_000_000

        # Invalid - exceeds limit
        with pytest.raises(ValidationError):
            CapitalPlanRequest(
                budget=1_000_000_000_001,
                priorities={"risk": 1.0}
            )

    def test_priorities_not_empty(self):
        """Priorities cannot be empty."""
        from api.schemas import CapitalPlanRequest

        with pytest.raises(ValidationError):
            CapitalPlanRequest(budget=1000000, priorities={})

    def test_priorities_values_range(self):
        """Priority values must be between 0 and 1."""
        from api.schemas import CapitalPlanRequest

        # Invalid - negative value
        with pytest.raises(ValidationError):
            CapitalPlanRequest(budget=1000000, priorities={"risk": -0.1})

        # Invalid - value > 1
        with pytest.raises(ValidationError):
            CapitalPlanRequest(budget=1000000, priorities={"risk": 1.5})


class TestForesightAgentRequestValidation:
    """Tests for ForesightAgentRequest schema validation."""

    def test_valid_foresight_request(self):
        """Valid foresight request should pass validation."""
        from api.schemas import ForesightAgentRequest

        request = ForesightAgentRequest(
            query="Optimize budget allocation",
            budget_total=10_000_000,
            planning_horizon_years=5,
            weights={"risk": 0.6, "coverage": 0.4}
        )
        assert request.budget_total == 10_000_000

    def test_budget_total_range(self):
        """Budget total must be positive and within limits."""
        from api.schemas import ForesightAgentRequest

        # Invalid - zero
        with pytest.raises(ValidationError):
            ForesightAgentRequest(budget_total=0)

        # Invalid - negative
        with pytest.raises(ValidationError):
            ForesightAgentRequest(budget_total=-1000)

    def test_planning_horizon_range(self):
        """Planning horizon must be between 1 and 50 years."""
        from api.schemas import ForesightAgentRequest

        # Valid extremes
        assert ForesightAgentRequest(planning_horizon_years=1).planning_horizon_years == 1
        assert ForesightAgentRequest(planning_horizon_years=50).planning_horizon_years == 50

        # Invalid
        with pytest.raises(ValidationError):
            ForesightAgentRequest(planning_horizon_years=0)

        with pytest.raises(ValidationError):
            ForesightAgentRequest(planning_horizon_years=51)


class TestGenerateRequestValidation:
    """Tests for GenerateRequest schema validation."""

    def test_valid_generate_request(self):
        """Valid generate request should pass validation."""
        from api.schemas import GenerateRequest

        request = GenerateRequest(
            prompt="Generate a summary",
            temperature=0.5
        )
        assert request.prompt == "Generate a summary"

    def test_prompt_required(self):
        """Prompt is required."""
        from api.schemas import GenerateRequest

        with pytest.raises(ValidationError):
            GenerateRequest()

    def test_prompt_length(self):
        """Prompt must be within length limits."""
        from api.schemas import GenerateRequest, MAX_PROMPT_LENGTH

        # Too short (empty string)
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="")

        # Too long (exceeds MAX_PROMPT_LENGTH which is 100000)
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="x" * (MAX_PROMPT_LENGTH + 1))

    def test_temperature_range(self):
        """Temperature must be between 0 and 2."""
        from api.schemas import GenerateRequest

        # Valid
        assert GenerateRequest(prompt="test", temperature=0.0).temperature == 0.0
        assert GenerateRequest(prompt="test", temperature=2.0).temperature == 2.0

        # Invalid
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", temperature=-0.1)

        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", temperature=2.1)


class TestAccessBridgeRequestValidation:
    """Tests for AccessBridgeRequest schema validation."""

    def test_valid_access_bridge_request(self):
        """Valid access bridge request should pass validation."""
        from api.schemas import AccessBridgeRequest

        request = AccessBridgeRequest(
            raw_text_input="I need help with my application",
            program_type="immigration",
            language="en"
        )
        assert request.program_type == "immigration"

    def test_program_type_enum(self):
        """Program type must be a valid value."""
        from api.schemas import AccessBridgeRequest

        # Valid types
        valid_types = ["general", "immigration", "benefits", "housing", "disability"]
        for program in valid_types:
            request = AccessBridgeRequest(program_type=program)
            assert request.program_type == program

        # Invalid type
        with pytest.raises(ValidationError):
            AccessBridgeRequest(program_type="invalid")


class TestOcrRequestValidation:
    """Tests for OcrRequest schema validation."""

    def test_valid_ocr_request(self):
        """Valid OCR request should pass validation."""
        from api.schemas import OcrRequest

        request = OcrRequest(
            file_base64="SGVsbG8gV29ybGQ=",
            file_type="pdf",
            language="en"
        )
        assert request.file_type == "pdf"

    def test_file_base64_required(self):
        """File base64 is required."""
        from api.schemas import OcrRequest

        with pytest.raises(ValidationError):
            OcrRequest()

    def test_file_type_enum(self):
        """File type must be a valid value."""
        from api.schemas import OcrRequest

        # Valid types
        for file_type in ["pdf", "png", "jpg", "jpeg"]:
            request = OcrRequest(file_base64="test", file_type=file_type)
            assert request.file_type == file_type

        # Invalid type
        with pytest.raises(ValidationError):
            OcrRequest(file_base64="test", file_type="exe")


class TestSttRequestValidation:
    """Tests for SttRequest schema validation."""

    def test_valid_stt_request(self):
        """Valid STT request should pass validation."""
        from api.schemas import SttRequest

        request = SttRequest(
            audio_base64="SGVsbG8gV29ybGQ=",
            audio_format="wav",
            language="fr"
        )
        assert request.audio_format == "wav"

    def test_audio_format_enum(self):
        """Audio format must be a valid value."""
        from api.schemas import SttRequest

        # Valid formats
        for fmt in ["wav", "mp3", "webm", "ogg", "m4a"]:
            request = SttRequest(audio_base64="test", audio_format=fmt)
            assert request.audio_format == fmt

        # Invalid format
        with pytest.raises(ValidationError):
            SttRequest(audio_base64="test", audio_format="flac")


class TestEmergencySimRequestValidation:
    """Tests for EmergencySimRequest schema validation."""

    def test_valid_emergency_sim_request(self):
        """Valid emergency sim request should pass validation."""
        from api.schemas import EmergencySimRequest

        request = EmergencySimRequest(event_type="Snowstorm")
        assert request.event_type == "Snowstorm"

    def test_event_type_enum(self):
        """Event type must be a valid value."""
        from api.schemas import EmergencySimRequest

        # Valid types
        for event in ["Snowstorm", "Flood", "Earthquake", "Fire", "None"]:
            request = EmergencySimRequest(event_type=event)
            assert request.event_type == event

        # Invalid type
        with pytest.raises(ValidationError):
            EmergencySimRequest(event_type="Tornado")
