# AGENTS.md

## Project Mission

Maintain this repository as a compact educational learning environment for baseline RAG and agentic workflow design. Favor clarity, inspectability, reproducibility, and interview-readiness over novelty or scale.

## Architecture Rules

- Keep the workflow explicit: `normalize_query -> classify_query -> make_plan -> retrieve_docs -> decide_tools -> run_tools -> synthesize_answer -> verify_grounding -> fallback_or_finalize`.
- Keep reusable logic in `src/`, not in notebooks.
- Preserve the shared `AgentState` shape in `src/state.py`.
- New behavior must remain deterministic unless a change explicitly documents why nondeterminism is necessary.
- Treat traces, evaluation outputs, and notebook tables as first-class artifacts, not afterthoughts.
- Keep memory behavior explicit and inspectable; short-term, long-term, and vector memory helpers belong in `src/memory.py`, not ad hoc notebook code.

## Coding Rules

- Target Python 3.11.
- Use type hints on public functions.
- Prefer small functions and direct data flow.
- Avoid hidden network calls, background services, and framework-heavy abstractions.
- Use `pyproject.toml` and `uv.lock` as the environment source of truth.
- Keep dependencies practical for local laptops and DGX notebook servers.

## Workflow Contract

- `classify_query` must return one of: `simple_lookup`, `comparison`, `multi_hop`, `summary`, `insufficient_evidence_risk`.
- `make_plan` must return an ordered list of execution steps.
- `retrieve_docs` must return scored chunks containing `doc_id`, `chunk_id`, `text`, `score`, and `source`.
- `run_tools` must only call local tools defined in `src/tools.py`.
- `verify_grounding` must report grounding status, coverage, unsupported claims, and missing aspects.
- `fallback_or_finalize` must stay conservative and prefer abstention over unsupported confidence.
- Every node must append a trace entry with readable `inputs` and `outputs`.

## Notebook Editing Rules

- Treat notebooks as mini tutorials, not scratchpads.
- Every code cell must have a Markdown explanation directly above it.
- Each notebook must include these sections in some form: Title, Learning goals, Concept explanation, Implementation, Experiment, Result analysis, Takeaways.
- Keep the first code cell as an environment verification cell that prints `sys.executable`.
- Notebooks must run from top to bottom without manual edits.
- Notebooks must import from `src/` instead of redefining core logic inline.
- If a notebook needs a new dependency, update `pyproject.toml`, refresh `uv.lock`, and keep the DGX setup scripts working.

## Safety Rules

- Do not invent facts outside the loaded documents.
- If the evidence is partial or weak, prefer cautious wording or abstention.
- New tools must stay local and sandbox-safe.
- Treat verifier regressions as high priority because they directly affect trustworthiness.
- Keep DGX instructions optional and CPU-safe unless GPU usage is explicitly required.

## Contribution Guidelines

- Preserve the baseline-versus-agent comparison story.
- Keep the sample corpus small, readable, and coherent enough for learning.
- When changing evaluation behavior, refresh persisted evaluation artifacts.
- When changing notebook pedagogy, optimize for explanation-first teaching value.
- When extending memory examples, prefer simple local storage and similarity search over opaque external services.
- Document meaningful design deviations in `README.md`.
