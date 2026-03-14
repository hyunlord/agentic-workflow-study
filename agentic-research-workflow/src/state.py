from __future__ import annotations

import uuid
from typing import Any, TypedDict

from src.schemas import VerificationResult
from src.utils import iso_timestamp, json_ready


class AgentState(TypedDict, total=False):
    session_id: str
    user_query: str
    normalized_query: str
    query_type: str
    requires_tools: bool
    plan: list[str]
    retrieved_docs: list[dict[str, Any]]
    retrieved_memories: list[dict[str, Any]]
    tool_requests: list[dict[str, Any]]
    tool_outputs: list[dict[str, Any]]
    draft_answer: str
    citations: list[dict[str, Any]]
    verification_result: VerificationResult
    final_answer: str
    final_status: str
    trace: list[dict[str, Any]]
    memory_updates: list[dict[str, Any]]
    errors: list[str]


def create_initial_state(user_query: str) -> AgentState:
    return AgentState(
        session_id=str(uuid.uuid4()),
        user_query=user_query,
        trace=[],
        errors=[],
    )


def append_trace(state: AgentState, node: str, payload: dict[str, Any]) -> None:
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    outputs = payload.get("outputs", payload) if isinstance(payload, dict) else payload
    state.setdefault("trace", []).append(
        {
            "node": node,
            "timestamp": iso_timestamp(),
            "payload": json_ready(payload),
            "inputs": json_ready(inputs),
            "outputs": json_ready(outputs),
        }
    )


def record_error(state: AgentState, error: str) -> None:
    state.setdefault("errors", []).append(error)
