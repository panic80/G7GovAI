"""
Centralized constants for the GovAI backend.

All magic numbers, timeouts, limits, and shared configuration should be defined here.
"""

from typing import Dict, FrozenSet

# =============================================================================
# Server Configuration
# =============================================================================

DEFAULT_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000
DEFAULT_HOST = "0.0.0.0"

# =============================================================================
# HTTP Timeouts (seconds)
# =============================================================================

HTTP_TIMEOUT_DEFAULT = 10
HTTP_TIMEOUT_LONG = 30
HTTP_TIMEOUT_VERY_LONG = 60

# Connector-specific timeouts
CONNECTOR_TIMEOUT_DEFAULT = 15
CONNECTOR_TIMEOUT_LARGE_DATASET = 60

# =============================================================================
# Row Estimation (bytes per row for different formats)
# =============================================================================

BYTES_PER_ROW: Dict[str, int] = {
    'csv': 100,
    'json': 200,
    'xml': 300,
    'default': 150,
}

# =============================================================================
# Query and Input Limits
# =============================================================================

MAX_QUERY_LENGTH = 2000
MIN_QUERY_LENGTH = 1
MAX_PROMPT_LENGTH = 10000
MAX_TEXT_LENGTH = 50000  # For OCR/STT results

# Search limits
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 100

# =============================================================================
# Document Processing
# =============================================================================

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MAX_CHUNK_SIZE = 4000

# Batch sizes for processing
EMBEDDING_BATCH_SIZE = 100
CATEGORIZATION_BATCH_SIZE = 50

# =============================================================================
# Parallelism Configuration (Ingestion)
# =============================================================================

ANALYSIS_MAX_WORKERS = 100     # Concurrent threads for LLM analysis (flash-lite: 4000 RPM)
ANALYSIS_BATCH_SIZE = 50       # Items per Gemini analysis API call
EMBEDDING_MAX_WORKERS = 100    # Concurrent threads for embedding generation

# =============================================================================
# LLM Configuration
# =============================================================================

LLM_TEMPERATURES = {
    'deterministic': 0.0,
    'low': 0.1,
    'moderate': 0.2,
    'creative': 0.7,
}

# Token limits
MAX_INPUT_TOKENS = 30000
MAX_OUTPUT_TOKENS = 8000

# =============================================================================
# Supported Languages
# =============================================================================

SUPPORTED_LANGUAGES: FrozenSet[str] = frozenset({'en', 'fr'})
DEFAULT_LANGUAGE = 'en'

# =============================================================================
# File Types
# =============================================================================

ALLOWED_FILE_EXTENSIONS: FrozenSet[str] = frozenset({
    '.pdf', '.txt', '.csv', '.md', '.json', '.html'
})

ALLOWED_CONTENT_TYPES: FrozenSet[str] = frozenset({
    'application/pdf',
    'text/plain',
    'text/csv',
    'text/markdown',
    'application/json',
    'text/html',
})

ALLOWED_IMAGE_TYPES: FrozenSet[str] = frozenset({
    'application/pdf',
    'image/png',
    'image/jpeg',
})

ALLOWED_AUDIO_TYPES: FrozenSet[str] = frozenset({
    'audio/wav',
    'audio/mp3',
    'audio/webm',
    'audio/ogg',
    'audio/mp4',
})

# =============================================================================
# G7 Countries
# =============================================================================

G7_COUNTRIES = ('CA', 'US', 'UK', 'FR', 'DE', 'IT', 'JP')

COUNTRY_NAMES: Dict[str, str] = {
    'CA': 'Canada',
    'US': 'United States',
    'UK': 'United Kingdom',
    'FR': 'France',
    'DE': 'Germany',
    'IT': 'Italy',
    'JP': 'Japan',
}

# =============================================================================
# Search Strategy
# =============================================================================

SEARCH_STRATEGIES: FrozenSet[str] = frozenset({'relevance', 'diverse'})
DEFAULT_SEARCH_STRATEGY = 'relevance'
DEFAULT_DIVERSITY_LAMBDA = 0.6

# =============================================================================
# Program Types (AccessBridge)
# =============================================================================

PROGRAM_TYPES: FrozenSet[str] = frozenset({
    'general', 'immigration', 'benefits', 'housing', 'disability'
})
DEFAULT_PROGRAM_TYPE = 'general'

# =============================================================================
# Emergency Event Types (ForesightOps)
# =============================================================================

EMERGENCY_EVENT_TYPES: FrozenSet[str] = frozenset({
    'Snowstorm', 'Flood', 'Earthquake', 'Fire', 'None'
})

# =============================================================================
# Budget Limits (ForesightOps)
# =============================================================================

MAX_BUDGET = 1_000_000_000_000  # 1 trillion
MIN_BUDGET = 1
DEFAULT_BUDGET = 10_000_000  # $10M default
MAX_PLANNING_HORIZON_YEARS = 50
MIN_PLANNING_HORIZON_YEARS = 1
DEFAULT_PLANNING_HORIZON_YEARS = 5

# =============================================================================
# Priority Weights (ForesightOps)
# =============================================================================

DEFAULT_WEIGHT_RISK = 0.6
DEFAULT_WEIGHT_COVERAGE = 0.4
DEFAULT_WEIGHTS = {"risk": DEFAULT_WEIGHT_RISK, "coverage": DEFAULT_WEIGHT_COVERAGE}

# =============================================================================
# Confidence Thresholds
# =============================================================================

CONFIDENCE_HIGH_THRESHOLD = 0.9
CONFIDENCE_MEDIUM_THRESHOLD = 0.7
CONFIDENCE_LOW_THRESHOLD = 0.6
DEFAULT_CONFIDENCE = 0.5

# Solver confidence mapping
SOLVER_CONFIDENCE = {
    "OPTIMAL": 0.95,
    "FEASIBLE": 0.85,
    "GREEDY_FALLBACK": 0.70,
    "INFEASIBLE": 0.30,
}

# =============================================================================
# Optimization Solver
# =============================================================================

SOLVER_TIME_LIMIT_MS = 10000
SOLVER_TIME_LIMIT_FAST_MS = 3000
SOLVER_TIME_LIMIT_SLOW_MS = 5000
MIN_REGIONAL_EQUITY_PCT = 0.1  # 10% minimum per region

# =============================================================================
# Risk Thresholds
# =============================================================================

RISK_SCORE_HIGH_THRESHOLD = 0.6
RISK_SCORE_MEDIUM_THRESHOLD = 0.4

# =============================================================================
# Pagination
# =============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# =============================================================================
# Date Formats
# =============================================================================

DATE_FORMAT_ISO = "%Y-%m-%d"
DATETIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"

# =============================================================================
# File Upload/Processing
# =============================================================================

FILE_CHUNK_SIZE_BYTES = 1024 * 1024  # 1MB chunks for file reading
MAX_FILENAME_LENGTH = 255
MAX_FILE_SIZE_MB = 50  # Default max file size for uploads

# =============================================================================
# Search Engine
# =============================================================================

SEARCH_INITIAL_LIMIT = 100  # Initial retrieval limit before filtering
SEARCH_RESULTS_DEFAULT = 50  # Default final results
KEYWORD_SEARCH_LIMIT = 50  # Keyword search results limit

# Source diversity (throttling per source)
DEFAULT_MAX_CHUNKS_PER_SOURCE = 3
DATASET_MAX_CHUNKS_PER_SOURCE = 500

# =============================================================================
# Embedding
# =============================================================================

EMBEDDING_CACHE_SIZE = 1000  # LRU cache size for embeddings
EMBEDDING_DIMENSIONS = 768  # Default embedding dimensions

# =============================================================================
# Progress Tracking
# =============================================================================

PROGRESS_WEIGHTS: Dict[str, int] = {
    "reading": 10,
    "analyzing": 50,
    "embedding": 90,
    "complete": 100,
}

# =============================================================================
# Security
# =============================================================================

MAX_QUERY_LENGTH_SECURITY = 10000  # Hard security limit
RATE_LIMIT_SEARCH = "60/minute"
RATE_LIMIT_UPLOAD = "10/minute"
RATE_LIMIT_PURGE = "1/hour"

# =============================================================================
# Logging
# =============================================================================

LOG_FORMAT_JSON = "json"
LOG_FORMAT_TEXT = "text"
DEFAULT_LOG_LEVEL = "INFO"
