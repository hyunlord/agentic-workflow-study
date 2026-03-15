from __future__ import annotations

import warnings

from src.synthesizer_llm import synthesize_answer_llm


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
        },
        {
            "doc_id": "rollout",
            "chunk_id": "rollout_chunk_1",
            "text": "The rollout plan explains training and execution steps.",
            "score": 0.73,
            "source": "ops_rollout_plan.md",
        },
    ]


def test_synthesize_answer_llm_uses_llm_response_and_parses_citations() -> None:
    client = StubClient(
        "The main goals are to reduce cost and standardize hybrid guidance. [workspace_policy_refresh.md]"
    )

    result = synthesize_answer_llm(
        query="What are the main goals of the workspace policy refresh?",
        query_type="simple_lookup",
        retrieved_docs=sample_docs(),
        tool_outputs=[],
        client=client,
    )

    assert "reduce cost" in result["draft_answer"]
    assert result["citations"] == [
        {
            "doc_id": "policy",
            "chunk_id": "policy_chunk_1",
            "source": "workspace_policy_refresh.md",
            "score": 0.91,
        }
    ]


def test_synthesize_answer_llm_falls_back_when_client_is_unavailable() -> None:
    client = StubClient("unused", available=False)

    with warnings.catch_warnings(record=True) as caught:
        result = synthesize_answer_llm(
            query="What are the main goals of the workspace policy refresh?",
            query_type="simple_lookup",
            retrieved_docs=sample_docs(),
            tool_outputs=[],
            client=client,
        )

    assert any("fallback" in str(warning.message).lower() for warning in caught)
    assert "Sources:" in result["draft_answer"]
    assert result["citations"][0]["source"] == "workspace_policy_refresh.md"


def test_synthesize_answer_llm_uses_default_citations_when_parsing_fails() -> None:
    client = StubClient("The rollout and policy documents should be read together.")

    result = synthesize_answer_llm(
        query="How is the rollout plan different from the policy refresh?",
        query_type="comparison",
        retrieved_docs=sample_docs(),
        tool_outputs=[],
        client=client,
    )

    assert len(result["citations"]) == 2
    assert result["citations"][0]["source"] == "workspace_policy_refresh.md"
    assert result["citations"][1]["source"] == "ops_rollout_plan.md"
