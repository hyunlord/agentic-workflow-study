from src.classifier import classify_query


def test_classify_detects_comparison_queries() -> None:
    result = classify_query("What is the difference between the launch plan and the policy memo?")

    assert result["query_type"] == "comparison"
    assert result["requires_tools"] is False


def test_classify_detects_tool_friendly_questions() -> None:
    result = classify_query("How many days passed between the pilot launch and the policy update?")

    assert result["query_type"] == "multi_hop"
    assert result["requires_tools"] is True
