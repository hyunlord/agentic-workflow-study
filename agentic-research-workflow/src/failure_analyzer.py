from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from src.failure_taxonomy import FAILURE_TAXONOMY, failure_mitigation, get_failure_metadata
from src.utils import ensure_directory


def _append_unique(failures: list[str], failure_type: str) -> None:
    if failure_type not in failures:
        failures.append(failure_type)


def _contains_tool_error(record: dict[str, Any]) -> bool:
    errors = [str(item).lower() for item in record.get("errors", [])]
    if any("tool" in error for error in errors):
        return True

    for entry in record.get("trace", []):
        node_name = str(entry.get("node", "")).lower()
        payload_text = str(entry.get("outputs", entry.get("payload", {}))).lower()
        if "tool" in node_name and ("error" in payload_text or "failed" in payload_text):
            return True
    return False


def classify_failure(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    expected_status = str(record.get("expected_status", "answered"))
    predicted_status = str(record.get("predicted_status", "answered"))
    retrieval = float(record.get("retrieval_hit_rate", 0.0) or 0.0)
    answer_correctness = float(record.get("answer_correctness", 0.0) or 0.0)
    grounding_pass = bool(record.get("grounding_pass", False))
    predicted_question_type = record.get("predicted_question_type")
    expected_question_type = record.get("expected_question_type")
    average_steps = float(record.get("average_steps", 0.0) or 0.0)
    citations = {str(item) for item in record.get("citations", [])}
    expected_sources = {str(item) for item in record.get("expected_sources", [])}

    if expected_status == "abstained" and predicted_status != "abstained":
        _append_unique(failures, "insufficient_evidence_not_detected")
    if expected_status == "answered" and predicted_status == "abstained":
        _append_unique(failures, "over_abstention")
    if retrieval == 0.0:
        _append_unique(failures, "retrieval_miss")
    if predicted_question_type and expected_question_type and predicted_question_type != expected_question_type:
        _append_unique(failures, "query_misclassification")
    if _contains_tool_error(record):
        _append_unique(failures, "tool_execution_error")
    if record.get("system") == "agent_workflow" and not grounding_pass and predicted_status == "answered":
        _append_unique(failures, "ungrounded_synthesis")
    if citations and expected_sources and citations.isdisjoint(expected_sources):
        _append_unique(failures, "citation_mismatch")

    if answer_correctness < 0.45:
        if retrieval >= 1.0 and predicted_status == "answered":
            _append_unique(failures, "synthesis_quality_gap")
            if 0.2 <= answer_correctness < 0.45:
                _append_unique(failures, "incomplete_synthesis")
        elif predicted_status == "answered":
            _append_unique(failures, "bad_plan")

    if 0.0 < retrieval < 1.0 and answer_correctness < 0.45 and predicted_status == "answered":
        _append_unique(failures, "retrieval_noise")

    if (
        expected_question_type in {"comparison", "multi_hop", "summary"}
        and predicted_status == "answered"
        and answer_correctness < 0.6
        and average_steps <= 4.0
    ):
        _append_unique(failures, "missing_decomposition")

    return failures


def _records_with_failures(results_df: pd.DataFrame) -> list[tuple[str, dict[str, str]]]:
    records: list[tuple[str, dict[str, str]]] = []
    if results_df.empty:
        return records

    for record in results_df.to_dict(orient="records"):
        failure_types = classify_failure(record)
        for failure_type in failure_types:
            metadata = get_failure_metadata(failure_type)
            records.append((failure_type, metadata))
    return records


def analyze_failures(results_df: pd.DataFrame) -> dict[str, Any]:
    if results_df.empty:
        return {
            "total_failure_instances": 0,
            "failure_distribution": {},
            "stage_distribution": {},
            "severity_distribution": {},
            "top_improvement_actions": [],
        }

    failure_records = _records_with_failures(results_df)
    failure_distribution = Counter(failure for failure, _ in failure_records)
    stage_distribution = Counter(metadata["stage"] for _, metadata in failure_records)
    severity_distribution = Counter(metadata["severity"] for _, metadata in failure_records)
    mitigation_distribution = Counter(failure_mitigation(failure) for failure, _ in failure_records)

    top_improvement_actions = [
        {"mitigation": mitigation, "count": count}
        for mitigation, count in mitigation_distribution.most_common(5)
    ]

    return {
        "total_failure_instances": sum(failure_distribution.values()),
        "failure_distribution": dict(sorted(failure_distribution.items())),
        "stage_distribution": dict(sorted(stage_distribution.items())),
        "severity_distribution": dict(sorted(severity_distribution.items())),
        "top_improvement_actions": top_improvement_actions,
    }


def generate_failure_report(analysis: dict[str, Any], output_path: Path) -> None:
    ensure_directory(output_path.parent)

    lines = [
        "# Failure Analysis Report",
        "",
        f"- Total failure instances: {analysis.get('total_failure_instances', 0)}",
        "",
        "## Failure Distribution",
    ]

    failure_distribution = analysis.get("failure_distribution", {})
    if failure_distribution:
        for failure_type, count in failure_distribution.items():
            metadata = get_failure_metadata(failure_type)
            lines.append(
                f"- `{failure_type}` ({metadata['severity']}, stage: `{metadata['stage']}`): {count} "
                f"- {metadata['description']}"
            )
    else:
        lines.append("- No failures detected.")

    lines.extend(["", "## Stage Distribution"])
    stage_distribution = analysis.get("stage_distribution", {})
    if stage_distribution:
        for stage, count in stage_distribution.items():
            lines.append(f"- `{stage}`: {count}")
    else:
        lines.append("- No stage-level failures to summarize.")

    lines.extend(["", "## Severity Distribution"])
    severity_distribution = analysis.get("severity_distribution", {})
    if severity_distribution:
        for severity, count in severity_distribution.items():
            lines.append(f"- `{severity}`: {count}")
    else:
        lines.append("- No severity distribution available.")

    lines.extend(["", "## Top Improvement Actions"])
    top_improvement_actions = analysis.get("top_improvement_actions", [])
    if top_improvement_actions:
        for item in top_improvement_actions:
            lines.append(f"- {item['mitigation']} ({item['count']})")
    else:
        lines.append("- No improvement actions identified.")

    output_path.write_text("\n".join(lines) + "\n")


def taxonomy_frame() -> pd.DataFrame:
    rows = []
    for failure_type, metadata in FAILURE_TAXONOMY.items():
        row = {"failure_type": failure_type}
        row.update(metadata)
        rows.append(row)
    return pd.DataFrame(rows)
