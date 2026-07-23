"""Tests for the normative KernelV3 compliance module."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from prama_protokol import KernelConfig, KernelConfigV3, compliance, project_v3
from prama_protokol.interface import causal_conditional_mean


def _stream(n=4000, seed=5):
    rng = np.random.default_rng(seed)
    raw = rng.gamma(2.0, 100.0, n)

    def normalize(x):
        cm = np.cumsum(x) / (np.arange(len(x)) + 1)
        return x / np.maximum(cm, 1e-12)

    def expectation(om):
        ctx = np.arange(len(om)) % 24
        return causal_conditional_mean(om, ctx, 10, 200)

    return raw, normalize, expectation


def test_public_compliance_is_bound_to_v3():
    assert compliance.KERNEL_API == "KernelV3/project_v3"
    assert compliance.COMPLIANCE_SCHEMA == "prama.compliance.v3"
    assert compliance.run_all.__annotations__["cfg"] == "KernelConfigV3 | None"
    try:
        compliance.check_memory_ratio(KernelConfig(), n_cal=1000)
    except TypeError as exc:
        assert "KernelConfigV3" in str(exc)
    else:
        raise AssertionError("legacy KernelConfig crossed the normative boundary")


def test_degeneration_record_is_self_sufficient():
    """Marginal failures must be legible from the record alone."""
    rng = np.random.default_rng(13)
    omega = rng.gamma(2.0, 1.0, 4000)
    g = project_v3(omega, np.full(len(omega), 1.0))
    rec = compliance.check_degeneration(g.delta, omega,
                                        r_star=0.5, s_min=0.01)
    for key in ("separation", "s_min", "r_star", "branch",
                "r_delta_omega", "r_degenerate"):
        assert key in rec
    assert rec["branch"] == "none" and not rec["passed"]
    # s_min is a real parameter: an absurdly permissive s_min flips the gate
    rec2 = compliance.check_degeneration(g.delta, omega,
                                         r_star=0.5, s_min=-10.0)
    assert rec2["passed"] and rec2["branch"] in ("relative", "both")


def test_inductive_ratio_band_is_bilateral():
    rng = np.random.default_rng(3)
    omega = rng.gamma(2.0, 1.0, 3000)
    perfect = omega.copy()            # rho_I = 1  -> must FAIL a bilateral band
    none_at_all = np.full_like(omega, omega.mean())  # rho_I ~ 0
    r_hi = compliance.check_inductive_ratio(omega, perfect, band=(0.05, 0.95))
    r_lo = compliance.check_inductive_ratio(omega, none_at_all, band=(0.05, 0.95))
    assert not r_hi["passed"] and r_hi["rho_I"] > 0.99
    assert not r_lo["passed"] and abs(r_lo["rho_I"]) < 0.05
    info = compliance.check_inductive_ratio(omega, perfect, band=None)
    assert info["passed"] is None


def test_density_ema_self_consistency_guard():
    """If Γ.Ξ cannot be reproduced from Γ.Δ, the check must refuse."""
    rng = np.random.default_rng(1)
    omega = rng.gamma(2.0, 1.0, 2000)
    cfg = KernelConfigV3(tau=64)
    gamma = project_v3(omega, np.roll(omega, 1), cfg)
    ok = compliance.check_density(gamma, cfg, n_null=20, f_star=None)
    assert ok["passed"] is None and "C4_D" in ok       # consistent -> computes
    bad_xi = gamma.xi.copy()
    bad_xi[100] += 1e-9                                  # corrupt one bit
    bad = replace(gamma, xi=bad_xi)
    rec = compliance.check_density(bad, cfg, n_null=20, f_star=None)
    assert rec["passed"] is False and "inconsist" in rec["detail"]


def test_density_separates_structure_from_noise():
    """Autocorrelated Δ must score higher density than white Δ, and the
    permutation null must not be vacuous (ratio ≈ 1) for structured Δ."""
    n, cfg = 6000, KernelConfigV3(tau=64)
    rng = np.random.default_rng(7)
    white = rng.gamma(2.0, 1.0, n)
    ar = np.zeros(n)
    eps = rng.normal(0, 1, n)
    for i in range(1, n):
        ar[i] = 0.95 * ar[i - 1] + eps[i]
    ar = np.abs(ar) + 0.1

    def gamma_for(om):
        return project_v3(om, np.full(n, np.mean(om)), cfg)

    d_white = compliance.check_density(gamma_for(white), cfg, n_null=50, seed=0)
    d_ar = compliance.check_density(gamma_for(ar), cfg, n_null=50, seed=0)
    assert d_ar["C4_D"] > 3.0 * d_white["C4_D"]
    assert d_ar["C4_D"] > 2.0
    assert 0.5 < d_white["C4_D"] < 2.0


def test_memory_ratio():
    cfg = KernelConfigV3(tau=336)
    rec = compliance.check_memory_ratio(cfg, n_cal=33600, min_ratio=20)
    assert rec["passed"] and abs(rec["ratio"] - 100.0) < 1e-12
    rec = compliance.check_memory_ratio(cfg, n_cal=1000, min_ratio=20)
    assert not rec["passed"]
    rec = compliance.check_memory_ratio(cfg, n_cal=1000, min_ratio=None)
    assert rec["passed"] is None


def test_run_all_record_structure_and_epoch():
    raw, normalize, expectation = _stream()
    record = compliance.run_all(raw, normalize, expectation,
                                induction_epoch="induction_v1", n_null=20)
    for key in ("C2", "C3", "RHO_I", "C4", "MEM", "N1",
                "all_passed", "informational", "induction_epoch", "n_cal"):
        assert key in record
    assert record["schema_version"] == "prama.compliance.v3"
    assert record["kernel_api"] == "KernelV3/project_v3"
    assert record["induction_epoch"] == "induction_v1"
    # thresholds not declared -> informational, excluded from all_passed
    assert set(record["informational"]) == {"RHO_I", "C4", "MEM"}
    assert record["C2"]["passed"] and record["N1"]["passed"]
