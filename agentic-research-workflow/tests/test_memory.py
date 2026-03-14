from pathlib import Path

import pandas as pd

from src.ingestion import build_demo_index
from src.memory import (
    LongTermMemory,
    ShortTermMemory,
    VectorMemory,
    display_memory,
    selective_memory_update,
)
from src.workflow import run_workflow_with_memory


def test_short_term_memory_keeps_recent_events() -> None:
    memory = ShortTermMemory(max_items=3)
    memory.append_event("user", "first turn")
    memory.append_event("assistant", "second turn")
    memory.append_event("user", "third turn")
    memory.append_event("assistant", "fourth turn")

    recent = memory.last_n(2)

    assert len(memory.events) == 3
    assert recent[0]["content"] == "third turn"
    assert recent[1]["content"] == "fourth turn"


def test_long_term_memory_persists_items(tmp_path: Path) -> None:
    store = LongTermMemory(tmp_path / "memory.json")
    store.store_memory("answer_style", "Prefer concise rollout summaries.", category="preference")

    reloaded = LongTermMemory(tmp_path / "memory.json")

    assert reloaded.retrieve_memory("answer_style")["value"] == "Prefer concise rollout summaries."
    assert reloaded.list_items()[0]["category"] == "preference"


def test_vector_memory_search_returns_relevant_text() -> None:
    memory = VectorMemory()
    memory.add_memory("Alex prefers concise rollout answers with the date first.", metadata={"kind": "preference"})
    memory.add_memory("The pilot retrospective is scheduled for June.", metadata={"kind": "fact"})

    results = memory.search("How should I answer rollout timing for Alex?", top_k=1)

    assert len(results) == 1
    assert "Alex prefers concise rollout answers" in results[0]["text"]


def test_selective_memory_update_uses_importance_threshold(tmp_path: Path) -> None:
    long_term = LongTermMemory(tmp_path / "memory.json")
    vector_memory = VectorMemory()

    decision = selective_memory_update(
        text="Remember: Mina prefers concise rollout summaries with dates first.",
        key="mina_preference",
        long_term_memory=long_term,
        vector_memory=vector_memory,
        threshold=0.5,
        category="preference",
    )

    assert decision["stored"] is True
    assert long_term.retrieve_memory("mina_preference") is not None
    assert vector_memory.search("How should I answer for Mina?", top_k=1)


def test_display_memory_returns_tables(tmp_path: Path) -> None:
    short_term = ShortTermMemory()
    short_term.append_event("user", "Explain rollout timing.")

    long_term = LongTermMemory(tmp_path / "memory.json")
    long_term.store_memory("style", "Use concise wording.", category="preference")

    vector_memory = VectorMemory()
    vector_memory.add_memory("Use concise wording for rollout answers.")

    tables = display_memory(
        short_term_memory=short_term,
        long_term_memory=long_term,
        vector_memory=vector_memory,
        render=False,
    )

    assert set(tables) == {"short_term", "long_term", "vector"}
    assert all(isinstance(table, pd.DataFrame) for table in tables.values())


def test_workflow_with_memory_reads_and_updates_memory(tmp_path: Path) -> None:
    retriever = build_demo_index(persist=False)
    short_term = ShortTermMemory()
    long_term = LongTermMemory(tmp_path / "memory.json")
    vector_memory = VectorMemory()
    vector_memory.add_memory(
        "Remember Mina prefers concise rollout answers that begin with the exact date.",
        metadata={"kind": "preference"},
    )

    state = run_workflow_with_memory(
        "When does the organization-wide rollout begin?",
        retriever=retriever,
        short_term_memory=short_term,
        long_term_memory=long_term,
        vector_memory=vector_memory,
        update_memory=True,
    )

    assert state["final_status"] == "answered"
    assert len(state["retrieved_memories"]) >= 1
    assert any(entry["node"] == "retrieve_memories" for entry in state["trace"])
    assert any(entry["node"] == "update_memory" for entry in state["trace"])
    assert len(short_term.events) >= 2
