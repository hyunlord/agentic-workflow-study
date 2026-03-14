from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, RuntimeConfig, get_paths
from src.retriever import HybridRetriever
from src.retriever_faiss import FAISSRetriever, OptionalDependencyError
from src.utils import ensure_directory, sentence_split, write_jsonl


SUPPORTED_EXTENSIONS = {".md", ".txt"}


def load_documents(raw_dir: Path | None = None) -> list[dict[str, str]]:
    paths = get_paths()
    source_dir = raw_dir or paths.raw_dir
    documents: list[dict[str, str]] = []

    for path in sorted(source_dir.iterdir()):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        documents.append(
            {
                "doc_id": path.stem,
                "source": path.name,
                "text": path.read_text(),
            }
        )

    return documents


def chunk_document(
    document: dict[str, str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    sentences = sentence_split(document["text"])
    if not sentences:
        return []

    step = max(1, chunk_size - overlap)
    chunks: list[dict[str, Any]] = []
    for index in range(0, len(sentences), step):
        window = sentences[index : index + chunk_size]
        if not window:
            continue
        chunk_id = f"{document['doc_id']}_chunk_{len(chunks) + 1}"
        chunks.append(
            {
                "doc_id": document["doc_id"],
                "chunk_id": chunk_id,
                "text": " ".join(window),
                "source": document["source"],
            }
        )
        if index + chunk_size >= len(sentences):
            break
    return chunks


def ingest_documents(
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
    persist: bool = True,
) -> list[dict[str, Any]]:
    paths = get_paths()
    chunks: list[dict[str, Any]] = []
    for document in load_documents(raw_dir):
        chunks.extend(chunk_document(document))

    if persist:
        output_dir = processed_dir or paths.processed_dir
        ensure_directory(output_dir)
        write_jsonl(output_dir / "chunks.jsonl", chunks)
    return chunks


def build_demo_index(
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
    persist: bool = True,
    backend: str = "tfidf",
) -> HybridRetriever | FAISSRetriever:
    paths = get_paths()
    chunks = ingest_documents(raw_dir=raw_dir, processed_dir=processed_dir, persist=persist)
    if backend == "faiss":
        config = RuntimeConfig.auto_detect()
        try:
            retriever: HybridRetriever | FAISSRetriever = FAISSRetriever.from_chunks(chunks, config=config)
        except OptionalDependencyError:
            retriever = HybridRetriever.from_chunks(chunks)
    else:
        retriever = HybridRetriever.from_chunks(chunks)

    if persist:
        output_dir = processed_dir or paths.processed_dir
        ensure_directory(output_dir)
        np.save(output_dir / "embeddings.npy", retriever.dense_embeddings())

    return retriever
