from __future__ import annotations

import warnings

from src.verifier_llm import verify_grounding_llm


class StubClient:
    def __init__(self, response: str, available: bool = True, should_raise: bool = False):
        self.response = response
        self.available = available
        self.should_raise = should_raise

    def is_available(self) -> bool:
        return self.available

    def chat(self, messages: list[dict[str, str]], **kwargs: object) -> str:
        if self.should_raise:
            raise RuntimeError("ollama down")
        return self.response


def sample_docs() -> list[dict[str, object]]:
    return [
        {
            "doc_id": "policy",
            "chunk_id": "policy_chunk_1",
            "text": "The workspace policy refresh aims to reduce operating cost and standardize hybrid guidance.",
            "score": 0.91,
            "source": "workspace_policy_refresh.md",
        }
    ]


def test_verify_grounding_llm_parses_json_response() -> None:
    client = StubClient(
        '{"is_grounded": true, "coverage_score": 0.88, "unsupported_claims": [], "missing_aspects": []}'
    )

    result = verify_grounding_llm(
        query="What are the main goals of the workspace policy refresh?",
        draft_answer="The main goals are to reduce operating cost and standardize hybrid guidance.",
        retrieved_docs=sample_docs(),
        client=client,
    )

    assert result.is_grounded is True
    assert result.coverage_score == 0.88
    assert result.unsupported_claims == []
    assert result.missing_aspects == []


def test_verify_grounding_llm_falls_back_on_invalid_json() -> None:
    client = StubClient("not-json")

    with warnings.catch_warnings(record=True) as caught:
        result = verify_grounding_llm(
            query="What are the main goals of the workspace policy refresh?",
            draft_answer="The main goals are to reduce operating cost and standardize hybrid guidance.",
            retrieved_docs=sample_docs(),
            client=client,
        )

    assert any("fallback" in str(warning.message).lower() for warning in caught)
    assert result.is_grounded is True
    assert result.coverage_score > 0.0


def test_verify_grounding_llm_falls_back_on_connection_failure() -> None:
    client = StubClient("unused", should_raise=True)

    with warnings.catch_warnings(record=True) as caught:
        result = verify_grounding_llm(
            query="What are the main goals of the workspace policy refresh?",
            draft_answer="The main goals are to reduce operating cost and standardize hybrid guidance.",
            retrieved_docs=sample_docs(),
            client=client,
        )

    assert any("fallback" in str(warning.message).lower() for warning in caught)
    assert result.is_grounded is True
