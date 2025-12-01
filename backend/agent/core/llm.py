"""
Unified LLM Service

Provides a single interface for all LLM operations across agents.
Supports both sync and async calls, with configurable model selection.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
# Removed lru_cache to allow dynamic model switching
# from functools import lru_cache

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from core.model_state import model_config

# Load environment
load_dotenv()

# API key is now managed via model_config (set via Governance Dashboard)
# No longer loaded from environment at startup


# Default temperature
DEFAULT_TEMPERATURE = 0.1


class LLMService:
    """
    Unified LLM service for all agent operations.

    Provides both direct genai access and LangChain-compatible interface.
    Uses lazy initialization - LLM clients created on first use.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        api_key: Optional[str] = None
    ):
        # Dynamic default
        self.model_name = model or model_config.get_model("reasoning")
        self.temperature = temperature
        # Use provided key, or get from model_config
        self._api_key = api_key

        # Lazy initialization - created on first use
        self._genai_model = None
        self._langchain_llm = None

    def _get_api_key(self) -> str:
        """Get API key from provided value or model_config."""
        if self._api_key:
            return self._api_key
        key = model_config.get_api_key()
        if not key:
            raise ValueError("API key not configured. Please set your Gemini API key in the Governance page.")
        return key

    def _ensure_initialized(self):
        """Lazy initialize LLM clients on first use."""
        if self._genai_model is None:
            api_key = self._get_api_key()
            genai.configure(api_key=api_key)
            self._genai_model = genai.GenerativeModel(self.model_name)
            self._langchain_llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=api_key
            )

    @property
    def langchain(self) -> ChatGoogleGenerativeAI:
        """Get LangChain-compatible LLM for chain composition."""
        self._ensure_initialized()
        return self._langchain_llm

    def generate_sync(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> str:
        """
        Synchronous text generation.

        Args:
            prompt: The prompt text
            temperature: Override default temperature
            json_mode: If True, hints model to return JSON

        Returns:
            Generated text response
        """
        try:
            self._ensure_initialized()
            config = {
                "temperature": temperature if temperature is not None else self.temperature
            }
            if json_mode:
                config["response_mime_type"] = "application/json"

            response = self._genai_model.generate_content(
                prompt,
                generation_config=config
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM Error: {type(e).__name__}")
            return ""

    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> str:
        """
        Asynchronous text generation.

        Args:
            prompt: The prompt text
            temperature: Override default temperature
            json_mode: If True, hints model to return JSON

        Returns:
            Generated text response
        """
        # Wrap sync call in thread for true async
        return await asyncio.to_thread(
            self.generate_sync,
            prompt,
            temperature,
            json_mode
        )

    async def invoke_chain(
        self,
        prompt_template: str,
        variables: Dict[str, Any],
        output_parser: Optional[Any] = None
    ) -> Any:
        """
        Invoke a LangChain-style prompt chain.

        Args:
            prompt_template: Template string with {variables}
            variables: Dict of variable values
            output_parser: Optional parser (e.g., JsonOutputParser)

        Returns:
            Parsed response or raw content
        """
        self._ensure_initialized()
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=list(variables.keys())
        )

        if output_parser:
            chain = prompt | self._langchain_llm | output_parser
        else:
            chain = prompt | self._langchain_llm

        result = await chain.ainvoke(variables)

        # If no parser, extract content from AIMessage
        if output_parser is None and hasattr(result, 'content'):
            return result.content
        return result

    def invoke_chain_sync(
        self,
        prompt_template: str,
        variables: Dict[str, Any],
        output_parser: Optional[Any] = None
    ) -> Any:
        """Synchronous version of invoke_chain."""
        self._ensure_initialized()
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=list(variables.keys())
        )

        if output_parser:
            chain = prompt | self._langchain_llm | output_parser
        else:
            chain = prompt | self._langchain_llm

        result = chain.invoke(variables)

        if output_parser is None and hasattr(result, 'content'):
            return result.content
        return result


# No longer cached to allow dynamic model switching
def get_llm(
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE
) -> LLMService:
    """
    Get an LLM service instance.
    """
    return LLMService(model=model, temperature=temperature)


# Convenience function matching old pattern
def get_llm_response(prompt: str, temperature: float = 0.1, json_mode: bool = False) -> str:
    """
    Quick helper for simple text generation.

    Maintains backward compatibility with existing code.
    """
    llm = get_llm()
    return llm.generate_sync(prompt, temperature=temperature, json_mode=json_mode)
