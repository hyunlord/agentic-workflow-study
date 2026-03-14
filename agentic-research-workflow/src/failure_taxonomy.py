from __future__ import annotations

from typing import Any


FailureMetadata = dict[str, str]


FAILURE_TAXONOMY: dict[str, FailureMetadata] = {
    "retrieval_miss": {
        "name": "Retrieval Miss",
        "description": "Relevant evidence never entered the retrieved context window.",
        "severity": "major",
        "stage": "retrieve_docs",
        "detection_method": "retrieval_hit_rate is 0.0 for a sample that expected grounded evidence.",
        "typical_cause": "Chunking is too coarse, lexical overlap is weak, or retrieval scoring is poorly tuned.",
        "mitigation": "Tune chunking, add richer retrieval features, or expand the corpus coverage.",
    },
    "retrieval_noise": {
        "name": "Retrieval Noise",
        "description": "Some evidence was retrieved, but the retrieved set was diluted by low-value chunks.",
        "severity": "minor",
        "stage": "retrieve_docs",
        "detection_method": "retrieval_hit_rate is partial and answer quality remains low.",
        "typical_cause": "Top-k is too large, ranking features are weak, or the query is underspecified.",
        "mitigation": "Tighten ranking, reduce noisy chunks, or add reranking before synthesis.",
    },
    "query_misclassification": {
        "name": "Query Misclassification",
        "description": "The workflow selected the wrong question type for the query.",
        "severity": "major",
        "stage": "classify_query",
        "detection_method": "predicted_question_type differs from expected_question_type.",
        "typical_cause": "Rule-based intent detection missed the dominant query signal.",
        "mitigation": "Expand classifier rules or replace them with a learned classifier.",
    },
    "bad_plan": {
        "name": "Bad Plan",
        "description": "The chosen reasoning template was not sufficient for the task.",
        "severity": "major",
        "stage": "make_plan",
        "detection_method": "answer quality is low without a better upstream explanation.",
        "typical_cause": "The workflow used a shallow plan for a multi-step or comparison-heavy question.",
        "mitigation": "Add stronger query-type-specific decomposition templates.",
    },
    "missing_decomposition": {
        "name": "Missing Decomposition",
        "description": "A multi-step question was handled without enough explicit reasoning steps.",
        "severity": "major",
        "stage": "make_plan",
        "detection_method": "average_steps is low for a complex question and the answer remains weak.",
        "typical_cause": "Planner templates are too short for multi-hop or comparison questions.",
        "mitigation": "Force decomposition for complex queries and expose intermediate sub-goals.",
    },
    "tool_execution_error": {
        "name": "Tool Execution Error",
        "description": "A tool call failed or produced unusable output during the run.",
        "severity": "critical",
        "stage": "run_tools",
        "detection_method": "Trace or error logs contain tool execution failures.",
        "typical_cause": "Malformed arguments, parsing issues, or unsupported tool input.",
        "mitigation": "Validate tool requests before execution and add error-aware fallbacks.",
    },
    "synthesis_quality_gap": {
        "name": "Synthesis Quality Gap",
        "description": "The workflow retrieved enough evidence but failed to form a strong answer.",
        "severity": "major",
        "stage": "synthesize_answer",
        "detection_method": "answer_correctness is low despite high retrieval hit rate.",
        "typical_cause": "Sentence selection or answer templating failed to capture the important evidence.",
        "mitigation": "Tighten answer templates or add a post-synthesis rewrite step.",
    },
    "incomplete_synthesis": {
        "name": "Incomplete Synthesis",
        "description": "The answer captured part of the evidence but omitted key details.",
        "severity": "minor",
        "stage": "synthesize_answer",
        "detection_method": "answer quality is middling and evidence coverage is only partially reflected in the answer.",
        "typical_cause": "The synthesis prompt or ranking logic prioritized only the first relevant fact.",
        "mitigation": "Increase synthesis coverage requirements and summarize multiple evidence spans explicitly.",
    },
    "ungrounded_synthesis": {
        "name": "Ungrounded Synthesis",
        "description": "The workflow answered confidently without enough supporting evidence.",
        "severity": "critical",
        "stage": "verify_grounding",
        "detection_method": "grounding_pass is false while the workflow still returned an answer.",
        "typical_cause": "Verification thresholds are too permissive or unsupported claims slipped through synthesis.",
        "mitigation": "Tighten verifier thresholds and block unsupported claims before finalization.",
    },
    "citation_mismatch": {
        "name": "Citation Mismatch",
        "description": "The cited or referenced sources do not line up with the expected evidence sources.",
        "severity": "major",
        "stage": "verify_grounding",
        "detection_method": "Provided citations do not overlap with expected_sources.",
        "typical_cause": "Source attribution drifted away from the evidence used to answer.",
        "mitigation": "Attach citations directly from retrieved chunks and validate them before finalization.",
    },
    "insufficient_evidence_not_detected": {
        "name": "Missed Abstention",
        "description": "The workflow should have abstained but answered anyway.",
        "severity": "critical",
        "stage": "fallback_or_finalize",
        "detection_method": "expected_status is abstained but predicted_status is answered.",
        "typical_cause": "Fallback thresholds are too lenient for insufficient-evidence questions.",
        "mitigation": "Raise verifier and fallback thresholds so unsupported answers abstain earlier.",
    },
    "over_abstention": {
        "name": "Over Abstention",
        "description": "The workflow abstained despite having enough evidence to answer.",
        "severity": "major",
        "stage": "fallback_or_finalize",
        "detection_method": "expected_status is answered but predicted_status is abstained.",
        "typical_cause": "Fallback thresholds or verifier criteria are too strict.",
        "mitigation": "Relax abstention thresholds when retrieval and grounding signals are sufficient.",
    },
}


def get_failure_metadata(failure_type: str) -> FailureMetadata:
    return FAILURE_TAXONOMY.get(
        failure_type,
        {
            "name": "Unknown Failure",
            "description": "No taxonomy metadata is available for this failure type.",
            "severity": "minor",
            "stage": "unknown",
            "detection_method": "Manual inspection required.",
            "typical_cause": "Unknown.",
            "mitigation": "Inspect the execution trace manually.",
        },
    )


def failure_mitigation(failure_type: str) -> str:
    return get_failure_metadata(failure_type)["mitigation"]


def taxonomy_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for failure_type, metadata in FAILURE_TAXONOMY.items():
        row = {"failure_type": failure_type}
        row.update(metadata)
        rows.append(row)
    return rows
