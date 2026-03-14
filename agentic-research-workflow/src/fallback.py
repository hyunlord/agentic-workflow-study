from __future__ import annotations

from src.schemas import VerificationResult


def fallback_or_finalize(
    query: str,
    query_type: str,
    draft_answer: str,
    verification_result: VerificationResult,
) -> dict[str, str]:
    if query_type == "insufficient_evidence_risk" and not (
        verification_result.is_grounded
        and verification_result.coverage_score >= 0.85
        and not verification_result.missing_aspects
    ):
        return {
            "final_answer": (
                "The loaded documents do not ground this request, so the workflow is abstaining instead of guessing."
            ),
            "final_status": "abstained",
        }

    if verification_result.is_grounded and verification_result.coverage_score >= 0.65:
        return {"final_answer": draft_answer, "final_status": "answered"}

    explanation = (
        "I do not have enough grounded evidence in the loaded documents to answer this confidently. "
        "Please narrow the question or add more source material."
    )
    if verification_result.missing_aspects:
        explanation = f"{explanation} Missing coverage: {'; '.join(verification_result.missing_aspects)}"

    return {"final_answer": explanation, "final_status": "abstained"}
