from src.config import RuntimeConfig
from src.ingestion import build_demo_index


def test_runtime_config_auto_detect_returns_supported_device() -> None:
    config = RuntimeConfig.auto_detect()

    assert config.device in {"cpu", "mps", "cuda"}
    assert config.embedding_batch_size > 0
    assert config.faiss_nprobe > 0


def test_build_demo_index_supports_faiss_backend_with_safe_fallback() -> None:
    retriever = build_demo_index(persist=False, backend="faiss")
    results = retriever.search("When does the organization-wide rollout begin?", top_k=2)

    assert hasattr(retriever, "search")
    assert isinstance(results, list)
