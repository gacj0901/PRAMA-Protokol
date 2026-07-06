"""PRAMA Protokol — Compliance Module.

Mechanical verification of the Observation Interface contract (AS-1 §5, §8).
Analytical argument without a passing record does not establish conformance;
these checks ARE the record.

    check_causality        — C2: truncation invariance of ω̂
    check_degeneration     — C3: Δ must not collapse into normalized activity
    check_scale_invariance — C4: rescaling raw inputs leaves Γ unchanged
    run_all                — full record as a dict, ready to commit
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from .kernel import KernelConfig, project

__all__ = [
    "check_causality",
    "check_degeneration",
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
) -> dict:
    """C3 — Degeneration statistic.

    Degeneration (the NYISO failure mode) means Δ has collapsed into
    normalized activity: the form Δ_deg = |ω − c|/(c + 1) with a constant
    (or slowly drifting) reference c. Two-part criterion:

      (a) absolute:  |r_Δω| < r*                      — dense streams; or
      (b) relative:  |r_Δω| < |r_deg| − 0.01          — the interface's Δ
          decouples strictly more than the canonical degenerate Δ built
          from the causal running mean of ω. Necessary for sparse event
          streams, where Δ and ω correlate mechanically because most
          information IS the activity spike.

    A Δ that is neither below r* nor below the degenerate baseline is
    indistinguishable from normalized activity and fails.
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

    passed = (abs(r) < r_star) or (abs(r) < abs(r_deg) - 0.01)
    detail = (
        f"r_Δω = {r:+.3f} (absolute threshold r* = {r_star}; "
        f"degenerate baseline r_deg = {r_deg:+.3f})"
    )
    return {"check": "C3 degeneration", "passed": passed, "detail": detail,
            "r_delta_omega": r, "r_degenerate": r_deg}


def check_scale_invariance(
    pipeline_fn: Callable[[np.ndarray], pd.DataFrame],
    raw: np.ndarray,
    factors: tuple = (1e-3, 1e-1, 10.0, 1e3),
    atol: float = 1e-9,
) -> dict:
    """C4 — Rescaling test.

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
                return {"check": "C4 scale invariance", "passed": False,
                        "detail": f"Γ.{col} changed under c={c} (max diff {d:.3e})"}
    return {"check": "C4 scale invariance", "passed": True,
            "detail": f"Γ invariant under rescaling factors {factors}"}


def run_all(
    raw: np.ndarray,
    normalize_fn: Callable[[np.ndarray], np.ndarray],
    expectation_fn: Callable[[np.ndarray], np.ndarray],
    cfg: KernelConfig | None = None,
    r_star: float = 0.5,
) -> dict:
    """Run the full mechanical record for a deployment.

    raw            : raw domain measurements ω̃
    normalize_fn   : the interface's explicit normalization  ω̃ → ω   (C4)
    expectation_fn : the interface's causal expectation      ω → ω̂  (C2, C3)
    """
    if cfg is None:
        cfg = KernelConfig()

    def pipeline(x: np.ndarray) -> pd.DataFrame:
        om = normalize_fn(x)
        return project(om, expectation_fn(om), cfg)

    omega = normalize_fn(np.asarray(raw, dtype=float))
    gamma = project(omega, expectation_fn(omega), cfg)

    record = {
        "C2": check_causality(expectation_fn, omega),
        "C3": check_degeneration(gamma["delta"].to_numpy(), omega, r_star=r_star),
        "C4": check_scale_invariance(pipeline, raw),
    }
    record["all_passed"] = all(v["passed"] for v in record.values() if isinstance(v, dict))
    return record
