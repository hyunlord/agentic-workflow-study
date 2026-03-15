from __future__ import annotations

"""Ollama LLM client. OpenAI-compatible chat wrapper for local models."""

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = "http://localhost:11434"
    model: str = "qwen3.5:9b"
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 120

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("LLM_MODEL", "qwen3.5:9b"),
        )


class OllamaClient:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self.session = requests.Session()
        # Local Ollama traffic should not silently inherit proxy settings.
        self.session.trust_env = False

    @staticmethod
    def is_local_base_url(base_url: str) -> bool:
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
        return host in {"localhost", "127.0.0.1", "::1"}

    def is_available(self) -> bool:
        try:
            response = self.session.get(f"{self.config.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        response = self.session.get(f"{self.config.base_url}/api/tags", timeout=5)
        response.raise_for_status()
        return [model["name"] for model in response.json().get("models", [])]

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }
        response = self.session.post(
            f"{self.config.base_url}/api/chat",
            json=payload,
            timeout=kwargs.get("timeout", self.config.timeout),
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def chat_with_metadata(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }
        response = self.session.post(
            f"{self.config.base_url}/api/chat",
            json=payload,
            timeout=kwargs.get("timeout", self.config.timeout),
        )
        response.raise_for_status()
        data = response.json()
        return {
            "content": data["message"]["content"],
            "model": data.get("model", self.config.model),
            "eval_count": data.get("eval_count", 0),
            "eval_duration_ms": data.get("eval_duration", 0) / 1_000_000,
            "total_duration_ms": data.get("total_duration", 0) / 1_000_000,
        }
