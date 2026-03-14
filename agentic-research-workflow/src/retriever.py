from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.utils import content_tokens, overlap_ratio


@dataclass
class HybridRetriever:
    chunks: list[dict[str, Any]]
    vectorizer: TfidfVectorizer
    matrix: Any

    @classmethod
    def from_chunks(cls, chunks: list[dict[str, Any]]) -> "HybridRetriever":
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        matrix = vectorizer.fit_transform(chunk["text"] for chunk in chunks)
        return cls(chunks=chunks, vectorizer=vectorizer, matrix=matrix)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.chunks:
            return []

        query_vector = self.vectorizer.transform([query])
        cosine_scores = cosine_similarity(query_vector, self.matrix).flatten()
        lexical_scores = np.array(
            [overlap_ratio(content_tokens(query), content_tokens(chunk["text"])) for chunk in self.chunks]
        )
        combined_scores = (cosine_scores * 0.8) + (lexical_scores * 0.2)
        ranking = np.argsort(combined_scores)[::-1][:top_k]

        results: list[dict[str, Any]] = []
        for index in ranking:
            chunk = dict(self.chunks[index])
            chunk["score"] = round(float(combined_scores[index]), 4)
            results.append(chunk)
        return results

    def dense_embeddings(self) -> np.ndarray:
        return self.matrix.toarray()
