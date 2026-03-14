from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import nbformat
import pandas as pd
from src.utils import read_json
from src.workflow import run_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_defines_uv_project_metadata() -> None:
    pyproject_path = PROJECT_ROOT / "pyproject.toml"

    assert pyproject_path.exists()

    data = tomllib.loads(pyproject_path.read_text())
    assert data["project"]["name"] == "agentic-research-workflow"
    assert data["project"]["requires-python"] == ">=3.11"
    assert "jupyterlab" in " ".join(data["project"]["dependencies"])
    assert "cpu" in data["project"]["optional-dependencies"]
    assert "gpu" in data["project"]["optional-dependencies"]
    assert "ipykernel" in " ".join(data["dependency-groups"]["dev"])
    assert "pytest" in " ".join(data["dependency-groups"]["dev"])


def test_uv_scripts_exist_with_expected_commands() -> None:
    setup_script = (PROJECT_ROOT / "scripts" / "setup_uv_env.sh").read_text()
    jupyter_script = (PROJECT_ROOT / "scripts" / "run_jupyter.sh").read_text()
    makefile = (PROJECT_ROOT / "Makefile").read_text()

    assert "uv venv --seed" in setup_script
    assert "uv sync" in setup_script
    assert "ipython kernel install" in setup_script
    assert "jupyter lab" in jupyter_script
    assert "--ip=0.0.0.0" in jupyter_script
    assert "setup:" in makefile
    assert "jupyter:" in makefile
    assert "eval:" in makefile


def test_notebooks_are_structured_as_tutorials() -> None:
    notebook_dir = PROJECT_ROOT / "notebooks"
    expected_names = {
        "01_rag_basics.ipynb",
        "02_agentic_workflow.ipynb",
        "03_evaluation.ipynb",
        "04_failure_analysis.ipynb",
        "05_agent_memory.ipynb",
        "06_agent_planning.ipynb",
        "07_tool_use.ipynb",
        "08_agent_debugging.ipynb",
    }
    assert {path.name for path in notebook_dir.glob("*.ipynb")} == expected_names

    required_sections = (
        "Learning goals",
        "Implementation",
        "Experiment",
        "Result analysis",
        "Takeaways",
    )

    for notebook_path in sorted(notebook_dir.glob("*.ipynb")):
        notebook = nbformat.read(notebook_path, as_version=4)
        markdown_sources = [
            cell["source"]
            for cell in notebook.cells
            if cell["cell_type"] == "markdown"
        ]
        merged_markdown = "\n".join(markdown_sources)
        for section in required_sections:
            assert section in merged_markdown

        for index, cell in enumerate(notebook.cells):
            if cell["cell_type"] != "code":
                continue
            assert index > 0
            assert notebook.cells[index - 1]["cell_type"] == "markdown"

        code_sources = [cell["source"] for cell in notebook.cells if cell["cell_type"] == "code"]
        assert any("import sys" in source and "sys.executable" in source for source in code_sources)


def test_eval_dataset_has_learning_scale_examples() -> None:
    dataset = read_json(PROJECT_ROOT / "data" / "eval" / "eval_dataset.json")
    assert len(dataset) == 40


def test_trace_visualization_returns_learning_friendly_table() -> None:
    from src.ingestion import build_demo_index
    from src.utils import display_trace

    retriever = build_demo_index(persist=False)
    state = run_workflow("How many days are in the pilot window?", retriever=retriever)

    frame = display_trace(state["trace"], render=False)

    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == ["step", "node", "latency", "inputs", "outputs", "timestamp"]
    assert "retrieve_docs" in set(frame["node"])
    assert frame["latency"].notna().all()
    assert all(isinstance(value, str) for value in frame["inputs"])
    assert all(isinstance(value, str) for value in frame["outputs"])


def test_runtime_config_and_faiss_module_import_safely() -> None:
    from src.config import RuntimeConfig
    from src.retriever_faiss import FAISSRetriever

    config = RuntimeConfig.auto_detect()

    assert config.device in {"cpu", "mps", "cuda"}
    assert isinstance(config.use_gpu_faiss, bool)
    assert FAISSRetriever.__name__ == "FAISSRetriever"


def test_evaluator_script_runs_as_direct_python_entrypoint() -> None:
    result = subprocess.run(
        [sys.executable, "src/evaluator.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "agent_workflow" in result.stdout
