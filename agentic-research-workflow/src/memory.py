from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.utils import (
    content_tokens,
    ensure_directory,
    iso_timestamp,
    normalize_text,
    overlap_ratio,
    read_json,
    write_json,
)


class ShortTermMemory:
    def __init__(self, max_items: int | None = None) -> None:
        self.max_items = max_items
        self.events: list[dict[str, Any]] = []

    def append_event(
        self,
        kind: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": len(self.events) + 1,
            "kind": kind,
            "content": normalize_text(content),
            "metadata": metadata or {},
            "timestamp": iso_timestamp(),
        }
        self.events.append(event)
        if self.max_items is not None and len(self.events) > self.max_items:
            self.events = self.events[-self.max_items :]
        return event

    def last_n(self, limit: int) -> list[dict[str, Any]]:
        return self.events[-limit:]

    def clear(self) -> None:
        self.events.clear()

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.events, columns=["event_id", "kind", "content", "metadata", "timestamp"])


class LongTermMemory:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._items: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        payload = read_json(self.path)
        return list(payload) if isinstance(payload, list) else []

    def _persist(self) -> None:
        ensure_directory(self.path.parent)
        write_json(self.path, self._items)

    def store_memory(
        self,
        key: str,
        value: str,
        category: str = "fact",
        metadata: dict[str, Any] | None = None,
        importance: float | None = None,
    ) -> dict[str, Any]:
        item = {
            "key": key,
            "value": normalize_text(value),
            "category": category,
            "metadata": metadata or {},
            "importance": importance,
            "updated_at": iso_timestamp(),
        }
        existing_index = next((index for index, entry in enumerate(self._items) if entry["key"] == key), None)
        if existing_index is None:
            self._items.append(item)
        else:
            self._items[existing_index] = item
        self._persist()
        return item

    def retrieve_memory(self, key: str) -> dict[str, Any] | None:
        return next((item for item in self._items if item["key"] == key), None)

    def list_items(self) -> list[dict[str, Any]]:
        return list(self._items)

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        query_tokens = content_tokens(query)
        matches: list[dict[str, Any]] = []
        for item in self._items:
            searchable_text = f"{item['key']} {item['value']} {item['category']}"
            lexical_score = overlap_ratio(query_tokens, content_tokens(searchable_text))
            exact_key_bonus = 0.25 if item["key"].lower() in normalize_text(query).lower() else 0.0
            score = round(min(1.0, lexical_score + exact_key_bonus), 3)
            if score <= 0.0:
                continue
            matches.append(
                {
                    "memory_type": "long_term",
                    "key": item["key"],
                    "text": item["value"],
                    "score": score,
                    "category": item["category"],
                    "metadata": item["metadata"],
                    "timestamp": item["updated_at"],
                }
            )
        return sorted(matches, key=lambda entry: entry["score"], reverse=True)[:limit]

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self._items, columns=["key", "value", "category", "importance", "updated_at"])


class VectorMemory:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix: Any = None

    def _rebuild_index(self) -> None:
        if not self.entries:
            self.vectorizer = None
            self.matrix = None
            return
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.matrix = self.vectorizer.fit_transform(entry["text"] for entry in self.entries)

    def add_memory(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
    ) -> dict[str, Any]:
        entry = {
            "memory_id": f"memory_{len(self.entries) + 1}",
            "text": normalize_text(text),
            "metadata": metadata or {},
            "importance": round(float(importance), 3),
            "timestamp": iso_timestamp(),
        }
        self.entries.append(entry)
        self._rebuild_index()
        return entry

    def search(self, query: str, top_k: int = 3, min_score: float = 0.0) -> list[dict[str, Any]]:
        if not self.entries or self.vectorizer is None or self.matrix is None:
            return []

        query_vector = self.vectorizer.transform([query])
        cosine_scores = cosine_similarity(query_vector, self.matrix).flatten()
        lexical_scores = [
            overlap_ratio(content_tokens(query), content_tokens(entry["text"]))
            for entry in self.entries
        ]

        ranked: list[dict[str, Any]] = []
        for index, entry in enumerate(self.entries):
            score = round(float((cosine_scores[index] * 0.85) + (lexical_scores[index] * 0.15)), 4)
            if score < min_score:
                continue
            ranked.append(
                {
                    "memory_type": "vector",
                    "memory_id": entry["memory_id"],
                    "text": entry["text"],
                    "score": score,
                    "importance": entry["importance"],
                    "metadata": entry["metadata"],
                    "timestamp": entry["timestamp"],
                }
            )

        return sorted(ranked, key=lambda entry: entry["score"], reverse=True)[:top_k]

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.entries, columns=["memory_id", "text", "importance", "metadata", "timestamp"])


def score_memory_importance(text: str, metadata: dict[str, Any] | None = None) -> float:
    normalized = normalize_text(text).lower()
    tokens = content_tokens(normalized)
    metadata = metadata or {}

    score = 0.2
    if len(tokens) >= 8:
        score += 0.2
    if any(marker in normalized for marker in ("remember", "prefers", "prefer", "always", "never", "important")):
        score += 0.25
    if any(character.isdigit() for character in normalized):
        score += 0.1
    if metadata.get("category") in {"preference", "constraint", "fact"}:
        score += 0.15
    if metadata.get("source") == "user":
        score += 0.1
    return round(min(score, 1.0), 3)


def selective_memory_update(
    text: str,
    key: str,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    threshold: float = 0.55,
    category: str = "fact",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    effective_metadata = {"category": category, **metadata}
    importance_score = score_memory_importance(text, effective_metadata)
    decision = {
        "key": key,
        "text": normalize_text(text),
        "category": category,
        "importance_score": importance_score,
        "stored": importance_score >= threshold,
        "stored_in": [],
    }
    if importance_score < threshold:
        return decision

    if long_term_memory is not None:
        long_term_memory.store_memory(
            key=key,
            value=text,
            category=category,
            metadata=metadata,
            importance=importance_score,
        )
        decision["stored_in"].append("long_term")

    if vector_memory is not None:
        vector_memory.add_memory(
            text=text,
            metadata={"key": key, "category": category, **metadata},
            importance=importance_score,
        )
        decision["stored_in"].append("vector")

    return decision


def retrieve_relevant_memories(
    query: str,
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    query_tokens = content_tokens(query)

    if short_term_memory is not None:
        for event in short_term_memory.last_n(top_k * 2):
            score = round(min(1.0, overlap_ratio(query_tokens, content_tokens(event["content"])) + 0.2), 3)
            if score <= 0.0:
                continue
            matches.append(
                {
                    "memory_type": "short_term",
                    "key": f"event_{event['event_id']}",
                    "text": event["content"],
                    "score": score,
                    "category": event["kind"],
                    "metadata": event["metadata"],
                    "timestamp": event["timestamp"],
                }
            )

    if long_term_memory is not None:
        matches.extend(long_term_memory.search(query, limit=top_k))

    if vector_memory is not None:
        matches.extend(vector_memory.search(query, top_k=top_k))

    ranked = sorted(matches, key=lambda entry: (entry["score"], entry.get("importance", 0.0)), reverse=True)
    return ranked[:top_k]


def build_memory_augmented_context(
    query: str,
    retrieved_docs: list[dict[str, Any]],
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    memories = retrieve_relevant_memories(
        query=query,
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        vector_memory=vector_memory,
        top_k=top_k,
    )
    combined_context = {
        "query": query,
        "documents": [doc["text"] for doc in retrieved_docs],
        "memories": [memory["text"] for memory in memories],
    }
    return {
        "query": query,
        "retrieved_docs": retrieved_docs,
        "retrieved_memories": memories,
        "combined_context": combined_context,
    }


def memory_results_to_docs(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pseudo_docs: list[dict[str, Any]] = []
    for index, memory in enumerate(memories, start=1):
        pseudo_docs.append(
            {
                "doc_id": f"memory_{memory['memory_type']}",
                "chunk_id": f"memory_chunk_{index}",
                "text": memory["text"],
                "source": f"memory://{memory['memory_type']}",
                "score": round(float(memory["score"]), 4),
            }
        )
    return pseudo_docs


def summarize_memory_events(events: list[dict[str, Any]], limit: int = 4) -> str:
    selected_events = events[-limit:]
    if not selected_events:
        return "No recent memory events to summarize."
    return " | ".join(f"{event['kind']}: {event['content']}" for event in selected_events)


def display_memory(
    short_term_memory: ShortTermMemory | None = None,
    long_term_memory: LongTermMemory | None = None,
    vector_memory: VectorMemory | None = None,
    render: bool = True,
) -> dict[str, pd.DataFrame]:
    tables = {
        "short_term": short_term_memory.to_frame() if short_term_memory is not None else pd.DataFrame(),
        "long_term": long_term_memory.to_frame() if long_term_memory is not None else pd.DataFrame(),
        "vector": vector_memory.to_frame() if vector_memory is not None else pd.DataFrame(),
    }
    if render:
        try:  # pragma: no branch - notebook convenience
            from IPython.display import Markdown, display

            for name, table in tables.items():
                display(Markdown(f"### {name.replace('_', ' ').title()}"))
                display(table)
        except Exception:  # pragma: no cover - notebook-only fallback
            for name, table in tables.items():
                print(name)
                print(table.to_string(index=False) if not table.empty else "(empty)")
    return tables


__all__ = [
    "ShortTermMemory",
    "LongTermMemory",
    "VectorMemory",
    "build_memory_augmented_context",
    "display_memory",
    "memory_results_to_docs",
    "retrieve_relevant_memories",
    "score_memory_importance",
    "selective_memory_update",
    "summarize_memory_events",
]
