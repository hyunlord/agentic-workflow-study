# Setup Guide

## Default Local Setup (TF-IDF Fallback)

```bash
uv sync
uv run jupyter lab
```

This path uses the existing CPU-safe TF-IDF retriever and works without optional dense-retrieval packages.

## Mac Studio (Apple Silicon)

```bash
uv sync --extra cpu
uv run jupyter lab
```

This installs `faiss-cpu`, `sentence-transformers`, and `torch` so the optional FAISS retriever can run on CPU or MPS-backed PyTorch environments.

## DGX Spark (CUDA GPU)

```bash
uv sync --extra gpu
uv run jupyter lab --ip 0.0.0.0 --port 8888
```

The `gpu` extra targets Linux x86_64 environments and installs:

- `faiss-gpu-cu12`
- `sentence-transformers`
- `torch`

## Notes

- The project still defaults to the TF-IDF `HybridRetriever`.
- To try the dense retriever, call `build_demo_index(backend="faiss")`.
- If optional FAISS dependencies are unavailable, the ingestion helper falls back to the TF-IDF retriever automatically.
