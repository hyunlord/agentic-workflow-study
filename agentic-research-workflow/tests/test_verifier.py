from src.verifier import verify_grounding


def test_verify_grounding_flags_missing_evidence() -> None:
    result = verify_grounding(
        query="What changed?",
        draft_answer="The company introduced a robotics program.",
        retrieved_docs=[],
    )

    assert result.is_grounded is False
    assert result.coverage_score == 0.0
    assert "No retrieved evidence" in result.unsupported_claims


def test_verify_grounding_passes_grounded_answer() -> None:
    result = verify_grounding(
        query="What is the pilot timeline?",
        draft_answer="The rollout pilot begins on March 10, 2025 and ends on April 4, 2025.",
        retrieved_docs=[
            {
                "doc_id": "ops_rollout_plan",
                "chunk_id": "ops_rollout_plan_chunk_1",
                "text": "The rollout pilot begins on March 10, 2025 and ends on April 4, 2025.",
                "source": "ops_rollout_plan.md",
                "score": 0.91,
            }
        ],
    )

    assert result.is_grounded is True
    assert result.coverage_score > 0.7
