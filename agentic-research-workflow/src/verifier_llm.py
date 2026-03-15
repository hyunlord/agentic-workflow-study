from __future__ import annotations

import json
import re
import warnings
from typing import Any

from src.schemas import VerificationResult
from src.verifier import verify_grounding


def _format_evidence(retrieved_docs: list[dict[str, Any]]) -> str:
    if not retrieved_docs:
        return "No retrieved documents."

    lines: list[str] = []
    for index, doc in enumerate(retrieved_docs, start=1):
        lines.append(
            "\n".join(
                [
                    f"[{index}] source={doc['source']}",
                    f"doc_id={doc['doc_id']} chunk_id={doc['chunk_id']} score={doc.get('score', 0.0)}",
                    f"text={doc['text']}",
                ]
            )
        )
    return "\n\n".join(lines)


def _extract_json_blob(response: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in verifier response.")
    return json.loads(match.group(0))


def verify_grounding_llm(
    query: str,
    draft_answer: str,
    retrieved_docs: list[dict[str, Any]],
    tool_outputs: list[dict[str, Any]] | None = None,
    client: Any = None,
) -> VerificationResult:
    """Verify grounding through an LLM JSON response, with safe fallback."""

    fallback = verify_grounding(
        query=query,
        draft_answer=draft_answer,
        retrieved_docs=retrieved_docs,
        tool_outputs=tool_outputs,
    )

    if client is None:
        warnings.warn("LLM verifier fallback: no client provided.", stacklevel=2)
        return fallback
    if hasattr(client, "is_available") and not client.is_available():
        warnings.warn("LLM verifier fallback: client unavailable.", stacklevel=2)
        return fallback

    messages = [
        {
            "role": "system",
            "content": (
                'You are a grounding verifier. Respond ONLY with JSON: '
                '{"is_grounded": bool, "coverage_score": float 0-1, '
                '"unsupported_claims": [...], "missing_aspects": [...]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Evidence:\n{_format_evidence(retrieved_docs)}\n\n"
                f"Answer:\n{draft_answer}\n\n"
                f"Question: {query}"
            ),
        },
    ]

    try:
        raw_response = client.chat(messages)
        parsed = _extract_json_blob(raw_response)
        return VerificationResult(
            is_grounded=bool(parsed["is_grounded"]),
            coverage_score=round(float(parsed["coverage_score"]), 3),
            unsupported_claims=[str(item) for item in parsed.get("unsupported_claims", [])],
            missing_aspects=[str(item) for item in parsed.get("missing_aspects", [])],
        )
    except Exception as error:
        warnings.warn(f"LLM verifier fallback: {error}", stacklevel=2)
        return fallback
