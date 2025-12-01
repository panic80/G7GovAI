// Environment configuration and constants

// Helper to get env vars with defaults
const getEnv = (key: string, defaultValue: string = ''): string => {
  // Vite uses import.meta.env
  const val = import.meta.env[key];
  return val || defaultValue;
};

export const CONFIG = {
  // AI Configuration
  GEMINI: {
    MODEL_NAME: getEnv('VITE_LLM_MODEL_NAME', 'gemini-2.5-flash-lite'),
    TTS_MODEL: getEnv('VITE_TTS_MODEL_NAME', 'gemini-2.5-flash-preview-tts'),
  },
  
  // Backend Services
  RAG: {
    BASE_URL: '/api', // Use local proxy to hide API key
    ENDPOINTS: {
      SEARCH: '/search',
    }
  },

  // Language & Localization
  DEFAULT_LANGUAGE: 'en',

  // Retrieval Configuration
  RETRIEVAL: {
    DEFAULT_LIMIT: 5,
    MAX_LIMIT: 50,
    SEMANTIC_THRESHOLD: 0.7,
  },

  // UI Constants
  UI: {
    TOAST_DURATION: 5000,    // 5 seconds
    DEBOUNCE_MS: 300,        // Search debounce
    MAX_FILE_SIZE_MB: 10,    // File upload limit
  },
};
