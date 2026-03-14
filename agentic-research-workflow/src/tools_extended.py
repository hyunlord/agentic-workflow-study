from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

import pandas as pd

from src.tools import calculator as base_calculator
from src.utils import content_tokens, normalize_text, overlap_ratio


ToolHandler = Callable[..., dict[str, Any]]


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ToolResult:
    tool_name: str
    ok: bool
    output: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculator(expression: str) -> dict[str, Any]:
    return base_calculator(expression)


def data_tool(rows: list[dict[str, Any]], column: str, operation: str = "count") -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    if column not in frame.columns:
        return {"ok": False, "error": f"Column '{column}' not found."}

    series = frame[column]
    if operation == "count":
        return {"ok": True, "operation": operation, "result": int(series.count())}
    if operation == "unique":
        return {"ok": True, "operation": operation, "result": sorted(series.dropna().astype(str).unique().tolist())}
    if operation == "mean":
        numeric = pd.to_numeric(series, errors="coerce")
        return {"ok": True, "operation": operation, "result": round(float(numeric.mean()), 3)}
    return {"ok": False, "error": f"Unsupported operation: {operation}"}


def search_tool(query: str, documents: list[str], top_k: int = 3) -> dict[str, Any]:
    query_tokens = content_tokens(query)
    ranked: list[dict[str, Any]] = []
    for index, document in enumerate(documents, start=1):
        score = round(overlap_ratio(query_tokens, content_tokens(document)), 4)
        ranked.append(
            {
                "document_id": index,
                "text": document,
                "score": score,
            }
        )
    results = sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]
    return {"ok": True, "results": results}


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler) -> None:
        self._handlers[name] = handler

    def list_tools(self) -> list[str]:
        return sorted(self._handlers)

    def call(self, tool_call: ToolCall) -> ToolResult:
        handler = self._handlers.get(tool_call.tool_name)
        if handler is None:
            return ToolResult(tool_call.tool_name, False, {"error": "Unknown tool"})
        output = handler(**tool_call.args)
        return ToolResult(tool_call.tool_name, bool(output.get("ok", False)), output)

    def select_tools(self, query: str) -> list[str]:
        normalized = normalize_text(query).lower()
        selected: list[str] = []
        if any(marker in normalized for marker in ("calculate", "sum", "difference", "days", "total")):
            selected.append("calculator")
        if any(marker in normalized for marker in ("average", "count", "dataset", "rows", "unique")):
            selected.append("data_tool")
        if any(marker in normalized for marker in ("search", "find", "lookup", "which document")):
            selected.append("search_tool")
        return selected or ["search_tool"]


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("calculator", calculator)
    registry.register("data_tool", data_tool)
    registry.register("search_tool", search_tool)
    return registry


__all__ = [
    "ToolCall",
    "ToolRegistry",
    "ToolResult",
    "build_default_registry",
    "calculator",
    "data_tool",
    "search_tool",
]
