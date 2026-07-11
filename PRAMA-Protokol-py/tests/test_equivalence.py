"""Kernel identity regression against committed golden vectors.

HISTORY. Until 0.2.0 this file certified the package against the code it
was extracted from (`Aptadynamic-Electrical-Grid`). That comparison is now
CIRCULAR: the grid imports its kernel from this package
(`from prama_protokol import project`), so the old test compared the
package with a wrapper around itself and certified nothing. The historical
extraction-time certification is preserved as a record in EQUIVALENCE.md;
the live cross-implementation certification is Python↔Rust
(EQUIVALENCE-RS.md).

WHAT THIS FILE DOES NOW. It pins the kernel's exact numerical identity at
0.2.1 with golden vectors: a committed fixture (tests/golden_gamma.npz)
holds a synthetic input stream and every Γ output produced by the current
certified kernel. Any future change to kernel arithmetic — however small —
breaks bit-exact reproduction and MUST be accompanied by regenerating the
fixture, a version bump, an ANOMALIES.md entry, and Rust recertification.

Regenerate (only as part of a certified kernel change):

    python tests/test_equivalence.py --regenerate
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from prama_protokol import KernelConfig, project
from prama_protokol.interface import causal_conditional_mean

FIXTURE = pathlib.Path(__file__).parent / "golden_gamma.npz"

GAMMA_COLS = ["delta", "xi", "lambda", "theta", "M", "G"]
DISCRETE_COLS = ["latent_collapse", "stratum", "valid"]


def _synthetic_stream(n: int = 24 * 400, seed: int = 7):
    """A year+ of synthetic hourly observables with seasonal structure."""
    rng = np.random.default_rng(seed)
    t0 = 1_100_000_000
    t = t0 + np.arange(n) * 3600
    hours = pd.to_datetime(t, unit="s", utc=True)
    base = 1.5 + np.sin(2 * np.pi * hours.hour / 24) + 0.5 * np.sin(
        2 * np.pi * hours.month / 12
    )
    omega = rng.poisson(np.clip(base, 0.1, None)).astype(float)
    ctx = (hours.month.to_numpy() * 100 + hours.hour.to_numpy())
    expected = causal_conditional_mean(omega, ctx, 10, 24 * 30)
    return omega, expected


def _project_current():
    omega, expected = _synthetic_stream()
    cfgs = {
        "grid": KernelConfig(),                                  # tau=336, g=24
        "llm": KernelConfig(tau_memory=64, g_smooth=16),         # LLM-domain cfg
    }
    out = {"omega": omega, "expected": expected}
    for name, cfg in cfgs.items():
        gamma = project(omega, expected, cfg)
        for col in GAMMA_COLS + DISCRETE_COLS:
            values = gamma[col].to_numpy()
            # NumPy's platform-native ``int`` is int32 on Windows and int64
            # on Linux. Canonicalize only the serialized regime labels so the
            # numerical golden-vector record is portable without changing the
            # kernel's public output dtype or arithmetic.
            if col == "stratum":
                values = values.astype(np.int64, copy=False)
            out[f"{name}__{col}"] = values
    return out


def test_golden_vectors_bit_exact():
    assert FIXTURE.exists(), (
        "golden fixture missing; regenerate ONLY as part of a certified "
        "kernel change: python tests/test_equivalence.py --regenerate"
    )
    golden = np.load(FIXTURE)
    current = _project_current()
    assert set(golden.files) == set(current.keys())
    for key in golden.files:
        a, b = golden[key], np.asarray(current[key])
        assert a.dtype == b.dtype, f"{key}: dtype changed {a.dtype} -> {b.dtype}"
        equal = (np.array_equal(a, b, equal_nan=True)
                 if np.issubdtype(a.dtype, np.floating)
                 else np.array_equal(a, b))
        assert equal, (
            f"{key}: kernel output diverged from certified 0.2.1 golden "
            f"vectors — bit-exact reproduction is required"
        )


if __name__ == "__main__":
    if "--regenerate" in sys.argv:
        np.savez_compressed(FIXTURE, **_project_current())
        print(f"golden vectors written: {FIXTURE}")
    else:
        test_golden_vectors_bit_exact()
        print("golden vectors reproduced bit-exactly")
