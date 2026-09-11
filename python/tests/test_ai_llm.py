"""Tests for LLMClient timeout + provider-error handling (backlog #4).

Before the fix, ``ai/llm.py`` created the OpenAI client with no timeout and no
retry bound, and read ``response.choices[0]`` blindly — so a router that answers
``200 OK`` with an error payload crashed confusingly, and a wedged endpoint could
hang a web request for the SDK's ~600s x its own retries.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ai.llm as llm  # noqa: E402
from ai.llm import LLMClient, provider_error  # noqa: E402


def _ok_response(content="hello"):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.choices[0].finish_reason = "stop"
    response.model = "test-model"
    response.usage = None
    return response


def _error_payload(etype="service_unavailable", message="model overloaded"):
    """HTTP 200 with no choices but a top-level error (a real router behaviour)."""
    response = MagicMock()
    response.choices = None
    response.model_extra = {"error": {"type": etype, "message": message}}
    return response


class TestClientConstruction:
    def test_timeout_and_retry_bounds_are_passed_to_sdk(self, monkeypatch):
        monkeypatch.delenv("OPENAI_TIMEOUT", raising=False)
        monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            client = LLMClient(api_key="k")
            mock_openai.assert_called_once_with(
                api_key="k",
                base_url=client.base_url,
                timeout=llm.DEFAULT_TIMEOUT_SECONDS,
                max_retries=0,
            )

    def test_timeout_configurable_via_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_TIMEOUT", "45")
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            client = LLMClient(api_key="k")
            assert client.timeout == 45.0
            assert mock_openai.call_args.kwargs["timeout"] == 45.0

    def test_explicit_timeout_argument_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_TIMEOUT", "45")
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            assert LLMClient(api_key="k", timeout=10).timeout == 10.0

    def test_max_retries_configurable_via_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MAX_RETRIES", "3")
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            assert LLMClient(api_key="k").max_retries == 3

    def test_no_client_without_api_key(self, monkeypatch):
        """Empty credentials must not construct an SDK client at all."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("ai.llm.OpenAI") as mock_openai:
            client = LLMClient(api_key=None)
            mock_openai.assert_not_called()
            assert client.is_available is False


class TestProviderErrorDetection:
    def test_returns_none_when_choices_present(self):
        assert provider_error(_ok_response()) is None

    def test_extracts_type_and_message_from_error_payload(self):
        message = provider_error(_error_payload("rate_limit", "slow down"))
        assert message is not None
        assert "rate_limit" in message
        assert "slow down" in message

    def test_flags_empty_choices_without_error_field(self):
        response = MagicMock()
        response.choices = []
        response.model_extra = {}
        message = provider_error(response)
        assert message is not None and "no choices" in message


class TestChat:
    def _client(self, monkeypatch, max_retries=1):
        monkeypatch.delenv("OPENAI_TIMEOUT", raising=False)
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            client = LLMClient(api_key="k", max_retries=max_retries)
        return client

    def test_success_returns_content_and_attempts(self, monkeypatch):
        client = self._client(monkeypatch)
        client._client.chat.completions.create.return_value = _ok_response("analysis text")
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] == "analysis text"
        assert result["finish_reason"] == "stop"
        assert result["attempts"] == 1

    def test_http200_error_payload_is_reported_not_crashing(self, monkeypatch):
        client = self._client(monkeypatch, max_retries=0)
        client._client.chat.completions.create.return_value = _error_payload()
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] is None
        assert result["finish_reason"] == "error"
        assert "service_unavailable" in result["error"]
        assert "overloaded" in result["error"]

    def test_transient_error_is_retried(self, monkeypatch):
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        client = self._client(monkeypatch, max_retries=2)
        client._client.chat.completions.create.side_effect = [
            _error_payload("service_unavailable", "busy"),
            _ok_response("recovered"),
        ]
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] == "recovered"
        assert result["attempts"] == 2
        assert client._client.chat.completions.create.call_count == 2

    def test_non_transient_error_is_not_retried(self, monkeypatch):
        client = self._client(monkeypatch, max_retries=2)
        client._client.chat.completions.create.side_effect = ValueError(
            "invalid_request_error: bad model"
        )
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] is None
        assert result["attempts"] == 1
        assert client._client.chat.completions.create.call_count == 1

    def test_exhausted_retries_return_structured_error(self, monkeypatch):
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        client = self._client(monkeypatch, max_retries=1)
        client._client.chat.completions.create.return_value = _error_payload()
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] is None
        assert result["attempts"] == 2
        assert result["error_type"] == "provider_error"
        assert client._client.chat.completions.create.call_count == 2

    def test_retry_skipped_when_budget_cannot_fit(self, monkeypatch):
        """A further attempt that cannot finish before the deadline is skipped.

        Simulates each request burning the full per-request timeout, so the
        bounded loop must stop early instead of stacking attempts forever.
        """
        clock = {"t": 1000.0}
        monkeypatch.setattr(llm.time, "monotonic", lambda: clock["t"])
        slept = []

        def fake_sleep(seconds):
            slept.append(seconds)
            clock["t"] += seconds

        monkeypatch.setattr(llm.time, "sleep", fake_sleep)

        client = self._client(monkeypatch, max_retries=2)
        client.timeout = 300.0  # budget = 300 * 3 attempts = 900s

        def slow_create(**kwargs):
            clock["t"] += 300.0  # every attempt consumes the whole request timeout
            return _error_payload("timed out", "Request timed out.")

        client._client.chat.completions.create.side_effect = slow_create
        result = client.chat([{"role": "user", "content": "x"}])

        # deadline = 1900. attempt 1 ends 1300 (2+300 fits) -> retry;
        # attempt 2 ends 1600, next would need 1600+4+300 = 1904 > 1900 -> stop.
        assert result["content"] is None
        assert client._client.chat.completions.create.call_count == 2
        assert result["attempts"] == 2
        assert slept == [2]

    def test_unconfigured_client_returns_error_dict(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("ai.llm.OpenAI"):
            client = LLMClient(api_key=None)
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] is None
        assert result["error_type"] == "not_configured"


class TestContentError:
    """Some routers leak their failure into the message CONTENT with HTTP 200.

    Observed live from router.bynara.id: every request answered in ~1s with
    ``choices[0].message.content == "[Error] upstream error"``. Stored verbatim
    it becomes a "successful" report and the recency debounce blocks a retry.
    """

    def test_flags_bracketed_error_prefix(self):
        message = llm.content_error("[Error] upstream error")
        assert message is not None and "upstream error" in message

    def test_flag_is_case_insensitive(self):
        assert llm.content_error("[ERROR] Upstream Error") is not None

    def test_flags_short_failure_phrase(self):
        assert llm.content_error("Upstream error, please retry later") is not None

    def test_real_analysis_is_never_flagged(self):
        report = "## Executive Summary\n" + ("[FACT] ROE 7%. " * 60)
        assert llm.content_error(report) is None

    def test_short_benign_answer_is_not_flagged(self):
        assert llm.content_error("OK") is None
        assert llm.content_error("The company reported growth this year.") is None

    def test_empty_content_returns_none(self):
        # Emptiness is handled by the caller, not misread as an error sentinel.
        assert llm.content_error(None) is None
        assert llm.content_error("   ") is None

    def test_upstream_error_is_transient_so_it_retries(self):
        assert llm._is_transient("[Error] upstream error") is True


class TestChatContentErrors:
    def _client(self, monkeypatch, max_retries=0):
        monkeypatch.delenv("OPENAI_TIMEOUT", raising=False)
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            return LLMClient(api_key="k", max_retries=max_retries)

    def test_error_content_is_reported_as_provider_error(self, monkeypatch):
        client = self._client(monkeypatch)
        client._client.chat.completions.create.return_value = _ok_response(
            "[Error] upstream error"
        )
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] is None
        assert result["error_type"] == "provider_error"
        assert "upstream error" in result["error"]

    def test_error_content_is_retried_then_reported(self, monkeypatch):
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        client = self._client(monkeypatch, max_retries=1)
        client._client.chat.completions.create.return_value = _ok_response(
            "[Error] upstream error"
        )
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["attempts"] == 2
        assert client._client.chat.completions.create.call_count == 2

    def test_empty_content_is_an_error(self, monkeypatch):
        client = self._client(monkeypatch)
        response = _ok_response("   ")
        # MagicMock auto-creates a truthy tool_calls, so clear it explicitly.
        response.choices[0].message.tool_calls = None
        client._client.chat.completions.create.return_value = response
        result = client.chat([{"role": "user", "content": "x"}])
        assert result["content"] is None
        assert "empty_content" in result["error"]

    def test_empty_content_with_tool_calls_is_allowed(self, monkeypatch):
        """A tool-call turn legitimately has no textual content."""
        client = self._client(monkeypatch)
        response = _ok_response(None)
        response.choices[0].message.tool_calls = [{"id": "call_1"}]
        client._client.chat.completions.create.return_value = response
        result = client.chat([{"role": "user", "content": "x"}], tools=[{"type": "function"}])
        assert result["content"] is None
        assert "error" not in result


class TestIsTransient:
    @pytest.mark.parametrize(
        "message",
        [
            "Request timed out.",
            "Error code: 503 - service_unavailable",
            "Rate limit reached for requests",
            "API connection error",
            "Bad Gateway",
        ],
    )
    def test_transient_markers_recognised(self, message):
        assert llm._is_transient(message) is True

    @pytest.mark.parametrize("message", ["invalid_request_error: bad model", "401 unauthorized"])
    def test_permanent_errors_not_transient(self, message):
        assert llm._is_transient(message) is False


class TestSharedHelperImported:
    def test_provider_error_reused_by_caller(self):
        """`provider_error` is importable so callers share one implementation."""
        from ai.researcher import provider_error as researcher_provider_error

        assert researcher_provider_error is provider_error

    def test_content_error_reused_by_caller(self):
        from ai.researcher import content_error as researcher_content_error

        assert researcher_content_error is llm.content_error


class TestModuleLevelIsLLMAvailable:
    def test_does_not_raise(self, monkeypatch):
        """Previously this imported a non-existent ``_llm_client`` (ImportError)."""
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            assert llm.is_llm_available() is True

    def test_false_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("ai.llm.OpenAI"):
            assert llm.is_llm_available() is False


class TestTwoTierModelRouting:
    def test_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL_STRONG", raising=False)
        monkeypatch.delenv("OPENAI_MODEL_FAST", raising=False)
        assert llm.resolve_model(llm.TIER_STRONG) == llm.DEFAULT_MODEL
        assert llm.resolve_model(llm.TIER_FAST) == llm.DEFAULT_MODEL

    def test_falls_back_to_openai_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-luna")
        monkeypatch.delenv("OPENAI_MODEL_STRONG", raising=False)
        monkeypatch.delenv("OPENAI_MODEL_FAST", raising=False)
        assert llm.resolve_model(llm.TIER_STRONG) == "gpt-luna"
        assert llm.resolve_model(llm.TIER_FAST) == "gpt-luna"

    def test_tier_specific_overrides(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-luna")
        monkeypatch.setenv("OPENAI_MODEL_STRONG", "gpt-strong")
        monkeypatch.setenv("OPENAI_MODEL_FAST", "gpt-fast")
        assert llm.resolve_model(llm.TIER_STRONG) == "gpt-strong"
        assert llm.resolve_model(llm.TIER_FAST) == "gpt-fast"

    def test_unknown_tier_uses_openai_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-luna")
        assert llm.resolve_model("unknown") == "gpt-luna"

    def test_llm_client_for_applies_tier_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("OPENAI_MODEL_FAST", "gpt-fast")
        with patch("ai.llm.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            client = llm.llm_client_for(llm.TIER_FAST)
        assert client.model == "gpt-fast"

    def test_researcher_defaults_to_strong_tier(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("OPENAI_MODEL_STRONG", "gpt-strong")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-luna")
        from ai.researcher import AIResearcher

        with patch("ai.researcher.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            researcher = AIResearcher()
        assert researcher.model == "gpt-strong"

    def test_researcher_explicit_model_kept(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("OPENAI_MODEL_STRONG", "gpt-strong")
        from ai.researcher import AIResearcher

        with patch("ai.researcher.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            researcher = AIResearcher(model="gpt-custom")
        assert researcher.model == "gpt-custom"
