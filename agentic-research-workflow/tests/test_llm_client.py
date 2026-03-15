from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.config import RuntimeConfig
from src.llm_client import LLMConfig, OllamaClient


def test_llm_config_defaults() -> None:
    config = LLMConfig()

    assert config.base_url == "http://localhost:11434"
    assert config.model == "qwen3.5:9b"
    assert config.temperature == 0.1
    assert config.max_tokens == 2048
    assert config.timeout == 120


def test_llm_config_from_env_overrides_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://dgx.local:11434")
    monkeypatch.setenv("LLM_MODEL", "qwen3.5:32b")

    config = LLMConfig.from_env()

    assert config.base_url == "http://dgx.local:11434"
    assert config.model == "qwen3.5:32b"


@patch("src.llm_client.requests.Session")
def test_ollama_client_is_available_success(mock_session_class: Mock) -> None:
    session = Mock()
    session.get.return_value.status_code = 200
    mock_session_class.return_value = session

    client = OllamaClient()

    assert client.is_available() is True
    assert client.session is session
    assert session.trust_env is False
    session.get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)


@patch("src.llm_client.requests.Session")
def test_ollama_client_is_available_failure(mock_session_class: Mock) -> None:
    session = Mock()
    session.get.side_effect = RuntimeError("connection refused")
    mock_session_class.return_value = session

    client = OllamaClient()

    assert client.is_available() is False


@patch("src.llm_client.requests.Session")
def test_ollama_client_chat_parses_content(mock_session_class: Mock) -> None:
    session = Mock()
    response = Mock()
    response.json.return_value = {
        "message": {
            "content": "The rollout starts on May 5, 2025.",
        }
    }
    session.post.return_value = response
    mock_session_class.return_value = session

    client = OllamaClient()
    result = client.chat([{"role": "user", "content": "When is rollout?"}], max_tokens=128)

    assert result == "The rollout starts on May 5, 2025."
    response.raise_for_status.assert_called_once_with()


@patch("src.llm_client.requests.Session")
def test_ollama_client_chat_with_metadata_parses_fields(mock_session_class: Mock) -> None:
    session = Mock()
    response = Mock()
    response.json.return_value = {
        "message": {"content": "Grounded answer"},
        "model": "qwen3.5:9b",
        "eval_count": 321,
        "eval_duration": 25_000_000,
        "total_duration": 50_000_000,
    }
    session.post.return_value = response
    mock_session_class.return_value = session

    client = OllamaClient()
    result = client.chat_with_metadata([{"role": "user", "content": "Summarize"}], temperature=0.2)

    assert result == {
        "content": "Grounded answer",
        "model": "qwen3.5:9b",
        "eval_count": 321,
        "eval_duration_ms": 25.0,
        "total_duration_ms": 50.0,
    }
    response.raise_for_status.assert_called_once_with()


@patch("src.config.OllamaClient")
def test_runtime_config_auto_detect_sets_llm_fields(mock_client_class: Mock) -> None:
    mock_client = Mock()
    mock_client.is_available.return_value = True
    mock_client_class.return_value = mock_client

    config = RuntimeConfig.auto_detect()

    assert config.llm_model == "qwen3.5:9b"
    assert config.llm_base_url == "http://localhost:11434"
    assert config.llm_available is True
    mock_client.is_available.assert_called_once_with()


@patch("src.config.OllamaClient")
@patch("src.config.LLMConfig.from_env")
def test_runtime_config_auto_detect_skips_non_local_llm_probe(
    mock_from_env: Mock,
    mock_client_class: Mock,
) -> None:
    mock_from_env.return_value = LLMConfig(base_url="http://example.com:11434", model="qwen3.5:9b")
    mock_client_class.is_local_base_url.return_value = False

    config = RuntimeConfig.auto_detect()

    assert config.llm_base_url == "http://example.com:11434"
    assert config.llm_available is False
    mock_client_class.assert_not_called()
