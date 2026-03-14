from __future__ import annotations

from typing import Any

from src.state import AgentState


class StateValidationError(ValueError):
    """Raised when workflow state is inconsistent with completed nodes."""


NODE_REQUIREMENTS: dict[str, dict[str, type[Any]]] = {
    "normalize_query": {"normalized_query": str},
    "classify_query": {"query_type": str, "requires_tools": bool},
    "make_plan": {"plan": list},
    "retrieve_docs": {"retrieved_docs": list},
    "retrieve_memories": {"retrieved_memories": list},
    "decide_tools": {"tool_requests": list},
    "run_tools": {"tool_outputs": list},
    "synthesize_answer": {"draft_answer": str, "citations": list},
    "verify_grounding": {"verification_result": object},
    "fallback_or_finalize": {"final_answer": str, "final_status": str},
    "update_memory": {"memory_updates": list},
}


def _is_invalid(value: Any, expected_type: type[Any]) -> bool:
    if value is None:
        return True
    if expected_type is str:
        return not isinstance(value, str) or not value.strip()
    if expected_type is bool:
        return not isinstance(value, bool)
    if expected_type is list:
        return not isinstance(value, list)
    return False


def validate_state(state: AgentState) -> None:
    completed_nodes = {str(entry.get("node", "")) for entry in state.get("trace", [])}
    issues: list[str] = []

    for node_name, requirements in NODE_REQUIREMENTS.items():
        if node_name not in completed_nodes:
            continue
        for key, expected_type in requirements.items():
            if key not in state:
                issues.append(f"{key} missing after {node_name}")
                continue
            if _is_invalid(state[key], expected_type):
                issues.append(f"{key} invalid after {node_name}")

    if issues:
        issue_text = "; ".join(issues)
        raise StateValidationError(f"State validation failed: {issue_text}")


__all__ = ["StateValidationError", "validate_state"]
