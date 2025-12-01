/**
 * Centralized constants for the GovAI frontend.
 *
 * All magic numbers, timeouts, limits, and shared data should be defined here.
 */

// =============================================================================
// Timing Constants (milliseconds)
// =============================================================================

/** Duration to show toast/feedback messages */
export const TOAST_DURATION_MS = 3000;

/** Duration to show copy-to-clipboard feedback */
export const COPY_FEEDBACK_MS = 2000;

/** Duration to highlight citations before clearing */
export const CITATION_HIGHLIGHT_MS = 2000;

/** Polling interval for dashboard refresh */
export const POLL_INTERVAL_MS = 5000;

/** Debounce delay for search input */
export const SEARCH_DEBOUNCE_MS = 300;

// =============================================================================
// Limits and Thresholds
// =============================================================================

/** Maximum query length for search */
export const MAX_QUERY_LENGTH = 2000;

/** Default number of search results */
export const DEFAULT_SEARCH_LIMIT = 5;

/** Maximum number of search results */
export const MAX_SEARCH_LIMIT = 100;

/** Maximum file size for uploads (10MB) */
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

/** Maximum number of files in a single upload batch */
export const MAX_UPLOAD_BATCH_SIZE = 10;

// =============================================================================
// LLM Configuration
// =============================================================================

/** Temperature settings for different LLM use cases */
export const LLM_TEMPERATURES = {
  /** For deterministic, reproducible outputs */
  DETERMINISTIC: 0.0,
  /** For slightly varied but consistent outputs */
  LOW_VARIATION: 0.1,
  /** For balanced creativity/consistency */
  MODERATE: 0.2,
  /** For more creative outputs */
  CREATIVE: 0.7,
} as const;

export type LLMTemperature = typeof LLM_TEMPERATURES[keyof typeof LLM_TEMPERATURES];

// =============================================================================
// G7 Country Data
// =============================================================================

/** Country code to flag emoji mapping */
export const COUNTRY_FLAGS: Record<string, string> = {
  CA: '🇨🇦',
  UK: '🇬🇧',
  FR: '🇫🇷',
  DE: '🇩🇪',
  IT: '🇮🇹',
  JP: '🇯🇵',
  US: '🇺🇸',
} as const;

/** Country code to full name mapping */
export const COUNTRY_NAMES: Record<string, string> = {
  CA: 'Canada',
  UK: 'United Kingdom',
  FR: 'France',
  DE: 'Germany',
  IT: 'Italy',
  JP: 'Japan',
  US: 'United States',
} as const;

/** List of G7 country codes in order */
export const G7_COUNTRIES = ['CA', 'US', 'UK', 'FR', 'DE', 'IT', 'JP'] as const;

export type G7CountryCode = typeof G7_COUNTRIES[number];

// =============================================================================
// Supported Languages
// =============================================================================

export const SUPPORTED_LANGUAGES = ['en', 'fr'] as const;

export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];

export const LANGUAGE_NAMES: Record<SupportedLanguage, string> = {
  en: 'English',
  fr: 'Français',
} as const;

// =============================================================================
// File Types
// =============================================================================

/** Allowed file extensions for document upload */
export const ALLOWED_FILE_EXTENSIONS = ['.pdf', '.txt', '.csv', '.md', '.json'] as const;

/** Allowed MIME types for document upload */
export const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'text/plain',
  'text/csv',
  'text/markdown',
  'application/json',
] as const;

/** Allowed image types for OCR */
export const ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg'] as const;

/** Allowed audio types for STT */
export const ALLOWED_AUDIO_TYPES = ['audio/wav', 'audio/mp3', 'audio/webm', 'audio/ogg', 'audio/mp4'] as const;

// =============================================================================
// API Endpoints
// =============================================================================

export const API_ENDPOINTS = {
  // Search
  SEARCH: '/search',
  FILTER_OPTIONS: '/filter-options',

  // Documents
  DOCUMENTS: '/documents',
  INGEST: '/ingest',

  // Knowledge Base
  KB_STATS: '/knowledge-base/stats',
  KB_INGEST: '/knowledge-base/ingest',
  KB_CONNECTORS: '/knowledge-base/connectors',
  KB_PURGE: '/knowledge-base/purge',
  KB_SAMPLE_DATA: '/knowledge-base/ingest-sample-data',

  // Agents
  AGENT_GOVLENS: '/agents/stream/govlens',
  AGENT_LEXGRAPH: '/agents/stream/lexgraph',
  AGENT_FORESIGHT: '/agents/stream/foresight',
  AGENT_ACCESSBRIDGE: '/agents/stream/accessbridge',

  // Foresight
  CAPITAL_PLAN: '/foresight/capital-plan',
  EMERGENCY_SIM: '/foresight/emergency-sim',

  // System
  HEALTH: '/health',
  AUDIT: '/audit',
  GENERATE: '/generate',
  TTS: '/tts',
  OCR: '/ocr',
  STT: '/stt',
  CONFIG_MODELS: '/config/models',
} as const;

// =============================================================================
// UI Constants
// =============================================================================

/** Default page sizes for pagination */
export const PAGE_SIZES = [10, 25, 50, 100] as const;

/** Animation duration for transitions (ms) */
export const ANIMATION_DURATION_MS = 200;

/** Z-index values for layering */
export const Z_INDEX = {
  DROPDOWN: 10,
  MODAL: 50,
  TOOLTIP: 100,
  TOAST: 200,
} as const;

// =============================================================================
// Citation Panel UI
// =============================================================================

/** Hover delay before showing citation panel (ms) */
export const HOVER_DELAY_MS = 150;

/** Assumed height for citation hover panel positioning (px) */
export const CITATION_PANEL_HEIGHT = 200;

/** Padding offset for citation panel positioning (px) */
export const CITATION_PANEL_PADDING = 10;

/** Max height for scrollable citations list (px) */
export const MAX_CITATIONS_HEIGHT = 600;

// =============================================================================
// Match Quality Thresholds
// =============================================================================

/** Thresholds for categorizing search match quality */
export const MATCH_THRESHOLDS = {
  /** Score >= 30% is considered Exact match */
  EXACT: 30,
  /** Score >= 15% is considered High match */
  HIGH: 15,
  /** Score >= 5% is considered Medium match */
  MEDIUM: 5,
} as const;

/** Match quality labels and colors */
export const MATCH_QUALITY_CONFIG = {
  EXACT: { label: 'Exact', color: 'bg-green-100 text-green-800' },
  HIGH: { label: 'High', color: 'bg-blue-100 text-blue-800' },
  MEDIUM: { label: 'Medium', color: 'bg-yellow-100 text-yellow-800' },
  LOW: { label: 'Low', color: 'bg-gray-100 text-gray-600' },
} as const;

// =============================================================================
// File Upload (must sync with backend)
// =============================================================================

/** File accept attribute for input elements */
export const FILE_ACCEPT_STRING = '.pdf,.txt,.md,.csv,.json,.html';

/** Max filename length */
export const MAX_FILENAME_LENGTH = 255;

// =============================================================================
// Security
// =============================================================================

/** Max query length (hard security limit) */
export const MAX_QUERY_LENGTH_SECURITY = 10000;

/** Purge confirmation string */
export const PURGE_CONFIRMATION_STRING = 'CONFIRM_PURGE_ALL_DATA';

// =============================================================================
// Progress Steps
// =============================================================================

/** Step names for progress tracking */
export const PROGRESS_STEPS = {
  CLASSIFY: 'classify',
  EXPAND: 'expand',
  RETRIEVE: 'retrieve',
  GRADE: 'grade',
  SYNTHESIZE: 'synthesize',
  COMPLETE: 'complete',
} as const;

// =============================================================================
// Audio Configuration
// =============================================================================

/** Sample rate for Gemini TTS output */
export const AUDIO_SAMPLE_RATE = 24000;

// =============================================================================
// Risk Thresholds (must sync with backend)
// =============================================================================

/** Risk score thresholds for UI styling */
export const RISK_THRESHOLDS = {
  HIGH: 0.6,
  MEDIUM: 0.4,
} as const;

// =============================================================================
// Confidence Thresholds (must sync with backend)
// =============================================================================

export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.9,
  MEDIUM: 0.7,
  LOW: 0.6,
} as const;

// =============================================================================
// Default Values (ForesightOps)
// =============================================================================

export const FORESIGHT_DEFAULTS = {
  BUDGET: 50_000_000,
  PLANNING_HORIZON_YEARS: 5,
  WEIGHT_RISK: 0.6,
  WEIGHT_COVERAGE: 0.4,
} as const;

// =============================================================================
// Retry/Error Handling
// =============================================================================

/** Maximum delay for exponential backoff (ms) */
export const MAX_RETRY_DELAY_MS = 30000;

/** Base delay for retry attempts (ms) */
export const BASE_RETRY_DELAY_MS = 1000;
