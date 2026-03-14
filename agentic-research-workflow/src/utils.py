from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b",
    re.IGNORECASE,
)
STOPWORDS = {
    "a",
    "an",
    "answer",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "grounded",
    "how",
    "in",
    "into",
    "is",
    "it",
    "source",
    "sources",
    "summary",
    "comparison",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "what",
    "when",
    "which",
    "who",
    "why",
    "with",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def normalize_token(token: str) -> str:
    lowered = token.lower()
    if lowered.endswith("ies") and len(lowered) > 4:
        return lowered[:-3] + "y"
    if lowered.endswith("s") and len(lowered) > 3 and not lowered.endswith("ss"):
        return lowered[:-1]
    return lowered


def content_tokens(text: str) -> list[str]:
    normalized = [normalize_token(token) for token in tokenize(text)]
    return [token for token in normalized if token not in STOPWORDS]


def sentence_split(text: str) -> list[str]:
    cleaned = text.replace("\r", "\n")
    rough_parts = re.split(r"(?<=[.!?])\s+|\n{2,}", cleaned)
    return [normalize_text(part) for part in rough_parts if normalize_text(part)]


def overlap_ratio(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set)


def token_f1(prediction: str, gold: str) -> float:
    prediction_tokens = content_tokens(prediction)
    gold_tokens = content_tokens(gold)
    if not prediction_tokens or not gold_tokens:
        return 0.0
    overlap = len(set(prediction_tokens) & set(gold_tokens))
    if overlap == 0:
        return 0.0
    precision = overlap / len(set(prediction_tokens))
    recall = overlap / len(set(gold_tokens))
    return round(2 * precision * recall / (precision + recall), 3)


def extract_dates(text: str) -> list[str]:
    return [match.group(0) for match in DATE_RE.finditer(text)]


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return {key: json_ready(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path: Path, payload: Any) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(json_ready(payload), indent=2, ensure_ascii=True) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_directory(path.parent)
    serialized = "\n".join(json.dumps(json_ready(row), ensure_ascii=True) for row in rows)
    path.write_text(serialized + ("\n" if serialized else ""))


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _trace_cell(value: Any, max_length: int = 120) -> str:
    text = json.dumps(json_ready(value), ensure_ascii=True, sort_keys=True)
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def trace_to_frame(trace: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, str | int]] = []
    for index, entry in enumerate(trace, start=1):
        rows.append(
            {
                "step": index,
                "node": str(entry.get("node", "")),
                "inputs": _trace_cell(entry.get("inputs", {})),
                "outputs": _trace_cell(entry.get("outputs", entry.get("payload", {}))),
                "timestamp": str(entry.get("timestamp", "")),
            }
        )
    return pd.DataFrame(rows, columns=["step", "node", "inputs", "outputs", "timestamp"])


def display_trace(trace: list[dict[str, Any]], render: bool = True) -> pd.DataFrame:
    frame = trace_to_frame(trace)
    if render:
        try:  # pragma: no branch - visual convenience for notebooks
            from IPython.display import display

            display(frame)
        except Exception:  # pragma: no cover - notebook-only display fallback
            print(frame.to_string(index=False))
    return frame
