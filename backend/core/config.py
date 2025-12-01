import os
from pathlib import Path
from dotenv import load_dotenv

# Load Environment
script_dir = Path(__file__).resolve().parent.parent
project_root = Path(__file__).resolve().parent.parent.parent
env_path_local = project_root / ".env.local"
env_path_main = project_root / ".env"

if env_path_local.exists():
    load_dotenv(dotenv_path=env_path_local)
elif env_path_main.exists():
    load_dotenv(dotenv_path=env_path_main)
else:
    load_dotenv()

# GEMINI_API_KEY - No longer loaded from environment
# Users must configure via Governance Dashboard UI
GEMINI_API_KEY = None  # Kept for backwards compatibility, always None

GOVAI_API_KEY = os.getenv("GOVAI_API_KEY")
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:5173"
)

# File Upload Limits
MAX_FILE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

# LLM Model Configuration
# Strategy:
# - FAST: High speed, lower cost. Good for routing, simple extraction, classification.
# - REASONING: High intelligence, complex reasoning. Good for synthesis, complex extraction, agent logic.
# - VISION: Multimodal capabilities for images/documents.
# - AUDIO: Multimodal capabilities for speech.

# Default to the latest stable/preview models known to work well
LLM_FAST_MODEL = os.getenv("LLM_FAST_MODEL", "gemini-2.5-flash-lite")
LLM_REASONING_MODEL = os.getenv("LLM_REASONING_MODEL", "gemini-2.5-pro")
LLM_VISION_MODEL = os.getenv("LLM_VISION_MODEL", "gemini-2.5-flash")
LLM_AUDIO_MODEL = os.getenv("LLM_AUDIO_MODEL", "gemini-2.5-flash")

# TTS (Text-to-Speech)
TTS_MODEL = os.getenv("TTS_MODEL", "gemini-2.5-flash-preview-tts")