import os
import logging
import google.generativeai as genai
from .config import (
    LLM_FAST_MODEL as DEFAULT_FAST,
    LLM_REASONING_MODEL as DEFAULT_REASONING,
    LLM_VISION_MODEL as DEFAULT_VISION,
    LLM_AUDIO_MODEL as DEFAULT_AUDIO,
    TTS_MODEL as DEFAULT_TTS,
)

# No default API key - must be set via Governance Dashboard

logger = logging.getLogger(__name__)

class ModelConfig:
    def __init__(self):
        self.config = {
            "fast": DEFAULT_FAST,
            "reasoning": DEFAULT_REASONING,
            "vision": DEFAULT_VISION,
            "audio": DEFAULT_AUDIO,
            "tts": DEFAULT_TTS
        }
        self._custom_api_key: str | None = None

    def get_model(self, key: str) -> str:
        return self.config.get(key, DEFAULT_REASONING)

    def set_model(self, key: str, value: str):
        if key in self.config:
            self.config[key] = value
            logger.debug(f"ModelConfig: Updated '{key}' to '{value}'")
        else:
            logger.warning(f"ModelConfig: Unknown key '{key}'")

    def get_all(self):
        return self.config.copy()

    def set_api_key(self, key: str | None):
        """Set the API key (required - no default from .env)."""
        self._custom_api_key = key if key and key.strip() else None
        logger.debug(f"ModelConfig: API key {'configured' if self._custom_api_key else 'cleared'}")

    def get_api_key(self) -> str | None:
        """Get the API key. Returns None if not configured."""
        return self._custom_api_key

    def has_custom_api_key(self) -> bool:
        """Check if an API key is set."""
        return self._custom_api_key is not None

    def is_configured(self) -> bool:
        """Check if an API key is available."""
        return bool(self._custom_api_key)

    def ensure_configured(self) -> bool:
        """Configure genai with current API key. Returns True if configured."""
        key = self.get_api_key()
        if key:
            genai.configure(api_key=key)
            return True
        return False

# Singleton instance
model_config = ModelConfig()
