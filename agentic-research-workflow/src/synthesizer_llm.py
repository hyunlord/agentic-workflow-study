from __future__ import annotations

import re
import warnings
from typing import Any

from src.synthesizer import synthesize_answer


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


def _format_tools(tool_outputs: list[dict[str, Any]]) -> str:
    if not tool_outputs:
        return "No tool results."
    return "\n".join(f"- {output['tool_name']}: {output['output']}" for output in tool_outputs)


def _default_citations(retrieved_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "doc_id": doc["doc_id"],
            "chunk_id": doc["chunk_id"],
            "source": doc["source"],
            "score": doc.get("score", 0.0),
        }
        for doc in retrieved_docs[:3]
    ]


def _parse_citations(answer: str, retrieved_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cited_sources = {match.strip() for match in re.findall(r"\[([^\[\]]+)\]", answer)}
    citations = [
        {
            "doc_id": doc["doc_id"],
            "chunk_id": doc["chunk_id"],
            "source": doc["source"],
            "score": doc.get("score", 0.0),
        }
        for doc in retrieved_docs
        if doc["source"] in cited_sources
    ]
    return citations or _default_citations(retrieved_docs)


def synthesize_answer_llm(
    query: str,
    query_type: str,
    retrieved_docs: list[dict[str, Any]],
    tool_outputs: list[dict[str, Any]],
    client: Any = None,
) -> dict[str, Any]:
    """Generate a grounded answer from retrieved evidence via an LLM, with safe fallback."""

    fallback = synthesize_answer(
        query=query,
        query_type=query_type,
        retrieved_docs=retrieved_docs,
        tool_outputs=tool_outputs,
    )

    if client is None:
        warnings.warn("LLM synthesizer fallback: no client provided.", stacklevel=2)
        return fallback
    if hasattr(client, "is_available") and not client.is_available():
        warnings.warn("LLM synthesizer fallback: client unavailable.", stacklevel=2)
        return fallback

    messages = [
        {
            "role": "system",
            "content": (
                "You are a research assistant. Answer ONLY based on the provided evidence. "
                "If insufficient, say so. Include [source_name] citations."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Evidence:\n{_format_evidence(retrieved_docs)}\n\n"
                f"Tool results:\n{_format_tools(tool_outputs)}\n\n"
                f"Question: {query}"
            ),
        },
    ]

    try:
        draft_answer = client.chat(messages)
    except Exception as error:
        warnings.warn(f"LLM synthesizer fallback: {error}", stacklevel=2)
        return fallback

    return {
        "draft_answer": draft_answer,
        "citations": _parse_citations(draft_answer, retrieved_docs),
    }
