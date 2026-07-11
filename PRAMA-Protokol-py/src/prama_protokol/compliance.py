"""PRAMA Protokol — Compliance Module.

Mechanical verification of the Observation Interface contract.
Analytical argument without a passing record does not establish conformance;
these checks ARE the record.

Identifier namespaces
---------------------
The record keys follow the DEPLOYED domain-contract numbering
(`O_D Observation Contract` C1–C7), which is the numbering carried by
domain evidence. Where AS-1's interface numbering differs, the historical
AS-1 identifier is noted in the check's detail, never used as a record key.

    check_causality        — C2 : truncation invariance of ω̂
    check_degeneration     — C3 : Δ must not collapse into normalized
                                  activity (anti-degeneration gate)
    check_inductive_ratio  — ρ_I: explanatory ratio of the induction layer
                                  (band diagnostic; O_D deployment doc §8.2)
    check_density          — C4 : informational density of Ξ against a
                                  marginal/seasonal-preserving null (§8.3)
    check_memory_ratio     — MEM: τ_K ≪ L_cal condition (§8.4)
    check_scale_invariance — N1 : rescaling test of the normalization
                                  contract 𝔑_D (historically AS-1 "C4")
    run_all                — full record as a dict, ready to commit

Gate thresholds (s_min, ρ_I band, f_star, min_memory_ratio) are declared
in each domain's pre-registration, per induction epoch (C7). When a
threshold is not supplied, the corresponding check is computed and
reported as INFORMATIONAL (`passed = None`): it never certifies and never
blocks. A committed confirmatory record MUST supply every threshold.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from .kernel import KernelConfig, project

__all__ = [
    "check_causality",
    "check_degeneration",
    "check_inductive_ratio",
    "check_density",
    "check_memory_ratio",
    "check_scale_invariance",
    "run_all",
]


def check_causality(
    expectation_fn: Callable[[np.ndarray], np.ndarray],
    omega: np.ndarray,
    sample_points: int = 8,
    rtol: float = 0.0,
    atol: float = 0.0,
) -> dict:
    """C2 — Strict causality by truncation invariance.

    Truncating the stream at t must leave ω̂(s) unchanged for all s ≤ t.
    `expectation_fn` maps a stream prefix to its expectation array.
    Exact equality is required by default (fixed arithmetic).
    """
    omega = np.asarray(omega, dtype=float)
    n = len(omega)
    full = expectation_fn(omega)
    cuts = np.linspace(n // 4, n - 1, sample_points, dtype=int)
    worst = 0.0
    for t in cuts:
        trunc = expectation_fn(omega[: t + 1])
        a, b = full[: t + 1], trunc
        both = ~(np.isnan(a) | np.isnan(b))
        if not np.array_equal(np.isnan(a), np.isnan(b)):
            return {"check": "C2 causality", "passed": False,
                    "detail": f"NaN warm-up pattern changed under truncation at t={t}"}
        diff = float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0
        worst = max(worst, diff)
        if not np.allclose(a[both], b[both], rtol=rtol, atol=atol):
            return {"check": "C2 causality", "passed": False,
                    "detail": f"expectation changed under truncation at t={t} (max diff {diff:.3e})"}
    return {"check": "C2 causality", "passed": True,
            "detail": f"invariant under {sample_points} truncations (max diff {worst:.3e})"}


def check_degeneration(
    delta: np.ndarray,
    omega: np.ndarray,
    r_star: float = 0.5,
    s_min: float = 0.01,
) -> dict:
    """C3 — Anti-degeneration gate.

    Degeneration (the NYISO failure mode) means Δ has collapsed into
    normalized activity: the form Δ_deg = |ω − c|/(c + 1) with a constant
    (or slowly drifting) reference c. Two-branch criterion; passing EITHER
    branch passes the gate:

      (a) absolute:  |r_Δω| < r_star                 — dense streams; or
      (b) relative:  |r_deg| − |r_Δω| > s_min        — the interface's Δ
          decouples strictly more than the canonical degenerate Δ built
          from the causal running mean of ω. Necessary for sparse event
          streams, where Δ and ω correlate mechanically because most
          information IS the activity spike.

    A Δ that satisfies neither branch is indistinguishable from
    normalized activity and fails. The separation |r_deg| − |r_Δω|, the
    thresholds in force, and the deciding branch are all part of the
    record: a marginal failure (positive separation below s_min) must be
    legible from the record alone, without recomputation.

    `r_star` and `s_min` are declared in the domain pre-registration; the
    defaults reproduce the values in force (r_star=0.5, s_min=0.01).
    """
    delta = np.asarray(delta, dtype=float)
    omega = np.asarray(omega, dtype=float)
    ok = ~(np.isnan(delta) | np.isnan(omega))
    if ok.sum() < 3 or np.std(delta[ok]) == 0 or np.std(omega[ok]) == 0:
        return {"check": "C3 degeneration", "passed": False,
                "detail": "insufficient variation to compute r_Δω"}
    r = float(np.corrcoef(delta[ok], omega[ok])[0, 1])

    # canonical degenerate Δ: constant-like causal reference (running mean)
    c = np.cumsum(omega) / (np.arange(len(omega)) + 1)
    delta_deg = np.abs(omega - c) / (c + 1.0)
    if np.std(delta_deg[ok]) == 0:
        r_deg = 1.0
    else:
        r_deg = float(np.corrcoef(delta_deg[ok], omega[ok])[0, 1])

    separation = abs(r_deg) - abs(r)
    passed_absolute = abs(r) < r_star
    passed_relative = separation > s_min
    passed = passed_absolute or passed_relative
    if passed_absolute and passed_relative:
        branch = "both"
    elif passed_absolute:
        branch = "absolute"
    elif passed_relative:
        branch = "relative"
    else:
        branch = "none"
    detail = (
        f"r_Δω = {r:+.3f}, r_deg = {r_deg:+.3f}, "
        f"separation = {separation:+.4f} (s_min = {s_min}), "
        f"absolute threshold r_star = {r_star}, branch = {branch}"
    )
    return {"check": "C3 degeneration", "passed": passed, "detail": detail,
            "r_delta_omega": r, "r_degenerate": r_deg,
            "separation": separation, "s_min": s_min, "r_star": r_star,
            "branch": branch}


def check_inductive_ratio(
    omega: np.ndarray,
    expected: np.ndarray,
    band: tuple | None = None,
) -> dict:
    """ρ_I — Explanatory ratio of the induction layer (deployment doc §8.2).

    ρ_I = 1 − Var(ω − ω̂)/Var(ω), over rows with a defined expectation.
    The admissibility condition is BILATERAL: c_low ≤ ρ_I ≤ c_high,
    because both extremes are pathological — ρ_I → 1 degenerates Δ toward
    noise; ρ_I → 0 reduces Δ to rescaled intensity.

    `band = (c_low, c_high)` is declared per domain and per induction
    epoch. Without a band the check is informational (`passed = None`).
    """
    omega = np.asarray(omega, dtype=float)
    expected = np.asarray(expected, dtype=float)
    ok = ~np.isnan(expected) & ~np.isnan(omega)
    if ok.sum() < 3 or np.var(omega[ok]) == 0:
        return {"check": "RHO_I inductive ratio", "passed": False,
                "detail": "insufficient variation to compute rho_I"}
    resid = omega[ok] - expected[ok]
    rho = float(1.0 - np.var(resid) / np.var(omega[ok]))
    if band is None:
        return {"check": "RHO_I inductive ratio", "passed": None,
                "detail": f"rho_I = {rho:+.4f} (INFORMATIONAL: no band declared)",
                "rho_I": rho, "band": None}
    lo, hi = float(band[0]), float(band[1])
    passed = lo <= rho <= hi
    return {"check": "RHO_I inductive ratio", "passed": passed,
            "detail": f"rho_I = {rho:+.4f}, declared band [{lo}, {hi}]",
            "rho_I": rho, "band": (lo, hi)}


def _ema(delta: np.ndarray, tau_memory: float) -> np.ndarray:
    """Bit-exact replica of the kernel's Ξ recurrence (kernel.py):
    xi[0] = 0;  xi[i] = a·xi[i−1] + (1−a)·delta[i],  a = exp(−1/τ)."""
    a = np.exp(-1.0 / tau_memory)
    n = len(delta)
    xi = np.zeros(n)
    for i in range(1, n):
        xi[i] = a * xi[i - 1] + (1 - a) * delta[i]
    return xi


def check_density(
    gamma: pd.DataFrame,
    cfg: KernelConfig,
    context: np.ndarray | None = None,
    n_null: int = 200,
    seed: int = 0,
    f_star: float | None = None,
) -> dict:
    """C4 — Informational density of Ξ (deployment doc §8.3).

    C4_D = Var(Ξ) / E[Var(Ξ_null)], where the null permutes Δ while
    preserving its marginal distribution — and, when a `context` array of
    stratum labels is supplied (e.g. month×hour ids), permuting WITHIN
    strata so the seasonal composition is preserved too. What the null
    destroys is exactly the residual temporal dependence that the
    accumulator is supposed to integrate. C4_D ≈ 1 means Ξ carries no
    structure beyond marginal (and declared-seasonal) noise; C4_D ≫ 1
    means the accumulator integrates real temporal organization.

    NOTE — null choice: a circular shift is NOT a valid null for this
    statistic (rotation preserves internal autocorrelation, so
    Var(Ξ_shifted) ≈ Var(Ξ) and the ratio is vacuously ≈ 1). Circular
    shifts remain the correct null for outcome-ALIGNMENT tests; density
    requires a dependence-destroying, marginal-preserving permutation.

    Before trusting any null, the internal EMA replica is verified to
    reproduce Γ.Ξ from Γ.Δ EXACTLY; on mismatch the check fails as
    internally inconsistent rather than reporting a ratio.

    `f_star`, `n_null`, `seed` and the stratification are declared in the
    domain pre-registration. Without `f_star` the check is informational.
    """
    delta = gamma["delta"].to_numpy(dtype=float)
    xi = gamma["xi"].to_numpy(dtype=float)
    n = len(delta)
    if n < 8:
        return {"check": "C4 informational density", "passed": False,
                "detail": "stream too short for a density null"}

    xi_replica = _ema(delta, cfg.tau_memory)
    if not np.array_equal(xi_replica, xi):
        return {"check": "C4 informational density", "passed": False,
                "detail": "internal EMA replica does not reproduce Γ.Ξ "
                          "bit-exactly; refusing to compute nulls against "
                          "an inconsistent accumulator"}

    var_obs = float(np.var(xi))
    rng = np.random.default_rng(seed)
    if context is not None:
        context = np.asarray(context)
        if context.shape[0] != n:
            return {"check": "C4 informational density", "passed": False,
                    "detail": "context array length mismatch"}
        groups = [np.flatnonzero(context == u) for u in np.unique(context)]

    null_vars = np.empty(n_null)
    for k in range(n_null):
        d = delta.copy()
        if context is None:
            rng.shuffle(d)
        else:
            for idx in groups:
                d[idx] = d[rng.permutation(idx)]
        null_vars[k] = np.var(_ema(d, cfg.tau_memory))

    mean_null = float(null_vars.mean())
    if mean_null == 0.0:
        return {"check": "C4 informational density", "passed": False,
                "detail": "null variance is zero; degenerate Δ stream"}
    ratio = var_obs / mean_null
    q = np.quantile(null_vars, [0.05, 0.5, 0.95])
    stratified = "stratified" if context is not None else "unstratified"
    base = (f"C4_D = {ratio:.3f} ({stratified} permutation null, "
            f"n_null={n_null}, seed={seed}; Var(Ξ)={var_obs:.3e}, "
            f"null Var q05/q50/q95 = {q[0]:.3e}/{q[1]:.3e}/{q[2]:.3e})")
    if f_star is None:
        return {"check": "C4 informational density", "passed": None,
                "detail": base + " (INFORMATIONAL: no f_star declared)",
                "C4_D": ratio, "f_star": None, "n_null": n_null,
                "seed": seed, "stratified": context is not None}
    passed = ratio >= f_star
    return {"check": "C4 informational density", "passed": passed,
            "detail": base + f", declared f_star = {f_star}",
            "C4_D": ratio, "f_star": f_star, "n_null": n_null,
            "seed": seed, "stratified": context is not None}


def check_memory_ratio(
    cfg: KernelConfig,
    n_cal: int,
    min_ratio: float | None = None,
) -> dict:
    """MEM — τ_K ≪ L_cal condition (deployment doc §8.4).

    When the memory scale is comparable with the record length, the
    accumulator describes the observation window rather than a
    representative property of the system (Corpus). The minimum admissible
    ratio L_cal/τ_K is declared in the domain contract; without it the
    check is informational.
    """
    ratio = float(n_cal) / float(cfg.tau_memory)
    if min_ratio is None:
        return {"check": "MEM memory ratio", "passed": None,
                "detail": f"L_cal/tau_K = {ratio:.1f} "
                          "(INFORMATIONAL: no min_ratio declared)",
                "ratio": ratio, "min_ratio": None}
    passed = ratio >= min_ratio
    return {"check": "MEM memory ratio", "passed": passed,
            "detail": f"L_cal/tau_K = {ratio:.1f}, declared min = {min_ratio}",
            "ratio": ratio, "min_ratio": min_ratio}


def check_scale_invariance(
    pipeline_fn: Callable[[np.ndarray], pd.DataFrame],
    raw: np.ndarray,
    factors: tuple = (1e-3, 1e-1, 10.0, 1e3),
    atol: float = 1e-9,
) -> dict:
    """N1 — Rescaling test of the normalization contract 𝔑_D.

    (Historically labeled "C4" in AS-1's interface numbering; the record
    key is N1 to avoid colliding with the deployed domain contract, where
    C4 is informational density.)

    `pipeline_fn` maps RAW measurements ω̃ through the interface's
    normalization and the kernel to the Γ trajectory. Rescaling ω̃ by any
    c > 0 must leave Γ unchanged, with no re-tuning of parameters.
    """
    raw = np.asarray(raw, dtype=float)
    ref = pipeline_fn(raw)
    cols = ["delta", "xi", "lambda", "theta", "M", "G"]
    for c in factors:
        alt = pipeline_fn(raw * c)
        for col in cols:
            a = ref[col].to_numpy()
            b = alt[col].to_numpy()
            if not np.allclose(a, b, atol=atol, equal_nan=True):
                d = float(np.nanmax(np.abs(a - b)))
                return {"check": "N1 scale invariance", "passed": False,
                        "detail": f"Γ.{col} changed under c={c} (max diff {d:.3e})"}
    return {"check": "N1 scale invariance", "passed": True,
            "detail": f"Γ invariant under rescaling factors {factors}"}


def run_all(
    raw: np.ndarray,
    normalize_fn: Callable[[np.ndarray], np.ndarray],
    expectation_fn: Callable[[np.ndarray], np.ndarray],
    cfg: KernelConfig | None = None,
    r_star: float = 0.5,
    s_min: float = 0.01,
    rho_band: tuple | None = None,
    f_star: float | None = None,
    min_memory_ratio: float | None = None,
    n_cal: int | None = None,
    context: np.ndarray | None = None,
    n_null: int = 200,
    null_seed: int = 0,
    induction_epoch: str | None = None,
) -> dict:
    """Run the full mechanical record for a deployment.

    raw            : raw domain measurements ω̃
    normalize_fn   : the interface's explicit normalization  ω̃ → ω   (N1)
    expectation_fn : the interface's causal expectation      ω → ω̂  (C2, C3)
    n_cal          : calibration length in bins for MEM; defaults to the
                     full stream length (recorded as such)
    context        : optional stratum labels for the C4 density null
    induction_epoch: C7 — identifier of the induction epoch under which
                     this record is produced (e.g. "induction_v1").
                     Recorded verbatim; gate passes do NOT transfer
                     across epochs.

    Checks without a declared threshold are reported with passed=None
    (informational) and excluded from `all_passed`; the record lists them
    under `informational` so a confirmatory commit can be rejected if any
    gate was left undeclared.
    """
    if cfg is None:
        cfg = KernelConfig()

    def pipeline(x: np.ndarray) -> pd.DataFrame:
        om = normalize_fn(x)
        return project(om, expectation_fn(om), cfg)

    omega = normalize_fn(np.asarray(raw, dtype=float))
    expected = expectation_fn(omega)
    gamma = project(omega, expected, cfg)
    if n_cal is None:
        n_cal = len(omega)

    record = {
        "C2": check_causality(expectation_fn, omega),
        "C3": check_degeneration(gamma["delta"].to_numpy(), omega,
                                 r_star=r_star, s_min=s_min),
        "RHO_I": check_inductive_ratio(omega, expected, band=rho_band),
        "C4": check_density(gamma, cfg, context=context, n_null=n_null,
                            seed=null_seed, f_star=f_star),
        "MEM": check_memory_ratio(cfg, n_cal, min_ratio=min_memory_ratio),
        "N1": check_scale_invariance(pipeline, raw),
    }
    checks = {k: v for k, v in record.items() if isinstance(v, dict)}
    record["informational"] = sorted(
        k for k, v in checks.items() if v["passed"] is None
    )
    record["all_passed"] = all(
        v["passed"] for v in checks.values() if v["passed"] is not None
    )
    record["induction_epoch"] = induction_epoch
    record["n_cal"] = int(n_cal)
    return record
