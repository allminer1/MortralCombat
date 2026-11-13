"""The backend image is built from uv.lock with `--no-dev`. Nothing in the lock file may
be a training library (Phase 2 acceptance: "image has no torch")."""

import tomllib
from pathlib import Path

FORBIDDEN = {"torch", "pycox", "torchtuples", "scikit-learn", "pandas", "matplotlib", "streamlit", "joblib"}


def test_lock_file_has_no_training_libraries():
    lock = tomllib.loads((Path(__file__).parents[2] / "uv.lock").read_text(encoding="utf-8"))
    names = {package["name"].lower() for package in lock["package"]}
    assert {"fastapi", "onnxruntime", "numpy"} <= names
    assert not (names & FORBIDDEN)
