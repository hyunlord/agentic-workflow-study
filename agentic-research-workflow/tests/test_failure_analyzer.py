from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluator import classify_failure as legacy_classify_failure
from src.failure_analyzer import analyze_failures, classify_failure, generate_failure_report
from src.failure_taxonomy import FAILURE_TAXONOMY


def test_failure_taxonomy_contains_required_metadata() -> None:
    assert len(FAILURE_TAXONOMY) >= 12
    for metadata in FAILURE_TAXONOMY.values():
        assert {"severity", "stage", "mitigation", "detection_method"} <= set(metadata)


def test_classify_failure_detects_retrieval_miss() -> None:
    failures = classify_failure(
        {
            "expected_status": "answered",
            "predicted_status": "answered",
            "retrieval_hit_rate": 0.0,
            "expected_question_type": "simple_lookup",
            "predicted_question_type": "simple_lookup",
            "answer_correctness": 0.1,
            "grounding_pass": False,
            "system": "baseline",
        }
    )

    assert "retrieval_miss" in failures


def test_classify_failure_detects_over_abstention() -> None:
    failures = classify_failure(
        {
            "expected_status": "answered",
            "predicted_status": "abstained",
            "retrieval_hit_rate": 1.0,
            "expected_question_type": "simple_lookup",
            "predicted_question_type": "simple_lookup",
            "answer_correctness": 0.0,
            "grounding_pass": True,
            "system": "agent_workflow",
        }
    )

    assert "over_abstention" in failures


def test_classify_failure_returns_none_for_successful_record() -> None:
    failures = classify_failure(
        {
            "expected_status": "answered",
            "predicted_status": "answered",
            "retrieval_hit_rate": 1.0,
            "expected_question_type": "comparison",
            "predicted_question_type": "comparison",
            "answer_correctness": 0.95,
            "grounding_pass": True,
            "system": "agent_workflow",
            "average_steps": 6.0,
        }
    )

    assert failures == []


def test_classify_failure_detects_citation_mismatch() -> None:
    failures = classify_failure(
        {
            "expected_status": "answered",
            "predicted_status": "answered",
            "retrieval_hit_rate": 1.0,
            "expected_question_type": "simple_lookup",
            "predicted_question_type": "simple_lookup",
            "answer_correctness": 0.8,
            "grounding_pass": True,
            "system": "agent_workflow",
            "citations": ["leadership_faq.txt"],
            "expected_sources": ["workspace_policy_refresh.md"],
        }
    )

    assert "citation_mismatch" in failures


def test_legacy_classify_failure_returns_first_failure_type() -> None:
    failure_type = legacy_classify_failure(
        {
            "expected_status": "abstained",
            "predicted_status": "answered",
            "retrieval_hit_rate": 1.0,
            "expected_question_type": "insufficient_evidence_risk",
            "predicted_question_type": "simple_lookup",
            "answer_correctness": 0.0,
            "grounding_pass": False,
            "system": "agent_workflow",
        }
    )

    assert failure_type == "insufficient_evidence_not_detected"


def test_analyze_failures_handles_empty_frame() -> None:
    analysis = analyze_failures(pd.DataFrame())

    assert analysis["total_failure_instances"] == 0
    assert analysis["failure_distribution"] == {}
    assert analysis["top_improvement_actions"] == []


def test_analyze_failures_and_generate_report(tmp_path: Path) -> None:
    results = pd.DataFrame(
        [
            {
                "expected_status": "answered",
                "predicted_status": "answered",
                "retrieval_hit_rate": 0.0,
                "expected_question_type": "simple_lookup",
                "predicted_question_type": "simple_lookup",
                "answer_correctness": 0.1,
                "grounding_pass": False,
                "system": "baseline",
                "average_steps": 3.0,
            },
            {
                "expected_status": "answered",
                "predicted_status": "abstained",
                "retrieval_hit_rate": 1.0,
                "expected_question_type": "summary",
                "predicted_question_type": "summary",
                "answer_correctness": 0.0,
                "grounding_pass": True,
                "system": "agent_workflow",
                "average_steps": 5.0,
            },
        ]
    )

    analysis = analyze_failures(results)

    assert analysis["failure_distribution"]["retrieval_miss"] >= 1
    assert analysis["severity_distribution"]["major"] >= 1
    assert analysis["top_improvement_actions"]

    report_path = tmp_path / "failure_report.md"
    generate_failure_report(analysis, report_path)

    assert report_path.exists()
    content = report_path.read_text()
    assert "Failure Analysis Report" in content
    assert "retrieval_miss" in content
