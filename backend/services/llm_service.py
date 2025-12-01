import google.generativeai as genai
import base64
import json
from typing import Dict, List, Any, Optional

from core.model_state import model_config


class LLMService:
    def generate_content(self, prompt: str, model_name: str, temperature: float, schema: Optional[Dict[str, Any]] = None, history: Optional[List[Dict[str, str]]] = None, context: Optional[str] = None) -> str:
        if not model_config.ensure_configured():
            raise ValueError("API key not configured. Please set your Gemini API key in the Governance Dashboard.")

        model = genai.GenerativeModel(model_name)
        generation_config = genai.types.GenerationConfig(temperature=temperature)

        if schema:
            generation_config.response_mime_type = "application/json"
            generation_config.response_schema = schema

        # Build System Prompt
        system_instruction = """You are GovLens, an expert AI assistant for the Canadian Government.
        
        CORE INSTRUCTIONS:
        1. Answer the user's question based ONLY on the provided context.
        2. If the answer is not in the context, say "I cannot find that information in the available documents."
        3. CITATIONS ARE MANDATORY. Every factual statement must be backed by a reference to the source document index.
           Format: "The bill proposes changes to the Criminal Code [1]."
           Use [1], [2], [3] corresponding to the source order.
        4. Be concise, professional, and neutral.
        5. If the user asks a follow-up question, use the conversation history to understand the context.
        6. DISAMBIGUATION: If the context contains multiple distinct legislative bills or entities with the same identifier (e.g., 'Bill C-3' from different years), you MUST list them separately in the answer, clearly identifying each by Year and Topic. Do not merge them into a single description.
        """

        formatted_context = ""
        if context:
            formatted_context = f"\n\n--- AVAILABLE SOURCES ---\n{context}\n-------------------------\n"

        formatted_history = ""
        if history:
            formatted_history = "\n--- CONVERSATION HISTORY ---\n"
            for msg in history:
                role = "User" if msg.get("role") == "user" else "GovLens"
                formatted_history += f"{role}: {msg.get('content', '')}\n"

        full_prompt = f"{system_instruction}{formatted_context}{formatted_history}\nUser: {prompt}\nGovLens:"

        response = model.generate_content(
            full_prompt, generation_config=generation_config
        )
        return response.text

    def generate_speech(self, text: str, language: str, model_name: str) -> str:
        if not model_config.ensure_configured():
            raise ValueError("API key not configured. Please set your Gemini API key in the Governance Dashboard.")

        model = genai.GenerativeModel(model_name)
        prompt_parts = [f"Say this specifically in {language}: {text}"]

        response = model.generate_content(
            prompt_parts,
            generation_config={
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {"prebuilt_voice_config": {"voice_name": "Kore"}}
                },
            },
        )

        if not response.parts:
            raise ValueError("No content parts returned")

        part = response.parts[0]
        if hasattr(part, "inline_data") and part.inline_data:
            return base64.b64encode(part.inline_data.data).decode("utf-8")
        else:
            raise ValueError("No inline audio data found in response")
