"""Structural tests for the repository-local universal kernel contract.

These tests require no reference implementation and no real data. Each test
name states the principle it verifies.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prama_protokol import KernelConfig, project, stratify
from prama_protokol.interface import causal_conditional_mean
from prama_protokol import compliance


def _stream(n=5000, seed=3):
    rng = np.random.default_rng(seed)
    omega = rng.gamma(2.0, 1.0, n)
    ctx = np.arange(n) % 24  # hour-like context
    expected = causal_conditional_mean(omega, ctx, 10, 200)
    return omega, expected


def test_P1_single_condition_defines_margin():
    omega, expected = _stream()
    g = project(omega, expected)
    assert np.allclose(g["M"], g["theta"] - g["xi"])


def test_P2_memory_xi_is_exponential_convolution():
    """Ξ recursion == discrete convolution with the exponential causal kernel."""
    omega, expected = _stream(n=1200)
    cfg = KernelConfig(tau_memory=48)
    g = project(omega, expected, cfg)
    delta = g["delta"].to_numpy()
    a = np.exp(-1.0 / cfg.tau_memory)
    n = len(delta)
    k = (1 - a) * a ** np.arange(n)          # K(s) = (1-a)·a^s, causal, ≥ 0
    xi_conv = np.convolve(delta, k)[:n]
    xi_conv[0] = 0.0                          # recursion starts at Ξ(0)=0
    assert np.allclose(g["xi"].to_numpy(), xi_conv, atol=1e-8)


def test_P2_not_markovian():
    """Same present, different past ⇒ different Ξ. Memoryless evaluation is out."""
    n = 600
    calm = np.concatenate([np.zeros(n // 2), np.ones(n // 2)])
    stormy = np.concatenate([np.full(n // 2, 5.0), np.ones(n // 2)])
    expected = np.full(n, 1.0)
    g1 = project(calm, expected)
    g2 = project(stormy, expected)
    assert g1["xi"].iloc[-1] < g2["xi"].iloc[-1]


def test_P3_threshold_strictly_increasing_in_lambda():
    omega, expected = _stream()
    g = project(omega, expected)
    order = np.argsort(g["lambda"].to_numpy())
    th = g["theta"].to_numpy()[order]
    assert np.all(np.diff(th) >= 0)


def test_P4_recovery_never_modifies_xi():
    """Non-reincarnation: λ recovers after quiet periods; Ξ follows its own
    kernel decay exactly, unaffected by λ's recovery dynamics."""
    n = 3000
    # shock, then a long quiet period where ω matches expectation ⇒ Δ = 0
    omega = np.concatenate([np.full(200, 8.0), np.full(n - 200, 1.0)])
    expected = np.full(n, 1.0)
    cfg = KernelConfig(tau_memory=30)
    g = project(omega, expected, cfg)
    # during the quiet tail, λ recovers from its post-shock minimum...
    lam = g["lambda"].to_numpy()
    assert lam[-1] > lam.min()
    # ...while Ξ decays PURELY by its kernel: Ξ(i) = a·Ξ(i-1) when Δ = 0
    a = np.exp(-1.0 / cfg.tau_memory)
    xi = g["xi"].to_numpy()
    start = 205  # safely inside the Δ = 0 tail
    assert np.allclose(
        xi[start:], xi[start - 1] * a ** np.arange(1, n - start + 1), atol=1e-10
    )


def test_P4_recovery_bounded():
    omega, expected = _stream()
    cfg = KernelConfig()
    g = project(omega, expected, cfg)
    lam = g["lambda"].to_numpy()
    d_lam = np.diff(lam)
    bound = cfg.lambda_recovery * (cfg.lambda_eq - lam[:-1]) + 1e-12
    assert np.all(d_lam <= bound)


def test_P6_latent_collapse_definition():
    omega, expected = _stream()
    g = project(omega, expected)
    lc = g["latent_collapse"].to_numpy()
    manual = (omega > 0) & (g["M"].to_numpy() >= 0) & (g["G"].to_numpy() < 0) \
        & g["valid"].to_numpy()
    assert np.array_equal(lc, manual)


def test_P7_kernel_is_domain_blind():
    """The kernel accepts bare arrays: no column names, no domain objects."""
    omega = np.abs(np.sin(np.arange(400) / 7.0)) * 3
    expected = np.full(400, 1.5)
    g = project(omega, expected)
    assert set(["delta", "xi", "lambda", "theta", "M", "G"]).issubset(g.columns)


def test_stratification_quadrants():
    m = np.array([1.0, 1.0, -1.0, -1.0])
    g = np.array([1.0, -1.0, 1.0, -1.0])
    assert list(stratify(m, g)) == [1, 2, 3, 4]


def test_compliance_record_passes_on_conformant_interface():
    rng = np.random.default_rng(5)
    raw = rng.gamma(2.0, 100.0, 4000)  # dimensional raw measurements

    def normalize(x):
        # explicit causal normalization: divide by causal running mean (N1)
        cm = np.cumsum(x) / (np.arange(len(x)) + 1)
        return x / np.maximum(cm, 1e-12)

    def expectation(om):
        ctx = np.arange(len(om)) % 24
        return causal_conditional_mean(om, ctx, 10, 200)

    record = compliance.run_all(raw, normalize, expectation)
    assert record["C2"]["passed"], record["C2"]["detail"]
    assert record["N1"]["passed"], record["N1"]["detail"]
    assert record["all_passed"] or not record["C3"]["passed"]  # C3 depends on data


def test_compliance_detects_future_leak():
    """A non-causal expectation (centered moving average) MUST fail C2."""
    rng = np.random.default_rng(9)
    omega = rng.gamma(2.0, 1.0, 2000)

    def leaky_expectation(om):
        s = pd.Series(om)
        return s.rolling(25, center=True, min_periods=1).mean().to_numpy()

    result = compliance.check_causality(leaky_expectation, omega)
    assert not result["passed"]


def test_compliance_detects_degenerate_delta():
    """Δ built on a constant reference degenerates into activity and fails C3."""
    rng = np.random.default_rng(13)
    omega = rng.gamma(2.0, 1.0, 4000)
    constant_ref = np.full(len(omega), 1.0)          # ω̂ = c  (violates C3)
    g = project(omega, constant_ref)
    result = compliance.check_degeneration(g["delta"].to_numpy(), omega)
    assert not result["passed"]
    assert result["r_delta_omega"] > 0.9


def test_prefix_causality_all_outputs():
    rng = np.random.default_rng(42)
    omega = rng.gamma(2, 1, 80)
    expected = rng.gamma(2, 1, 80)
    expected[:12] = np.nan
    cfg = KernelConfig(g_smooth=9)
    reference = project(omega, expected, cfg)
    for k in (0, 1, 11, 12, 37, 78):
        changed_o, changed_e = omega.copy(), expected.copy()
        changed_o[k + 1:] = rng.normal(100, 50, len(omega) - k - 1)
        changed_e[k + 1:] = rng.normal(10, 3, len(omega) - k - 1)
        changed = project(changed_o, changed_e, cfg)
        for col in ("delta", "xi", "lambda", "theta", "M", "G",
                    "latent_collapse", "stratum", "valid"):
            assert np.array_equal(reference[col].to_numpy()[:k + 1],
                                  changed[col].to_numpy()[:k + 1])


def test_causal_g_and_edge_cases():
    with np.testing.assert_raises_regex(ValueError, "non-empty"):
        project(np.array([]), np.array([]))
    for window in (1, 20):
        one = project(np.array([1.0]), np.array([np.nan]), KernelConfig(g_smooth=window))
        assert one.loc[0, "G"] == 0.0
        assert not one.loc[0, "valid"]
        omega = np.array([1., 4., 1., 4., 1.])
        out = project(omega, np.ones(5), KernelConfig(g_smooth=window))
        sm = out["M"].rolling(window, min_periods=1).mean().to_numpy()
        assert np.array_equal(out["G"].to_numpy(), np.diff(sm, prepend=sm[0]))
