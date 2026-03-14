from src.ingestion import build_demo_index
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
