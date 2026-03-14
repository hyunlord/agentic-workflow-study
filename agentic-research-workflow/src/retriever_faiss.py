from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import numpy as np

from src.config import RuntimeConfig


class OptionalDependencyError(ImportError):
    """Raised when optional FAISS or sentence-transformer dependencies are unavailable."""


def _import_faiss() -> Any:
    try:
        import faiss  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional extras
        raise OptionalDependencyError(
            "FAISS dependencies are not installed. Run `uv sync --extra cpu` or `uv sync --extra gpu`."
        ) from exc
    return faiss


def _import_sentence_transformer() -> Any:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional extras
        raise OptionalDependencyError(
            "sentence-transformers is not installed. Run `uv sync --extra cpu` or `uv sync --extra gpu`."
        ) from exc
    return SentenceTransformer


def _load_model(model_name: str, device: str) -> Any:
    SentenceTransformer = _import_sentence_transformer()
    try:
        return SentenceTransformer(model_name, device=device, local_files_only=True)
    except Exception as exc:  # pragma: no cover - depends on optional model cache state
        raise OptionalDependencyError(
            "sentence-transformers model files are not available locally. Cache the model first or "
            "use the default TF-IDF retriever."
        ) from exc


@dataclass
class FAISSRetriever:
    chunks: list[dict[str, Any]]
    embeddings: np.ndarray
    index: Any
    model_name: str
    device: str
    nprobe: int = 10
    _model: Any = field(default=None, repr=False)

    @classmethod
    def from_chunks(cls, chunks: list[dict[str, Any]], config: RuntimeConfig) -> "FAISSRetriever":
        if not chunks:
            raise ValueError("Cannot build a FAISS retriever from an empty chunk list.")

        faiss = _import_faiss()

        model = _load_model(config.embedding_model, config.device)
        embeddings = model.encode(
            [chunk["text"] for chunk in chunks],
            batch_size=config.embedding_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        index = faiss.IndexFlatIP(embeddings.shape[1])
        if config.device == "cuda" and config.use_gpu_faiss and hasattr(faiss, "StandardGpuResources"):
            resources = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(resources, 0, index)

        index.add(embeddings)
        if hasattr(index, "nprobe"):
            index.nprobe = config.faiss_nprobe

        return cls(
            chunks=chunks,
            embeddings=embeddings,
            index=index,
            model_name=config.embedding_model,
            device=config.device,
            nprobe=config.faiss_nprobe,
            _model=model,
        )

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = _load_model(self.model_name, self.device)
        return self._model

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_embedding = self._get_model().encode(
            [query],
            batch_size=1,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")
        scores, indices = self.index.search(query_embedding, top_k)

        results: list[dict[str, Any]] = []
        for score, index in zip(scores[0], indices[0], strict=False):
            if index < 0:
                continue
            chunk = dict(self.chunks[int(index)])
            chunk["score"] = round(float(score), 4)
            results.append(chunk)
        return results

    def dense_embeddings(self) -> np.ndarray:
        return self.embeddings

    def save(self, path: Path) -> None:
        faiss = _import_faiss()
        output_dir = Path(path)
        output_dir.mkdir(parents=True, exist_ok=True)

        cpu_index = self.index
        if self.device == "cuda" and hasattr(faiss, "index_gpu_to_cpu"):
            cpu_index = faiss.index_gpu_to_cpu(self.index)

        faiss.write_index(cpu_index, str(output_dir / "index.faiss"))
        np.save(output_dir / "embeddings.npy", self.embeddings)
        (output_dir / "chunks.json").write_text(json.dumps(self.chunks, ensure_ascii=True, indent=2))
        (output_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "model_name": self.model_name,
                    "device": self.device,
                    "nprobe": self.nprobe,
                },
                ensure_ascii=True,
                indent=2,
            )
        )

    @classmethod
    def load(cls, path: Path, config: RuntimeConfig) -> "FAISSRetriever":
        faiss = _import_faiss()
        input_dir = Path(path)
        index = faiss.read_index(str(input_dir / "index.faiss"))

        if config.device == "cuda" and config.use_gpu_faiss and hasattr(faiss, "StandardGpuResources"):
            resources = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(resources, 0, index)

        metadata = json.loads((input_dir / "metadata.json").read_text())
        chunks = json.loads((input_dir / "chunks.json").read_text())
        embeddings = np.load(input_dir / "embeddings.npy")
        if hasattr(index, "nprobe"):
            index.nprobe = config.faiss_nprobe

        return cls(
            chunks=chunks,
            embeddings=embeddings,
            index=index,
            model_name=str(metadata.get("model_name", config.embedding_model)),
            device=config.device,
            nprobe=config.faiss_nprobe,
            _model=None,
        )
