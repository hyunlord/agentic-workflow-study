from __future__ import annotations

from pathlib import Path

from src.ingestion import ingest_documents, load_documents


def test_load_documents_defaults_to_demo_corpus() -> None:
    documents = load_documents()

    sources = {document["source"] for document in documents}

    assert len(documents) == 7
    assert "workspace_policy_refresh.md" in sources
    assert "technical_retrieval_notes.txt" in sources


def test_load_documents_recursive_reads_nested_files(tmp_path: Path) -> None:
    (tmp_path / "top.md").write_text("# Top\n\nTop level content.")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "child.txt").write_text("Nested content.")
    deeper = nested / "deeper"
    deeper.mkdir()
    (deeper / "grandchild.md").write_text("Deep content.")
    (tmp_path / "ignore.json").write_text("{}")

    shallow = load_documents(raw_dir=tmp_path, recursive=False)
    recursive = load_documents(raw_dir=tmp_path, recursive=True)

    assert {item["source"] for item in shallow} == {"top.md"}
    assert {item["source"] for item in recursive} == {
        "top.md",
        "nested/child.txt",
        "nested/deeper/grandchild.md",
    }
    assert {item["doc_id"] for item in recursive} == {
        "top",
        "nested__child",
        "nested__deeper__grandchild",
    }


def test_ingest_documents_supports_recursive_loading(tmp_path: Path) -> None:
    (tmp_path / "top.md").write_text("Top level sentence. Another top sentence.")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "child.txt").write_text("Nested sentence. Another nested sentence.")

    shallow_chunks = ingest_documents(raw_dir=tmp_path, persist=False)
    recursive_chunks = ingest_documents(raw_dir=tmp_path, persist=False, recursive=True)

    assert {chunk["source"] for chunk in shallow_chunks} == {"top.md"}
    assert {chunk["source"] for chunk in recursive_chunks} == {
        "top.md",
        "nested/child.txt",
    }
