import pytest

from src.ingestion import build_demo_index
from src.state import append_trace, create_initial_state
from src.state_validation import StateValidationError, validate_state
from src.workflow import run_workflow


def test_workflow_happy_path_returns_grounded_answer() -> None:
    retriever = build_demo_index()

    state = run_workflow(
        "What are the main goals of the workspace policy refresh?",
        retriever=retriever,
    )

    assert state["final_status"] == "answered"
    assert state["verification_result"].is_grounded is True
    assert len(state["trace"]) == 9
    assert all("latency" in entry for entry in state["trace"])
    assert all(isinstance(entry["latency"], float) for entry in state["trace"])
    assert all(entry["latency"] >= 0.0 for entry in state["trace"])
    assert any(citation["source"] == "workspace_policy_refresh.md" for citation in state["citations"])


def test_workflow_uses_tools_for_day_difference() -> None:
    retriever = build_demo_index()

    state = run_workflow(
        "How many days are in the pilot window?",
        retriever=retriever,
    )

    assert state["final_status"] == "answered"
    assert "25" in state["final_answer"]
    assert any(output["tool_name"] == "calculator" for output in state["tool_outputs"])


def test_workflow_abstains_for_out_of_scope_question() -> None:
    retriever = build_demo_index()

    state = run_workflow(
        "Who is the current CEO of the company?",
        retriever=retriever,
    )

    assert state["query_type"] == "insufficient_evidence_risk"
    assert state["final_status"] == "abstained"


def test_validate_state_raises_for_missing_required_keys() -> None:
    state = create_initial_state("What is the rollout date?")
    state["normalized_query"] = "what is the rollout date?"
    append_trace(
        state,
        "normalize_query",
        {
            "inputs": {"user_query": state["user_query"]},
            "outputs": {"normalized_query": state["normalized_query"]},
            "latency": 0.001,
        },
    )
    state["query_type"] = "simple_lookup"
    state["requires_tools"] = False
    append_trace(
        state,
        "classify_query",
        {
            "inputs": {"normalized_query": state["normalized_query"]},
            "outputs": {"query_type": state["query_type"], "requires_tools": state["requires_tools"]},
            "latency": 0.001,
        },
    )
    append_trace(
        state,
        "retrieve_docs",
        {
            "inputs": {"normalized_query": state["normalized_query"], "top_k": 5},
            "outputs": {"results": 1, "sources": ["ops_rollout_plan.md"]},
            "latency": 0.002,
        },
    )

    with pytest.raises(StateValidationError, match="retrieved_docs"):
        validate_state(state)
