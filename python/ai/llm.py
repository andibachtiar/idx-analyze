"""
LLM Integration Module for idx-bei investment research platform.

Provides OpenAI-compatible API integration for AI-powered analysis.
Supports both OpenAI and compatible endpoints (Ollama, vLLM, LiteLLM, etc.)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMClient:
    """
    OpenAI-compatible LLM client.

    Supports any OpenAI-compatible API endpoint including:
    - OpenAI (gpt-4, gpt-3.5-turbo)
    - Ollama (local models)
    - vLLM (self-hosted)
    - LiteLLM proxy
    - Azure OpenAI
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key (defaults to OPENAI_API_KEY env var)
            base_url: API base URL (defaults to OpenAI)
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._client = None
        if OpenAI is not None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

    @property
    def client(self):
        """Get OpenAI client instance."""
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if LLM client is available."""
        return self._client is not None and bool(self.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional JSON schema for structured output
            tools: Optional function calling tools

        Returns:
            Response dict with 'content', 'finish_reason', etc.
        """
        if not self.is_available:
            return {
                "content": None,
                "finish_reason": "error",
                "error": "LLM client not configured. Set OPENAI_API_KEY environment variable.",
            }

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if response_format:
                kwargs["response_format"] = response_format

            if tools:
                kwargs["tools"] = tools

            response = self._client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            return {
                "content": choice.message.content,
                "finish_reason": choice.finish_reason,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }
        except Exception as e:
            return {
                "content": None,
                "finish_reason": "error",
                "error": str(e),
            }

    def analyze_with_prompt(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze using a prompt template.

        Args:
            prompt: The analysis prompt
            system_message: Optional system message
            output_format: Optional expected output format description

        Returns:
            Analysis result dict
        """
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})
        else:
            messages.append({
                "role": "system",
                "content": "You are a professional investment analyst. Provide evidence-based analysis with clear distinction between facts, interpretations, and speculation."
            })

        if output_format:
            messages.append({
                "role": "user",
                "content": f"Analyze the following data.{chr(10)}{prompt}{chr(10)}{chr(10)}Please format your response as: {output_format}"
            })
        else:
            messages.append({"role": "user", "content": prompt})

        return self.chat(messages)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_llm_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o",
) -> LLMClient:
    """Create an LLM client instance."""
    return LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def analyze_text(
    text: str,
    instruction: str,
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    """
    Quick analysis of text using LLM.

    Args:
        text: Input text to analyze
        instruction: What to analyze/extract
        model: Model name
        api_key: Optional API key
        base_url: Optional base URL

    Returns:
        Analysis result string
    """
    client = create_llm_client(api_key=api_key, base_url=base_url, model=model)
    result = client.analyze_with_prompt(
        prompt=text,
        output_format=instruction,
    )
    return result.get("content") or ""


def is_llm_available() -> bool:
    """Check if LLM is available."""
    from ai.llm import _llm_client
    return _llm_client.is_available if _llm_client else False
