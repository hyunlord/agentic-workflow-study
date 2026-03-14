from src.ingestion import build_demo_index
from src.planner_extended import PlanExecutor, PlanGenerator
from src.tools_extended import ToolCall, build_default_registry
from src.trace_debug import display_node_inputs, display_node_outputs, display_trace
from src.workflow import run_workflow


def test_plan_generator_and_executor_support_tutorial_examples() -> None:
    generator = PlanGenerator()
    plan = generator.generate_plan("Find the rollout date and summarize why it matters.", strategy="planner_executor")

    executor = PlanExecutor()
    executor.register_handler("retrieval", lambda step: {"status": "completed", "output": f"retrieved for {step['step_id']}"})
    executor.register_handler("tool", lambda step: {"status": "completed", "output": f"tool used for {step['step_id']}"})
    log = executor.execute(plan)

    assert len(plan) >= 3
    assert len(log) == len(plan)
    assert all(entry["status"] == "completed" for entry in log)


def test_tools_extended_registry_handles_structured_calls() -> None:
    registry = build_default_registry()

    calc_result = registry.call(ToolCall("calculator", {"expression": "2 + 3 * 4"}))
    search_result = registry.call(
        ToolCall(
            "search_tool",
            {"query": "rollout date", "documents": ["The launch date is May 5, 2025.", "Finance approved the pilot."]},
        )
    )

    assert "calculator" in registry.list_tools()
    assert calc_result.ok is True
    assert calc_result.output["result"] == 14
    assert search_result.ok is True
    assert search_result.output["results"][0]["score"] >= 0.0


def test_trace_debug_adds_latency_and_node_specific_views() -> None:
    retriever = build_demo_index(persist=False)
    state = run_workflow("What are the main goals of the workspace policy refresh?", retriever=retriever)

    trace_frame = display_trace(state["trace"], render=False)
    input_frame = display_node_inputs(state["trace"], "retrieve_docs", render=False)
    output_frame = display_node_outputs(state["trace"], "retrieve_docs", render=False)

    assert list(trace_frame.columns) == ["step", "node", "latency", "inputs", "outputs", "timestamp"]
    assert "retrieve_docs" in set(trace_frame["node"])
    assert trace_frame["latency"].notna().all()
    assert not input_frame.empty
    assert not output_frame.empty
