"""Equivalence certification against the validated reference implementation.

The extracted universal kernel and the generalized causal expectation MUST
reproduce, bit-identically, the outputs of `Aptadynamic-Electrical-Grid`
(the BPA/NYISO-validated code) when fed the same inputs.

Run inside an environment where the reference package is importable as
`aptadynamic_eg` (e.g. `pip install -e` both repositories):

    pytest tests/test_equivalence.py -v

If the reference package is absent, these tests are skipped — the structural
tests in test_kernel.py still run.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from prama_protokol import KernelConfig, project
from prama_protokol.interface import causal_conditional_mean

ref = pytest.importorskip(
    "aptadynamic_eg", reason="reference implementation not installed"
)
from aptadynamic_eg import projection as ref_projection  # noqa: E402
from aptadynamic_eg import omega as ref_omega  # noqa: E402


def _synthetic_omega(n: int = 24 * 400, seed: int = 7) -> pd.DataFrame:
    """A year+ of synthetic hourly observables with seasonal structure."""
    rng = np.random.default_rng(seed)
    t0 = 1_100_000_000
    t = t0 + np.arange(n) * 3600
    hours = pd.to_datetime(t, unit="s", utc=True)
    base = 1.5 + np.sin(2 * np.pi * hours.hour / 24) + 0.5 * np.sin(
        2 * np.pi * hours.month / 12
    )
    intensity = rng.poisson(np.clip(base, 0.1, None)).astype(float)
    return pd.DataFrame({"t": t, "intensity": intensity})


def test_kernel_projection_identical():
    """π extracted == π validated, on every Γ column."""
    om = _synthetic_omega()
    ref_cfg = ref_projection.ProjectionConfig()
    ref_out = ref_projection.project(om, ref_cfg)

    expected = ref_omega.expected_profile(om)
    new_cfg = KernelConfig(
        tau_memory=ref_cfg.tau_memory,
        lambda_eq=ref_cfg.lambda_eq,
        lambda_recovery=ref_cfg.lambda_recovery,
        lambda_min=ref_cfg.lambda_min,
        theta_scale=ref_cfg.theta_scale,
        g_smooth=ref_cfg.g_smooth,
        kappa=ref_cfg.kappa,
    )
    new_out = project(om["intensity"].to_numpy(float), expected, new_cfg)

    pairs = [
        ("delta", "delta"), ("xi", "xi"), ("lambda", "lambda"),
        ("theta", "theta"), ("M", "M"), ("G", "G"),
    ]
    for ref_col, new_col in pairs:
        assert np.array_equal(
            ref_out[ref_col].to_numpy(), new_out[new_col].to_numpy()
        ), f"Γ.{new_col} differs from the validated reference"

    assert np.array_equal(
        ref_out["latent_collapse"].to_numpy(), new_out["latent_collapse"].to_numpy()
    )
    assert np.array_equal(
        ref_out["stratum"].to_numpy(), new_out["stratum"].to_numpy()
    )


def test_causal_expectation_identical():
    """CausalConditionalMean(month, hour) == the grid's seasonal profile."""
    om = _synthetic_omega(seed=11)
    ref_exp = ref_omega.expected_profile(om)

    ts = pd.to_datetime(om["t"], unit="s", utc=True)
    ctx = np.stack([ts.dt.month.to_numpy(), ts.dt.hour.to_numpy()], axis=1)
    new_exp = causal_conditional_mean(
        om["intensity"].to_numpy(float), ctx,
        min_context_count=10, min_global_count=24 * 30,
    )

    assert np.array_equal(np.isnan(ref_exp), np.isnan(new_exp)), "warm-up pattern differs"
    ok = ~np.isnan(ref_exp)
    assert np.array_equal(ref_exp[ok], new_exp[ok]), "causal expectation differs"
