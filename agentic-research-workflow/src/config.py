from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TOP_K = 5
DEFAULT_CHUNK_SIZE = 2
DEFAULT_CHUNK_OVERLAP = 1
DEFAULT_REFERENCE_DATE = "2025-04-01"
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-large"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    eval_dir: Path
    notebooks_dir: Path
    src_dir: Path
    artifacts_dir: Path
    traces_dir: Path
    logs_dir: Path
    reports_dir: Path


@dataclass(frozen=True)
class RuntimeConfig:
    device: str
    use_gpu_faiss: bool
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_batch_size: int = 32
    faiss_nprobe: int = 10
    top_k: int = DEFAULT_TOP_K
    coverage_threshold: float = 0.65

    @classmethod
    def auto_detect(cls) -> "RuntimeConfig":
        device = "cpu"
        use_gpu_faiss = False
        batch_size = 32
        faiss_nprobe = 10

        if importlib.util.find_spec("torch") is not None:
            try:
                import torch

                if torch.cuda.is_available():
                    device = "cuda"
                    batch_size = 256
                    faiss_nprobe = 32
                elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                    device = "mps"
                    batch_size = 64
            except Exception:
                device = "cpu"
                use_gpu_faiss = False
                batch_size = 32
                faiss_nprobe = 10

        if device == "cuda" and importlib.util.find_spec("faiss") is not None:
            try:
                import faiss

                use_gpu_faiss = hasattr(faiss, "StandardGpuResources")
            except Exception:
                use_gpu_faiss = False

        return cls(
            device=device,
            use_gpu_faiss=use_gpu_faiss,
            embedding_batch_size=batch_size,
            faiss_nprobe=faiss_nprobe,
        )


def get_paths(root: Path | None = None) -> ProjectPaths:
    project_root = root or Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    artifacts_dir = project_root / "artifacts"
    return ProjectPaths(
        root=project_root,
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        processed_dir=data_dir / "processed",
        eval_dir=data_dir / "eval",
        notebooks_dir=project_root / "notebooks",
        src_dir=project_root / "src",
        artifacts_dir=artifacts_dir,
        traces_dir=artifacts_dir / "traces",
        logs_dir=artifacts_dir / "logs",
        reports_dir=artifacts_dir / "reports",
    )
