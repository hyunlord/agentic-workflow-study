from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.utils import json_ready


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _serialize(value: Any, max_length: int = 120) -> str:
    text = str(json_ready(value))
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def trace_to_debug_frame(trace: list[dict[str, Any]]) -> pd.DataFrame:
    previous_timestamp: datetime | None = None
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(trace, start=1):
        current_timestamp = _parse_timestamp(str(entry.get("timestamp", "")))
        latency = entry.get("latency")
        if not isinstance(latency, (int, float)) and previous_timestamp is not None and current_timestamp is not None:
            latency = round((current_timestamp - previous_timestamp).total_seconds(), 6)
        previous_timestamp = current_timestamp or previous_timestamp
        rows.append(
            {
                "step": index,
                "node": str(entry.get("node", "")),
                "latency": round(float(latency), 6) if isinstance(latency, (int, float)) else None,
                "inputs": _serialize(entry.get("inputs", {})),
                "outputs": _serialize(entry.get("outputs", entry.get("payload", {}))),
                "timestamp": str(entry.get("timestamp", "")),
            }
        )
    return pd.DataFrame(rows, columns=["step", "node", "latency", "inputs", "outputs", "timestamp"])


def display_trace(trace: list[dict[str, Any]], render: bool = True) -> pd.DataFrame:
    frame = trace_to_debug_frame(trace)
    if render:
        try:  # pragma: no branch - notebook convenience
            from IPython.display import display

            display(frame)
        except Exception:  # pragma: no cover
            print(frame.to_string(index=False))
    return frame


def display_node_inputs(trace: list[dict[str, Any]], node_name: str, render: bool = True) -> pd.DataFrame:
    rows = [
        {"step": index, "node": entry.get("node", ""), "inputs": _serialize(entry.get("inputs", {}))}
        for index, entry in enumerate(trace, start=1)
        if entry.get("node") == node_name
    ]
    frame = pd.DataFrame(rows, columns=["step", "node", "inputs"])
    if render:
        try:  # pragma: no branch
            from IPython.display import display

            display(frame)
        except Exception:  # pragma: no cover
            print(frame.to_string(index=False))
    return frame


def display_node_outputs(trace: list[dict[str, Any]], node_name: str, render: bool = True) -> pd.DataFrame:
    rows = [
        {"step": index, "node": entry.get("node", ""), "outputs": _serialize(entry.get("outputs", {}))}
        for index, entry in enumerate(trace, start=1)
        if entry.get("node") == node_name
    ]
    frame = pd.DataFrame(rows, columns=["step", "node", "outputs"])
    if render:
        try:  # pragma: no branch
            from IPython.display import display

            display(frame)
        except Exception:  # pragma: no cover
            print(frame.to_string(index=False))
    return frame


__all__ = [
    "display_node_inputs",
    "display_node_outputs",
    "display_trace",
    "trace_to_debug_frame",
]
