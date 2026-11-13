# Phase 0 gate scripts (archived)

Record of the feature-order gate (`docs/REBUILD_SPEC.md` Section 3, outcome in
`docs/DECISIONS.md`). `legacy_model.py` builds positional arrays in two orderings on
purpose, to compare them. Nothing outside this directory may import from it; the
rebuild's inference code reads the order from `model/feature_spec.json` only.

    cd tools && uv run python gate/gate_regression.py
