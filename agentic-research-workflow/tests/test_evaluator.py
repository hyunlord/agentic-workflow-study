from src.evaluator import evaluate_system, load_eval_dataset


def test_evaluate_system_repeats_each_sample() -> None:
    dataset = load_eval_dataset()[:2]

    results = evaluate_system("baseline", dataset=dataset, repeats=2)

    assert len(results) == 4
    assert set(results["run_id"]) == {1, 2}
