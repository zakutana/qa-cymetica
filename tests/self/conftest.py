"""Our own tests: state goes to a temp folder, scripts load by path, nothing reaches the network."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(f"self_{name}", REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _state_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    (tmp_path / "state").mkdir()
    return tmp_path / "state"


@pytest.fixture
def script():
    return load_script
