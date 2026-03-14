from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RetrievedDoc:
    doc_id: str
    chunk_id: str
    text: str
    score: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ToolRequest:
    tool_name: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ToolOutput:
    tool_name: str
    output: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VerificationResult:
    is_grounded: bool
    coverage_score: float
    unsupported_claims: list[str] = field(default_factory=list)
    missing_aspects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvaluationRecord:
    system: str
    question_id: str
    run_id: int
    question: str
    expected_question_type: str
    predicted_question_type: str | None
    expected_status: str
    predicted_status: str
    final_answer: str
    answer_correctness: float
    retrieval_hit_rate: float
    grounding_pass: bool
    abstained: bool
    abstain_precision: float
    latency_seconds: float
    average_steps: float
    failure_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
