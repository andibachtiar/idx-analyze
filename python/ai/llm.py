"""
LLM Integration Module for idx-bei investment research platform.

Provides OpenAI-compatible API integration for AI-powered analysis.
Supports both OpenAI and compatible endpoints (Ollama, vLLM, LiteLLM, etc.)
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Per-request ceiling. Without one the OpenAI SDK falls back to ~600s *plus* its
# own internal retries, so a wedged router looked like an infinitely hanging web
# request rather than a failure.
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_RETRIES = 1

# Two-tier model routing. High-reasoning tasks (comprehensive research reports,
# stock comparison, thesis validation) use the STRONG tier; quick, lower-reasoning
# summaries (fundamental/dividend/valuation/technical/screen/macro) use the FAST
# tier. Both fall back to OPENAI_MODEL (then DEFAULT_MODEL), so setting only
# OPENAI_MODEL keeps the previous single-model behaviour.
TIER_STRONG = "strong"
TIER_FAST = "fast"
DEFAULT_MODEL = "gpt-4o"
_TIER_ENV = {
    TIER_STRONG: "OPENAI_MODEL_STRONG",
    TIER_FAST: "OPENAI_MODEL_FAST",
}

# Failures worth retrying: rate limits, 5xx/overload, and connection/timeout
# errors. Anything else (bad request, unknown model, auth) fails immediately.
TRANSIENT_ERROR_MARKERS = (
    "service_unavailable",
    "temporarily unavailable",
    "unavailable",
    "rate_limit",
    "rate limit",
    "overloaded",
    "timed out",
    "timeout",
    "connection error",
    "connection refused",
    "api connection",
    "upstream error",
    "server error",
    "bad gateway",
    "502",
    "503",
    "504",
)


def resolve_model(tier: str = TIER_STRONG) -> str:
    """Resolve the model for a reasoning tier from the environment.

    Precedence per tier: ``OPENAI_MODEL_STRONG``/``OPENAI_MODEL_FAST``, then
    ``OPENAI_MODEL``, then :data:`DEFAULT_MODEL`. Returns the explicit
    ``OPENAI_MODEL`` for both tiers when no tier-specific var is set, so a
    single-model deployment keeps working unchanged.
    """
    env_name = _TIER_ENV.get(tier)
    model = os.environ.get(env_name) if env_name else None
    if not model:
        model = os.environ.get("OPENAI_MODEL")
    return model or DEFAULT_MODEL


def llm_client_for(tier: str = TIER_STRONG, **kwargs) -> "LLMClient":
    """Create an :class:`LLMClient` configured for a reasoning tier.

    Pass ``model`` to override the tier-resolved model, or any other
    :class:`LLMClient` constructor kwargs.
    """
    kwargs.setdefault("model", resolve_model(tier))
    return LLMClient(**kwargs)


def _is_transient(message: str) -> bool:
    """True when a provider/transport failure is likely to clear on retry."""
    low = (message or "").lower()
    return any(marker in low for marker in TRANSIENT_ERROR_MARKERS)


def provider_error(response: Any) -> Optional[str]:
    """Extract a provider error from an HTTP-200 error payload, else None.

    Some OpenAI-compatible routers answer ``200 OK`` with ``choices`` missing or
    empty plus a top-level ``error`` object. Reading ``response.choices[0]`` on
    such a payload raises a confusing ``TypeError: 'NoneType' object is not
    subscriptable`` that hides the real reason (e.g. model overloaded), so
    surface it explicitly.
    """
    if getattr(response, "choices", None):
        return None
    extra = getattr(response, "model_extra", None) or {}
    error = extra.get("error") if isinstance(extra, dict) else None
    if isinstance(error, dict):
        etype = str(error.get("type") or extra.get("type") or "provider_error")
        emessage = str(error.get("message") or "LLM returned no choices")
        return f"LLM provider error ({etype}): {emessage}"
    return "LLM provider error: response contained no choices"


# Some routers also report failure as HTTP 200 with the error text INSIDE
# ``choices[0].message.content`` (observed live: "[Error] upstream error" for
# every request). Stored verbatim it becomes a "successful" report whose body is
# an error string, and the 24h recency debounce then blocks a real retry.
CONTENT_ERROR_MAX_LENGTH = 200
_CONTENT_ERROR_PREFIX_RE = re.compile(r"^\s*\[error\]", re.IGNORECASE)
_CONTENT_ERROR_PHRASES = (
    "upstream error",
    "service_unavailable",
    "service unavailable",
    "rate limit",
    "internal server error",
    "bad gateway",
    "gateway timeout",
    "overloaded",
)


def content_error(content: Any) -> Optional[str]:
    """Return a provider error message if ``content`` is an error sentinel.

    Only unambiguous shapes count: an ``[Error] ...`` prefix, or a short reply
    (no markdown headings) that merely states a provider failure. A real
    analysis is long and structured, so it is never flagged.
    """
    text = "" if content is None else str(content).strip()
    if not text:
        return None
    if _CONTENT_ERROR_PREFIX_RE.match(text):
        return f"LLM provider error (upstream): {text}"
    if len(text) <= CONTENT_ERROR_MAX_LENGTH and "#" not in text:
        low = text.lower()
        if any(phrase in low for phrase in _CONTENT_ERROR_PHRASES):
            return f"LLM provider error (upstream): {text}"
    return None


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
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key (defaults to OPENAI_API_KEY env var)
            base_url: API base URL (defaults to OpenAI)
            model: Model name to use (defaults to OPENAI_MODEL env var)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Per-request timeout in seconds (defaults to OPENAI_TIMEOUT
                env var, else DEFAULT_TIMEOUT_SECONDS)
            max_retries: Extra attempts after the first for transient errors
                (defaults to LLM_MAX_RETRIES env var, else DEFAULT_MAX_RETRIES)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        # Plain LLMClient() defaults to the STRONG tier so direct construction
        # keeps resolving to OPENAI_MODEL as before; FAST endpoints opt in via
        # llm_client_for(TIER_FAST).
        self.model = model or resolve_model(TIER_STRONG)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = (
            float(timeout)
            if timeout is not None
            else float(os.environ.get("OPENAI_TIMEOUT", DEFAULT_TIMEOUT_SECONDS) or DEFAULT_TIMEOUT_SECONDS)
        )
        self.max_retries = (
            int(max_retries)
            if max_retries is not None
            else int(os.environ.get("LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES) or DEFAULT_MAX_RETRIES)
        )

        self._client = None
        # Only build a client when a key exists: OpenAI() raises on empty
        # credentials, and is_available must mean "usable", not "constructed".
        if OpenAI is not None and self.api_key:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                # Retries are handled in chat() so the *total* wait stays bounded
                # by the budget below instead of being multiplied by SDK retries.
                max_retries=0,
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

        Transient provider failures (overload, rate limit, timeouts) are retried
        with backoff, bounded by a total time budget so a wedged endpoint cannot
        hang a request indefinitely. An HTTP-200 error payload is reported as a
        provider error rather than a crash on ``choices[0]``.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional JSON schema for structured output
            tools: Optional function calling tools

        Returns:
            Response dict with 'content', 'finish_reason', etc. On failure:
            'content' is None plus 'error', 'error_type' and 'attempts'.
        """
        if not self.is_available:
            return {
                "content": None,
                "finish_reason": "error",
                "error_type": "not_configured",
                "error": "LLM client not configured. Set OPENAI_API_KEY environment variable.",
            }

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

        # Hard ceiling on wall-clock for this logical call, so retries cannot
        # compound into minutes of silence.
        deadline = time.monotonic() + self.timeout * (self.max_retries + 1)
        last_error = "LLM call failed"
        last_type = "provider_error"
        attempts = 0

        for attempt in range(self.max_retries + 1):
            attempts += 1
            try:
                response = self._client.chat.completions.create(**kwargs)
                message = provider_error(response)
                if message is None:
                    choice = response.choices[0]
                    content = choice.message.content
                    tool_calls = getattr(choice.message, "tool_calls", None)
                    if not (content or "").strip() and not tool_calls:
                        message = "LLM provider error (empty_content): response returned no content"
                    else:
                        message = content_error(content)
                    if message is None:
                        return {
                            "content": content,
                            "finish_reason": choice.finish_reason,
                            "model": response.model,
                            "usage": {
                                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                                "total_tokens": response.usage.total_tokens if response.usage else 0,
                            },
                            "attempts": attempts,
                        }
                last_error, last_type = message, "provider_error"
            except Exception as exc:
                last_error, last_type = str(exc), type(exc).__name__

            if not _is_transient(last_error) or attempt >= self.max_retries:
                break
            delay = 2 * (attempt + 1)
            # Skip the retry if it could not complete before the budget expires.
            if time.monotonic() + delay + self.timeout > deadline:
                break
            print(
                f"LLM call failed ({last_error}); retrying in {delay}s "
                f"(attempt {attempts}/{self.max_retries + 1})"
            )
            time.sleep(delay)

        return {
            "content": None,
            "finish_reason": "error",
            "error_type": last_type,
            "error": last_error,
            "attempts": attempts,
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
    timeout: Optional[float] = None,
) -> LLMClient:
    """Create an LLM client instance."""
    return LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
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
    """Check if LLM is available.

    Note: this is ``ai.llm``'s own helper. ``ai.llm_config.is_llm_available`` and
    ``ai.config.is_llm_available`` are separate implementations for their own
    config objects.
    """
    return LLMClient().is_available
