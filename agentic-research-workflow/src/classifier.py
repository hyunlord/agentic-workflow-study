from __future__ import annotations

from src.utils import normalize_text


SUMMARY_MARKERS = ("summary", "summarize", "overview", "recap", "요약")
COMPARISON_MARKERS = ("compare", "comparison", "difference", "different", "차이", "비교")
MULTI_HOP_MARKERS = (
    "how",
    "why",
    "impact",
    "effect",
    "because",
    "timeline",
    "how many",
    "days",
    "days passed",
    "risk",
    "risks",
    "며칠",
    "영향",
    "왜",
    "어떻게",
)
INSUFFICIENT_MARKERS = (
    "latest",
    "today",
    "current",
    "real-time",
    "external",
    "outside the docs",
    "ceo",
    "stock",
    "weather",
    "news",
)
TOOL_MARKERS = ("how many", "days", "calculate", "date", "timeline", "며칠", "날짜", "계산")


def classify_query(query: str) -> dict[str, object]:
    normalized = normalize_text(query).lower()

    if any(marker in normalized for marker in INSUFFICIENT_MARKERS):
        return {"query_type": "insufficient_evidence_risk", "requires_tools": False}

    if any(marker in normalized for marker in SUMMARY_MARKERS):
        return {"query_type": "summary", "requires_tools": False}

    if any(marker in normalized for marker in COMPARISON_MARKERS):
        requires_tools = any(marker in normalized for marker in TOOL_MARKERS)
        return {"query_type": "comparison", "requires_tools": requires_tools}

    if any(marker in normalized for marker in MULTI_HOP_MARKERS):
        return {"query_type": "multi_hop", "requires_tools": True}

    return {"query_type": "simple_lookup", "requires_tools": False}
