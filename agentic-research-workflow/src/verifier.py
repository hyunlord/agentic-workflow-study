from __future__ import annotations

from typing import Any

from src.schemas import VerificationResult
from src.utils import content_tokens, overlap_ratio, sentence_split


def verify_grounding(
    query: str,
    draft_answer: str,
    retrieved_docs: list[dict[str, Any]],
    tool_outputs: list[dict[str, Any]] | None = None,
) -> VerificationResult:
    if not retrieved_docs:
        return VerificationResult(
            is_grounded=False,
            coverage_score=0.0,
            unsupported_claims=["No retrieved evidence"],
            missing_aspects=[query],
        )

    evidence_token_sets = [content_tokens(doc["text"]) for doc in retrieved_docs]
    evidence_union = [token for token_set in evidence_token_sets for token in token_set]
    answer_sentences = [
        sentence
        for sentence in sentence_split(draft_answer)
        if not sentence.lower().startswith("sources:")
    ]

    calculator_tokens = {
        token
        for output in (tool_outputs or [])
        if output["tool_name"] == "calculator" and output["output"].get("ok")
        for token in content_tokens(str(output["output"]["result"]))
    }
    parsed_date_count = sum(
        1
        for output in (tool_outputs or [])
        if output["tool_name"] == "date_parser" and output["output"].get("ok")
    )

    unsupported_claims: list[str] = []
    support_scores: list[float] = []
    for sentence in answer_sentences:
        sentence_tokens = content_tokens(sentence)
        if not sentence_tokens:
            continue
        support = max(overlap_ratio(sentence_tokens, evidence_tokens) for evidence_tokens in evidence_token_sets)
        if calculator_tokens and calculator_tokens.issubset(set(sentence_tokens)) and parsed_date_count >= 2:
            support = max(support, 0.85)
        support_scores.append(support)
        if support < 0.45:
            unsupported_claims.append(sentence)

    query_coverage = overlap_ratio(content_tokens(query), evidence_union)
    answer_coverage = sum(support_scores) / len(support_scores) if support_scores else 0.0
    coverage_score = round(min(1.0, (answer_coverage * 0.75) + (query_coverage * 0.25)), 3)

    missing_aspects: list[str] = []
    if query_coverage < 0.35:
        missing_aspects.append("Evidence only covers part of the request.")

    is_grounded = not unsupported_claims and coverage_score >= 0.6
    return VerificationResult(
        is_grounded=is_grounded,
        coverage_score=coverage_score,
        unsupported_claims=unsupported_claims,
        missing_aspects=missing_aspects,
    )
