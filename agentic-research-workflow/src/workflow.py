from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from src.classifier import classify_query
from src.config import DEFAULT_TOP_K
from src.fallback import fallback_or_finalize
from src.memory import (
    LongTermMemory,
    ShortTermMemory,
    VectorMemory,
    memory_results_to_docs,
    retrieve_relevant_memories,
    selective_memory_update,
)
from src.planner import make_plan
from src.schemas import ToolRequest
from src.state import AgentState, append_trace, create_initial_state, record_error
from src.synthesizer import build_baseline_answer, synthesize_answer
from src.tools import execute_tool_requests, plan_tool_requests
from src.utils import normalize_text, write_json
from src.verifier import verify_grounding


def normalize_query_node(state: AgentState) -> None:
    state["normalized_query"] = normalize_text(state["user_query"])
    append_trace(
        state,
        "normalize_query",
        {
            "inputs": {"user_query": state["user_query"]},
            "outputs": {"normalized_query": state["normalized_query"]},
        },
    )


def classify_query_node(state: AgentState) -> None:
    result = classify_query(state["normalized_query"])
    state["query_type"] = str(result["query_type"])
    state["requires_tools"] = bool(result["requires_tools"])
    append_trace(
        state,
        "classify_query",
        {
            "inputs": {"normalized_query": state["normalized_query"]},
            "outputs": result,
        },
    )


def make_plan_node(state: AgentState) -> None:
    state["plan"] = make_plan(state["query_type"])
    append_trace(
        state,
        "make_plan",
        {
            "inputs": {"query_type": state["query_type"]},
            "outputs": {"plan": state["plan"]},
        },
    )


def retrieve_docs_node(state: AgentState, retriever: Any, top_k: int) -> None:
    state["retrieved_docs"] = retriever.search(state["normalized_query"], top_k=top_k)
    append_trace(
        state,
        "retrieve_docs",
        {
            "inputs": {"normalized_query": state["normalized_query"], "top_k": top_k},
            "outputs": {
                "results": len(state["retrieved_docs"]),
                "sources": [doc["source"] for doc in state["retrieved_docs"]],
            },
        },
    )


def retrieve_memories_node(
    state: AgentState,
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    top_k: int = 3,
    include_memories_in_context: bool = False,
) -> None:
    state["retrieved_memories"] = retrieve_relevant_memories(
        query=state["normalized_query"],
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        vector_memory=vector_memory,
        top_k=top_k,
    )
    if include_memories_in_context and state["retrieved_memories"]:
        state["retrieved_docs"] = [*state["retrieved_docs"], *memory_results_to_docs(state["retrieved_memories"])]
    append_trace(
        state,
        "retrieve_memories",
        {
            "inputs": {
                "normalized_query": state["normalized_query"],
                "memory_top_k": top_k,
                "include_memories_in_context": include_memories_in_context,
            },
            "outputs": {
                "memory_count": len(state["retrieved_memories"]),
                "memory_types": [memory["memory_type"] for memory in state["retrieved_memories"]],
            },
        },
    )


def decide_tools_node(state: AgentState) -> None:
    requests = plan_tool_requests(state["normalized_query"], state["query_type"], state["retrieved_docs"])
    state["tool_requests"] = [request.to_dict() for request in requests]
    append_trace(
        state,
        "decide_tools",
        {
            "inputs": {
                "normalized_query": state["normalized_query"],
                "query_type": state["query_type"],
                "retrieved_doc_count": len(state["retrieved_docs"]),
            },
            "outputs": {
                "requires_tools": state["requires_tools"],
                "tool_requests": state["tool_requests"],
            },
        },
    )


def run_tools_node(state: AgentState) -> None:
    requests = [ToolRequest(**request) for request in state["tool_requests"]]
    outputs = execute_tool_requests(requests)
    state["tool_outputs"] = [output.to_dict() for output in outputs]
    append_trace(
        state,
        "run_tools",
        {
            "inputs": {"tool_requests": state["tool_requests"]},
            "outputs": {"tool_outputs": state["tool_outputs"]},
        },
    )


def synthesize_answer_node(state: AgentState) -> None:
    result = synthesize_answer(
        query=state["normalized_query"],
        query_type=state["query_type"],
        retrieved_docs=state["retrieved_docs"],
        tool_outputs=state["tool_outputs"],
    )
    state["draft_answer"] = result["draft_answer"]
    state["citations"] = result["citations"]
    append_trace(
        state,
        "synthesize_answer",
        {
            "inputs": {
                "query_type": state["query_type"],
                "retrieved_doc_count": len(state["retrieved_docs"]),
                "tool_output_count": len(state["tool_outputs"]),
            },
            "outputs": {"draft_answer": state["draft_answer"], "citations": state["citations"]},
        },
    )


def verify_grounding_node(state: AgentState) -> None:
    state["verification_result"] = verify_grounding(
        query=state["normalized_query"],
        draft_answer=state["draft_answer"],
        retrieved_docs=state["retrieved_docs"],
        tool_outputs=state["tool_outputs"],
    )
    append_trace(
        state,
        "verify_grounding",
        {
            "inputs": {"draft_answer": state["draft_answer"]},
            "outputs": state["verification_result"].to_dict(),
        },
    )


def fallback_or_finalize_node(state: AgentState) -> None:
    result = fallback_or_finalize(
        query=state["normalized_query"],
        query_type=state["query_type"],
        draft_answer=state["draft_answer"],
        verification_result=state["verification_result"],
    )
    state["final_answer"] = result["final_answer"]
    state["final_status"] = result["final_status"]
    append_trace(
        state,
        "fallback_or_finalize",
        {
            "inputs": {
                "query_type": state["query_type"],
                "coverage_score": state["verification_result"].coverage_score,
                "is_grounded": state["verification_result"].is_grounded,
            },
            "outputs": result,
        },
    )


WORKFLOW_STEPS = (
    normalize_query_node,
    classify_query_node,
    make_plan_node,
    retrieve_docs_node,
    decide_tools_node,
    run_tools_node,
    synthesize_answer_node,
    verify_grounding_node,
    fallback_or_finalize_node,
    )


def update_memory_node(
    state: AgentState,
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    threshold: float = 0.55,
) -> None:
    memory_updates: list[dict[str, Any]] = []

    if short_term_memory is not None:
        memory_updates.append(
            {
                "memory_type": "short_term",
                "event": short_term_memory.append_event(
                    "user_query",
                    state["user_query"],
                    {"query_type": state["query_type"]},
                ),
            }
        )
        memory_updates.append(
            {
                "memory_type": "short_term",
                "event": short_term_memory.append_event(
                    "assistant_answer",
                    state["final_answer"],
                    {"final_status": state["final_status"]},
                ),
            }
        )

    if long_term_memory is not None or vector_memory is not None:
        memory_key = "_".join(normalize_text(state["user_query"]).lower().split())[:48] or "memory_entry"
        decision = selective_memory_update(
            text=f"Question: {state['user_query']} Answer: {state['final_answer']}",
            key=memory_key,
            long_term_memory=long_term_memory,
            vector_memory=vector_memory,
            threshold=threshold,
            category="interaction",
            metadata={"source": "agent", "query_type": state["query_type"]},
        )
        memory_updates.append(decision)

    state["memory_updates"] = memory_updates
    append_trace(
        state,
        "update_memory",
        {
            "inputs": {
                "final_status": state["final_status"],
                "threshold": threshold,
            },
            "outputs": {
                "memory_updates": state["memory_updates"],
            },
        },
    )


def run_workflow(
    query: str,
    retriever: Any,
    top_k: int = DEFAULT_TOP_K,
    trace_path: Path | None = None,
) -> AgentState:
    state = create_initial_state(query)

    try:
        normalize_query_node(state)
        classify_query_node(state)
        make_plan_node(state)
        retrieve_docs_node(state, retriever, top_k)
        decide_tools_node(state)
        run_tools_node(state)
        synthesize_answer_node(state)
        verify_grounding_node(state)
        fallback_or_finalize_node(state)
    except Exception as error:  # pragma: no cover - defensive path
        record_error(state, str(error))
        append_trace(
            state,
            "workflow_error",
            {
                "inputs": {
                    "last_completed_node": state["trace"][-1]["node"] if state["trace"] else None,
                },
                "outputs": {"error": str(error)},
            },
        )
        state["final_answer"] = "Workflow execution failed."
        state["final_status"] = "failed"

    if trace_path is not None:
        write_json(trace_path, state)

    return state


def run_workflow_with_memory(
    query: str,
    retriever: Any,
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    top_k: int = DEFAULT_TOP_K,
    memory_top_k: int = 3,
    include_memories_in_context: bool = False,
    update_memory: bool = True,
    memory_threshold: float = 0.55,
    trace_path: Path | None = None,
) -> AgentState:
    state = create_initial_state(query)

    try:
        normalize_query_node(state)
        classify_query_node(state)
        make_plan_node(state)
        retrieve_docs_node(state, retriever, top_k)
        retrieve_memories_node(
            state,
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            vector_memory=vector_memory,
            top_k=memory_top_k,
            include_memories_in_context=include_memories_in_context,
        )
        decide_tools_node(state)
        run_tools_node(state)
        synthesize_answer_node(state)
        verify_grounding_node(state)
        fallback_or_finalize_node(state)
        if update_memory:
            update_memory_node(
                state,
                short_term_memory=short_term_memory,
                long_term_memory=long_term_memory,
                vector_memory=vector_memory,
                threshold=memory_threshold,
            )
    except Exception as error:  # pragma: no cover - defensive path
        record_error(state, str(error))
        append_trace(
            state,
            "workflow_error",
            {
                "inputs": {
                    "last_completed_node": state["trace"][-1]["node"] if state["trace"] else None,
                },
                "outputs": {"error": str(error)},
            },
        )
        state["final_answer"] = "Workflow execution failed."
        state["final_status"] = "failed"

    if trace_path is not None:
        write_json(trace_path, state)

    return state


def run_baseline_rag(query: str, retriever: Any, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    start = time.perf_counter()
    normalized_query = normalize_text(query)
    retrieved_docs = retriever.search(normalized_query, top_k=top_k)
    synthesis = build_baseline_answer(normalized_query, retrieved_docs)
    latency = time.perf_counter() - start
    return {
        "user_query": query,
        "normalized_query": normalized_query,
        "retrieved_docs": retrieved_docs,
        "draft_answer": synthesis["draft_answer"],
        "final_answer": synthesis["draft_answer"],
        "final_status": "answered",
        "citations": synthesis["citations"],
        "trace": [
            {
                "node": "normalize_query",
                "inputs": {"user_query": query},
                "outputs": {"normalized_query": normalized_query},
                "payload": {
                    "inputs": {"user_query": query},
                    "outputs": {"normalized_query": normalized_query},
                },
            },
            {
                "node": "retrieve_docs",
                "inputs": {"normalized_query": normalized_query, "top_k": top_k},
                "outputs": {"results": len(retrieved_docs)},
                "payload": {
                    "inputs": {"normalized_query": normalized_query, "top_k": top_k},
                    "outputs": {"results": len(retrieved_docs)},
                },
            },
            {
                "node": "synthesize_answer",
                "inputs": {"retrieved_doc_count": len(retrieved_docs)},
                "outputs": {"draft_answer": synthesis["draft_answer"]},
                "payload": {
                    "inputs": {"retrieved_doc_count": len(retrieved_docs)},
                    "outputs": {"draft_answer": synthesis["draft_answer"]},
                },
            },
        ],
        "latency_seconds": round(latency, 4),
    }
