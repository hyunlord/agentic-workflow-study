from __future__ import annotations

import pandas as pd
import pytest

from src.data_profiles import compare_profiles, list_profiles, load_profile


def test_list_profiles_returns_expected_frame() -> None:
    frame = list_profiles()

    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == [
        "name",
        "raw_dir",
        "eval_dataset",
        "description",
        "language",
    ]
    assert set(frame["name"]) == {"demo", "tech_docs", "korean_public"}


def test_load_profile_demo_returns_retriever_eval_and_stats() -> None:
    profile = load_profile("demo", persist=False)

    assert profile["name"] == "demo"
    assert hasattr(profile["retriever"], "search")
    assert isinstance(profile["eval_dataset"], list)
    assert isinstance(profile["documents"], list)
    assert isinstance(profile["chunks"], list)
    assert profile["config"]["language"] == "en"
    assert profile["stats"]["document_count"] == 7
    assert profile["stats"]["chunk_count"] > 0
    assert profile["stats"]["eval_question_count"] == len(profile["eval_dataset"])


def test_load_profile_raises_for_unknown_profile() -> None:
    with pytest.raises(KeyError):
        load_profile("missing-profile")


def test_compare_profiles_single_profile_returns_stats_frame() -> None:
    frame = compare_profiles("demo")

    assert isinstance(frame, pd.DataFrame)
    assert list(frame["name"]) == ["demo"]
    assert frame.loc[0, "language"] == "en"
    assert frame.loc[0, "document_count"] == 7
