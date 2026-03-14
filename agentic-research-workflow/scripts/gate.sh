#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. All imports ==="
uv run python - <<'PY'
from src.config import RuntimeConfig, get_paths
from src.schemas import EvaluationRecord, RetrievedDoc, ToolOutput, ToolRequest, VerificationResult
from src.state import AgentState, append_trace, create_initial_state
from src.state_validation import validate_state
from src.classifier import classify_query
from src.planner import make_plan
from src.planner_extended import PlanExecutor, PlanGenerator
from src.retriever import HybridRetriever
from src.retriever_faiss import FAISSRetriever
from src.ingestion import build_demo_index, chunk_document, load_documents
from src.tools import calculator, date_parser, execute_tool_requests, plan_tool_requests
from src.tools_extended import ToolRegistry, build_default_registry
from src.synthesizer import build_baseline_answer, synthesize_answer
from src.verifier import verify_grounding
from src.fallback import fallback_or_finalize
from src.workflow import run_baseline_rag, run_workflow, run_workflow_with_memory
from src.evaluator import evaluate_system, summarize_results
from src.memory import LongTermMemory, ShortTermMemory, VectorMemory
from src.trace_debug import display_trace, trace_to_debug_frame
from src.failure_taxonomy import FAILURE_TAXONOMY
from src.failure_analyzer import analyze_failures, classify_failure

print("All imports OK")
print(RuntimeConfig.auto_detect())
PY

echo "=== 2. Eval dataset ==="
uv run python - <<'PY'
import json
from collections import Counter

with open("data/eval/eval_dataset.json") as fh:
    dataset = json.load(fh)

assert len(dataset) == 40, f"Expected 40, got {len(dataset)}"
distribution = Counter(item["question_type"] for item in dataset)
for query_type in ["simple_lookup", "comparison", "multi_hop", "summary", "insufficient_evidence_risk"]:
    assert distribution[query_type] == 8, f"{query_type}: expected 8, got {distribution[query_type]}"
print("Eval dataset OK")
PY

echo "=== 3. Failure taxonomy ==="
uv run python - <<'PY'
from src.failure_taxonomy import FAILURE_TAXONOMY

assert len(FAILURE_TAXONOMY) >= 12
for failure_type, metadata in FAILURE_TAXONOMY.items():
    for field in ["severity", "stage", "mitigation", "detection_method"]:
        assert field in metadata, f"{failure_type} missing {field}"
print("Failure taxonomy OK")
PY

echo "=== 4. Architecture docs ==="
uv run python - <<'PY'
from pathlib import Path

path = Path("docs/architecture.md")
assert path.exists(), "Missing docs/architecture.md"
assert path.read_text().lower().count("```mermaid") >= 3, "Expected at least three Mermaid diagrams"
print("Architecture docs OK")
PY

echo "=== 5. Tests ==="
uv run pytest tests/ -q

echo "=== ALL GATES PASSED ==="
