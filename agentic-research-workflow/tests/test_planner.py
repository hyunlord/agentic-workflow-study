from src.planner import make_plan


def test_make_plan_for_multi_hop_contains_verification_step() -> None:
    plan = make_plan("multi_hop")

    assert "decompose question into sub-parts" in plan
    assert plan[-1] == "verify grounding before final answer"


def test_make_plan_defaults_to_simple_lookup_template() -> None:
    plan = make_plan("unknown")

    assert plan[0] == "retrieve relevant evidence"
