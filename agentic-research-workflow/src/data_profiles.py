from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import RuntimeConfig, get_paths
from src.ingestion import build_demo_index, chunk_document, load_documents
from src.utils import read_json


PROFILES = {
    "demo": {
        "raw_dir": "data/raw/demo",
        "eval_dataset": "data/eval/eval_dataset.json",
        "description": "가상 사내 문서 7개 (영문). 학습/테스트용.",
        "language": "en",
    },
    "tech_docs": {
        "raw_dir": "data/raw/tech_docs",
        "eval_dataset": "data/eval/eval_dataset_tech_docs.json",
        "description": "Anthropic, LangGraph, sentence-transformers 공개 기술 문서.",
        "language": "en",
    },
    "korean_public": {
        "raw_dir": "data/raw/korean_public",
        "eval_dataset": "data/eval/eval_dataset_korean.json",
        "description": "한국어 법령, 정책, 공공데이터.",
        "language": "ko",
    },
}


def _resolve_profile(name: str) -> dict[str, Any]:
    if name not in PROFILES:
        available = ", ".join(sorted(PROFILES))
        raise KeyError(f"Unknown profile '{name}'. Available profiles: {available}")
    return PROFILES[name]


def _profile_paths(name: str) -> tuple[Path, Path]:
    paths = get_paths()
    profile = _resolve_profile(name)
    return paths.root / profile["raw_dir"], paths.root / profile["eval_dataset"]


def _is_recursive_profile(name: str) -> bool:
    return name == "tech_docs"


def _load_profile_materials(name: str) -> dict[str, Any]:
    profile = _resolve_profile(name)
    raw_dir, eval_path = _profile_paths(name)
    recursive = _is_recursive_profile(name)
    documents = load_documents(raw_dir=raw_dir, recursive=recursive)
    chunks = [
        chunk
        for document in documents
        for chunk in chunk_document(document)
    ]
    eval_dataset = read_json(eval_path)
    return {
        "profile": profile,
        "raw_dir": raw_dir,
        "eval_path": eval_path,
        "recursive": recursive,
        "documents": documents,
        "chunks": chunks,
        "eval_dataset": eval_dataset,
    }


def list_profiles() -> pd.DataFrame:
    """사용 가능한 프로필 목록."""
    rows = [{"name": name, **profile} for name, profile in PROFILES.items()]
    return pd.DataFrame(
        rows,
        columns=["name", "raw_dir", "eval_dataset", "description", "language"],
    )


def load_profile(name: str, backend: str = "tfidf", persist: bool = False) -> dict[str, Any]:
    """Load a profile with retriever, corpus, evaluation set, and summary stats."""
    materials = _load_profile_materials(name)
    runtime_config = RuntimeConfig.auto_detect()
    retriever = build_demo_index(
        raw_dir=materials["raw_dir"],
        persist=persist,
        backend=backend,
        recursive=materials["recursive"],
    )

    stats = {
        "name": name,
        "language": materials["profile"]["language"],
        "backend": backend,
        "recursive": materials["recursive"],
        "document_count": len(materials["documents"]),
        "chunk_count": len(materials["chunks"]),
        "eval_question_count": len(materials["eval_dataset"]),
        "avg_document_chars": round(
            sum(len(document["text"]) for document in materials["documents"]) / len(materials["documents"]),
            1,
        )
        if materials["documents"]
        else 0.0,
        "avg_chunk_chars": round(
            sum(len(chunk["text"]) for chunk in materials["chunks"]) / len(materials["chunks"]),
            1,
        )
        if materials["chunks"]
        else 0.0,
    }

    return {
        "name": name,
        "retriever": retriever,
        "eval_dataset": materials["eval_dataset"],
        "documents": materials["documents"],
        "chunks": materials["chunks"],
        "config": {
            **materials["profile"],
            "backend": backend,
            "persist": persist,
            "recursive": materials["recursive"],
            "runtime": asdict(runtime_config),
        },
        "stats": stats,
    }


def compare_profiles(*names: str) -> pd.DataFrame:
    """여러 프로필의 데이터 규모와 평가셋 크기를 비교."""
    selected_names = names or tuple(PROFILES.keys())
    rows: list[dict[str, Any]] = []
    for name in selected_names:
        loaded = load_profile(name, persist=False)
        row = {"name": loaded["name"], **loaded["stats"]}
        rows.append(row)
    return pd.DataFrame(rows)
