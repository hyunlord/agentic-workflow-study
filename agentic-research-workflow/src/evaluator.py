from __future__ import annotations

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import time
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from src.config import get_paths
from src.ingestion import build_demo_index
from src.schemas import EvaluationRecord
from src.utils import read_json, token_f1, write_json
from src.workflow import run_baseline_rag, run_workflow


SystemName = Literal["baseline", "agent_workflow"]


def load_eval_dataset(dataset_path: Path | None = None) -> list[dict[str, Any]]:
    paths = get_paths()
    source = dataset_path or paths.eval_dir / "eval_dataset.json"
    return list(read_json(source))


def score_answer(predicted_answer: str, gold_answer: str, predicted_status: str, expected_status: str) -> float:
    if expected_status == "abstained":
        return 1.0 if predicted_status == "abstained" else 0.0
    if predicted_status == "abstained":
        return 0.0
    return token_f1(predicted_answer, gold_answer)


def retrieval_hit_rate(retrieved_docs: list[dict[str, Any]], expected_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0 if retrieved_docs else 0.0
    sources = {doc["source"] for doc in retrieved_docs}
    return 1.0 if any(source in sources for source in expected_sources) else 0.0


def classify_failure(record: dict[str, Any]) -> str:
    if record["expected_status"] == "abstained" and record["predicted_status"] != "abstained":
        return "insufficient_evidence_not_detected"
    if record["expected_status"] == "answered" and record["predicted_status"] == "abstained":
        return "over_abstention"
    if record["retrieval_hit_rate"] == 0.0:
        return "retrieval_miss"
    if record["predicted_question_type"] and record["predicted_question_type"] != record["expected_question_type"]:
        return "query_misclassification"
    if record["system"] == "agent_workflow" and not record["grounding_pass"] and record["predicted_status"] == "answered":
        return "ungrounded_synthesis"
    if record["answer_correctness"] < 0.45:
        if record["retrieval_hit_rate"] >= 1.0 and record["predicted_status"] == "answered":
            return "synthesis_quality_gap"
        return "bad_plan"
    return "none"


def evaluate_system(
    system: SystemName,
    dataset: list[dict[str, Any]] | None = None,
    trace_dir: Path | None = None,
    repeats: int = 3,
) -> pd.DataFrame:
    evaluation_set = dataset or load_eval_dataset()
    retriever = build_demo_index(persist=False)
    rows: list[dict[str, Any]] = []

    for run_id in range(1, repeats + 1):
        for sample in evaluation_set:
            start = time.perf_counter()
            if system == "baseline":
                result = run_baseline_rag(sample["question"], retriever)
                predicted_question_type = None
                grounding_pass = False
            else:
                trace_path = None
                if trace_dir is not None:
                    trace_path = trace_dir / f"{sample['id']}_run{run_id}.json"
                result = run_workflow(sample["question"], retriever, trace_path=trace_path)
                predicted_question_type = result["query_type"]
                grounding_pass = result["verification_result"].is_grounded

            latency = time.perf_counter() - start
            record = EvaluationRecord(
                system=system,
                question_id=sample["id"],
                run_id=run_id,
                question=sample["question"],
                expected_question_type=sample["question_type"],
                predicted_question_type=predicted_question_type,
                expected_status=sample.get("expected_status", "answered"),
                predicted_status=result["final_status"],
                final_answer=result["final_answer"],
                answer_correctness=score_answer(
                    result["final_answer"],
                    sample["gold_answer"],
                    result["final_status"],
                    sample.get("expected_status", "answered"),
                ),
                retrieval_hit_rate=retrieval_hit_rate(result["retrieved_docs"], sample.get("expected_sources", [])),
                grounding_pass=grounding_pass,
                abstained=result["final_status"] == "abstained",
                abstain_precision=0.0,
                latency_seconds=round(latency, 4),
                average_steps=float(len(result.get("trace", []))),
                failure_type="",
            ).to_dict()
            record["failure_type"] = classify_failure(record)
            record["abstain_precision"] = 1.0 if (
                record["abstained"] and record["expected_status"] == "abstained"
            ) else 0.0
            rows.append(record)

    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["grounding_pass_rate"] = frame["grounding_pass"].astype(float)
    else:
        frame["grounding_pass_rate"] = []
    return frame


def summarize_results(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for system, frame in results.groupby("system"):
        abstained = frame[frame["abstained"]]
        abstain_precision = (
            float((abstained["expected_status"] == "abstained").mean()) if not abstained.empty else 0.0
        )
        rows.append(
            {
                "system": system,
                "answer_correctness": frame["answer_correctness"].mean(),
                "retrieval_hit_rate": frame["retrieval_hit_rate"].mean(),
                "grounding_pass_rate": frame["grounding_pass_rate"].mean(),
                "abstain_precision": abstain_precision,
                "latency": frame["latency_seconds"].mean(),
                "average_steps": frame["average_steps"].mean(),
            }
        )
    return pd.DataFrame(rows).round(3)


def extract_failure_cases(results: pd.DataFrame) -> pd.DataFrame:
    return results[results["failure_type"] != "none"].copy()


def attach_failure_improvements(failures: pd.DataFrame) -> pd.DataFrame:
    fixes = {
        "retrieval_miss": "Tune chunking or add richer retrieval features.",
        "query_misclassification": "Expand classifier rules or add a learned classifier.",
        "bad_plan": "Add better query-type-specific decomposition templates.",
        "synthesis_quality_gap": "Tighten answer templates or add a post-synthesis rewrite step.",
        "ungrounded_synthesis": "Tighten unsupported claim checks before finalization.",
        "insufficient_evidence_not_detected": "Raise verifier thresholds and abstain earlier.",
        "over_abstention": "Relax fallback thresholds when evidence is sufficient.",
    }
    if failures.empty:
        failures["improvement_idea"] = []
        return failures
    failures = failures.copy()
    failures["improvement_idea"] = failures["failure_type"].map(fixes).fillna("Inspect trace manually.")
    return failures


def run_evaluation_suite(
    dataset: list[dict[str, Any]] | None = None,
    repeats: int = 3,
    persist_outputs: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = get_paths()
    baseline = evaluate_system("baseline", dataset=dataset, repeats=repeats)
    workflow = evaluate_system("agent_workflow", dataset=dataset, trace_dir=paths.traces_dir, repeats=repeats)
    results = pd.concat([baseline, workflow], ignore_index=True)
    summary = summarize_results(results)

    if persist_outputs:
        write_json(paths.eval_dir / "eval_results.json", results.to_dict(orient="records"))
        write_json(paths.reports_dir / "evaluation_summary.json", summary.to_dict(orient="records"))
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline vs agent workflow evaluation.")
    parser.add_argument("--repeats", type=int, default=3, help="How many repeated executions to run per sample.")
    parser.add_argument(
        "--persist-outputs",
        action="store_true",
        help="Persist evaluation results into data/eval and artifacts/reports.",
    )
    args = parser.parse_args()

    _, summary = run_evaluation_suite(repeats=args.repeats, persist_outputs=args.persist_outputs)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
