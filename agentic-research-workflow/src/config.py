from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_TOP_K = 5
DEFAULT_CHUNK_SIZE = 2
DEFAULT_CHUNK_OVERLAP = 1
DEFAULT_REFERENCE_DATE = "2025-04-01"


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
