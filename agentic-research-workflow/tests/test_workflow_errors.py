from src.workflow import run_workflow


class BrokenRetriever:
    def search(self, query: str, top_k: int = 5) -> list[dict[str, object]]:
        raise RuntimeError("retriever exploded")


def test_workflow_records_error_in_trace() -> None:
    state = run_workflow("What changed?", retriever=BrokenRetriever())

    assert state["final_status"] == "failed"
    assert state["errors"] == ["retriever exploded"]
    assert state["trace"][-1]["node"] == "workflow_error"
