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
from src.state_validation import validate_state
from src.synthesizer import build_baseline_answer, synthesize_answer
from src.tools import execute_tool_requests, plan_tool_requests
from src.utils import normalize_text, write_json
from src.verifier import verify_grounding


def _record_node_trace(
    state: AgentState,
    node_name: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    start_time: float,
) -> None:
    append_trace(
        state,
        node_name,
        {
            "inputs": inputs,
            "outputs": outputs,
            "latency": round(time.perf_counter() - start_time, 6),
        },
    )
    validate_state(state)


def normalize_query_node(state: AgentState) -> None:
    start = time.perf_counter()
    state["normalized_query"] = normalize_text(state["user_query"])
    _record_node_trace(
        state,
        "normalize_query",
        {"user_query": state["user_query"]},
        {"normalized_query": state["normalized_query"]},
        start,
    )


def classify_query_node(state: AgentState) -> None:
    start = time.perf_counter()
    result = classify_query(state["normalized_query"])
    state["query_type"] = str(result["query_type"])
    state["requires_tools"] = bool(result["requires_tools"])
    _record_node_trace(
        state,
        "classify_query",
        {"normalized_query": state["normalized_query"]},
        result,
        start,
    )


def make_plan_node(state: AgentState) -> None:
    start = time.perf_counter()
    state["plan"] = make_plan(state["query_type"])
    _record_node_trace(
        state,
        "make_plan",
        {"query_type": state["query_type"]},
        {"plan": state["plan"]},
        start,
    )


def retrieve_docs_node(state: AgentState, retriever: Any, top_k: int) -> None:
    start = time.perf_counter()
    state["retrieved_docs"] = retriever.search(state["normalized_query"], top_k=top_k)
    _record_node_trace(
        state,
        "retrieve_docs",
        {"normalized_query": state["normalized_query"], "top_k": top_k},
        {
            "results": len(state["retrieved_docs"]),
            "sources": [doc["source"] for doc in state["retrieved_docs"]],
        },
        start,
    )


def retrieve_memories_node(
    state: AgentState,
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    top_k: int = 3,
    include_memories_in_context: bool = False,
) -> None:
    start = time.perf_counter()
    state["retrieved_memories"] = retrieve_relevant_memories(
        query=state["normalized_query"],
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        vector_memory=vector_memory,
        top_k=top_k,
    )
    if include_memories_in_context and state["retrieved_memories"]:
        state["retrieved_docs"] = [*state["retrieved_docs"], *memory_results_to_docs(state["retrieved_memories"])]
    _record_node_trace(
        state,
        "retrieve_memories",
        {
            "normalized_query": state["normalized_query"],
            "memory_top_k": top_k,
            "include_memories_in_context": include_memories_in_context,
        },
        {
            "memory_count": len(state["retrieved_memories"]),
            "memory_types": [memory["memory_type"] for memory in state["retrieved_memories"]],
        },
        start,
    )


def decide_tools_node(state: AgentState) -> None:
    start = time.perf_counter()
    requests = plan_tool_requests(state["normalized_query"], state["query_type"], state["retrieved_docs"])
    state["tool_requests"] = [request.to_dict() for request in requests]
    _record_node_trace(
        state,
        "decide_tools",
        {
            "normalized_query": state["normalized_query"],
            "query_type": state["query_type"],
            "retrieved_doc_count": len(state["retrieved_docs"]),
        },
        {
            "requires_tools": state["requires_tools"],
            "tool_requests": state["tool_requests"],
        },
        start,
    )


def run_tools_node(state: AgentState) -> None:
    start = time.perf_counter()
    requests = [ToolRequest(**request) for request in state["tool_requests"]]
    outputs = execute_tool_requests(requests)
    state["tool_outputs"] = [output.to_dict() for output in outputs]
    _record_node_trace(
        state,
        "run_tools",
        {"tool_requests": state["tool_requests"]},
        {"tool_outputs": state["tool_outputs"]},
        start,
    )


def synthesize_answer_node(state: AgentState) -> None:
    start = time.perf_counter()
    result = synthesize_answer(
        query=state["normalized_query"],
        query_type=state["query_type"],
        retrieved_docs=state["retrieved_docs"],
        tool_outputs=state["tool_outputs"],
    )
    state["draft_answer"] = result["draft_answer"]
    state["citations"] = result["citations"]
    _record_node_trace(
        state,
        "synthesize_answer",
        {
            "query_type": state["query_type"],
            "retrieved_doc_count": len(state["retrieved_docs"]),
            "tool_output_count": len(state["tool_outputs"]),
        },
        {"draft_answer": state["draft_answer"], "citations": state["citations"]},
        start,
    )


def verify_grounding_node(state: AgentState) -> None:
    start = time.perf_counter()
    state["verification_result"] = verify_grounding(
        query=state["normalized_query"],
        draft_answer=state["draft_answer"],
        retrieved_docs=state["retrieved_docs"],
        tool_outputs=state["tool_outputs"],
    )
    _record_node_trace(
        state,
        "verify_grounding",
        {"draft_answer": state["draft_answer"]},
        state["verification_result"].to_dict(),
        start,
    )


def fallback_or_finalize_node(state: AgentState) -> None:
    start = time.perf_counter()
    result = fallback_or_finalize(
        query=state["normalized_query"],
        query_type=state["query_type"],
        draft_answer=state["draft_answer"],
        verification_result=state["verification_result"],
    )
    state["final_answer"] = result["final_answer"]
    state["final_status"] = result["final_status"]
    _record_node_trace(
        state,
        "fallback_or_finalize",
        {
            "query_type": state["query_type"],
            "coverage_score": state["verification_result"].coverage_score,
            "is_grounded": state["verification_result"].is_grounded,
        },
        result,
        start,
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
    start = time.perf_counter()
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
    _record_node_trace(
        state,
        "update_memory",
        {
            "final_status": state["final_status"],
            "threshold": threshold,
        },
        {
            "memory_updates": state["memory_updates"],
        },
        start,
    )


MEMORY_WORKFLOW_STEPS = (
    normalize_query_node,
    classify_query_node,
    make_plan_node,
    retrieve_docs_node,
    retrieve_memories_node,
    decide_tools_node,
    run_tools_node,
    synthesize_answer_node,
    verify_grounding_node,
    fallback_or_finalize_node,
    update_memory_node,
)


def _execute_workflow_steps(
    state: AgentState,
    steps: tuple[Any, ...],
    retriever: Any,
    top_k: int,
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    memory_top_k: int = 3,
    include_memories_in_context: bool = False,
    update_memory: bool = True,
    memory_threshold: float = 0.55,
) -> None:
    for step in steps:
        if step is retrieve_docs_node:
            step(state, retriever, top_k)
            continue
        if step is retrieve_memories_node:
            step(
                state,
                short_term_memory=short_term_memory,
                long_term_memory=long_term_memory,
                vector_memory=vector_memory,
                top_k=memory_top_k,
                include_memories_in_context=include_memories_in_context,
            )
            continue
        if step is update_memory_node:
            if update_memory:
                step(
                    state,
                    short_term_memory=short_term_memory,
                    long_term_memory=long_term_memory,
                    vector_memory=vector_memory,
                    threshold=memory_threshold,
                )
            continue
        step(state)


def run_workflow(
    query: str,
    retriever: Any,
    top_k: int = DEFAULT_TOP_K,
    trace_path: Path | None = None,
) -> AgentState:
    state = create_initial_state(query)

    try:
        _execute_workflow_steps(state, WORKFLOW_STEPS, retriever=retriever, top_k=top_k)
    except Exception as error:  # pragma: no cover - defensive path
        record_error(state, str(error))
        error_start = time.perf_counter()
        append_trace(
            state,
            "workflow_error",
            {
                "inputs": {"last_completed_node": state["trace"][-1]["node"] if state["trace"] else None},
                "outputs": {"error": str(error)},
                "latency": round(time.perf_counter() - error_start, 6),
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
        _execute_workflow_steps(
            state,
            MEMORY_WORKFLOW_STEPS,
            retriever=retriever,
            top_k=top_k,
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            vector_memory=vector_memory,
            memory_top_k=memory_top_k,
            include_memories_in_context=include_memories_in_context,
            update_memory=update_memory,
            memory_threshold=memory_threshold,
        )
    except Exception as error:  # pragma: no cover - defensive path
        record_error(state, str(error))
        error_start = time.perf_counter()
        append_trace(
            state,
            "workflow_error",
            {
                "inputs": {"last_completed_node": state["trace"][-1]["node"] if state["trace"] else None},
                "outputs": {"error": str(error)},
                "latency": round(time.perf_counter() - error_start, 6),
            },
        )
        state["final_answer"] = "Workflow execution failed."
        state["final_status"] = "failed"

    if trace_path is not None:
        write_json(trace_path, state)

    return state


def run_baseline_rag(query: str, retriever: Any, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    start = time.perf_counter()
    normalize_start = time.perf_counter()
    normalized_query = normalize_text(query)
    normalize_latency = round(time.perf_counter() - normalize_start, 6)

    retrieval_start = time.perf_counter()
    retrieved_docs = retriever.search(normalized_query, top_k=top_k)
    retrieval_latency = round(time.perf_counter() - retrieval_start, 6)

    synthesis_start = time.perf_counter()
    synthesis = build_baseline_answer(normalized_query, retrieved_docs)
    synthesis_latency = round(time.perf_counter() - synthesis_start, 6)

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
                "latency": normalize_latency,
                "payload": {
                    "inputs": {"user_query": query},
                    "outputs": {"normalized_query": normalized_query},
                    "latency": normalize_latency,
                },
            },
            {
                "node": "retrieve_docs",
                "inputs": {"normalized_query": normalized_query, "top_k": top_k},
                "outputs": {"results": len(retrieved_docs)},
                "latency": retrieval_latency,
                "payload": {
                    "inputs": {"normalized_query": normalized_query, "top_k": top_k},
                    "outputs": {"results": len(retrieved_docs)},
                    "latency": retrieval_latency,
                },
            },
            {
                "node": "synthesize_answer",
                "inputs": {"retrieved_doc_count": len(retrieved_docs)},
                "outputs": {"draft_answer": synthesis["draft_answer"]},
                "latency": synthesis_latency,
                "payload": {
                    "inputs": {"retrieved_doc_count": len(retrieved_docs)},
                    "outputs": {"draft_answer": synthesis["draft_answer"]},
                    "latency": synthesis_latency,
                },
            },
        ],
        "latency_seconds": round(latency, 4),
    }
