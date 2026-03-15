from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_dataset() -> list[dict[str, object]]:
    path = Path(__file__).resolve().parents[1] / "data" / "eval" / "eval_dataset_tech_docs.json"
    return json.loads(path.read_text())


def test_eval_dataset_tech_docs_has_expected_size_and_distribution() -> None:
    dataset = load_dataset()

    assert len(dataset) == 40

    query_type_counts = Counter(item["question_type"] for item in dataset)
    assert query_type_counts == {
        "simple_lookup": 8,
        "comparison": 8,
        "multi_hop": 8,
        "summary": 8,
        "insufficient_evidence_risk": 8,
    }


def test_eval_dataset_tech_docs_has_expected_domain_mix_and_abstain_cases() -> None:
    dataset = load_dataset()

    def infer_domain(record: dict[str, object]) -> str:
        expected_sources = record["expected_sources"]
        if not expected_sources:
            return "none"
        return str(expected_sources[0]).split("/", 1)[0]

    domain_counts = Counter(infer_domain(item) for item in dataset)
    assert domain_counts["anthropic"] == 15
    assert domain_counts["langgraph"] == 15
    assert domain_counts["sentence_transformers"] == 10

    for item in dataset:
        if item["question_type"] == "insufficient_evidence_risk":
            assert item["expected_status"] == "abstained"


def test_eval_dataset_tech_docs_expected_sources_exist() -> None:
    dataset = load_dataset()
    docs_root = Path(__file__).resolve().parents[1] / "data" / "raw" / "tech_docs"

    for item in dataset:
        for source in item["expected_sources"]:
            assert (docs_root / str(source)).exists(), f"Missing expected source: {source}"
