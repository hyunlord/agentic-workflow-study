from src.evaluator import evaluate_system, load_eval_dataset


def test_evaluate_system_repeats_each_sample() -> None:
    dataset = load_eval_dataset()[:2]

    results = evaluate_system("baseline", dataset=dataset, repeats=2)

    assert len(results) == 4
    assert set(results["run_id"]) == {1, 2}


def test_evaluate_system_keeps_richer_failure_analysis_fields_for_agent_workflow() -> None:
    dataset = load_eval_dataset()[:1]

    results = evaluate_system("agent_workflow", dataset=dataset, repeats=1)

    assert "trace" in results.columns
    assert "errors" in results.columns
    assert "citations" in results.columns
    assert "expected_sources" in results.columns
