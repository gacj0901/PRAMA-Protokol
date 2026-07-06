"""PRAMA Protokol — Reference Kernel (π).

Universal aptadynamic projection:  Ω → Γ(t) = (Δ, Ξ, λ, Θ, M, G).

    Δ(t)  = |ω(t) − ω̂(t)| / (ω̂(t) + 1)      structural decoupling (AS-1 P5)
    Ξ(t)  = ∫ K(t−τ) Δ(τ) dτ                 non-Markovian tension accumulator,
                                              exponential causal kernel (P2)
    λ(t)  = historical permissivity: eroded by excess (Ξ−Θ)⁺, bounded
            recovery that NEVER modifies Ξ (P3, P4 — non-reincarnation)
    Θ(λ)  = endogenous threshold, strictly increasing in λ (P3)
    M(t)  = Θ(λ) − Ξ                          viability margin
    G(t)  = D⁺M (smoothed)                    margin generation power

Latent collapse (P6):  σ_op(t) = 1  ∧  M(t) ≥ 0  ∧  G(t) < 0.

Regime stratification S₁–S₄ on the (M, G) plane.

This module is the universal component of the protocol (AS-1 P7): it contains
no domain knowledge whatsoever. It never sees raw measurements; it receives
the observable stream ω and its strictly causal expectation ω̂, both produced
by an Observation Interface (see `prama_protokol.interface`).

Extracted from the reference implementation `Aptadynamic-Electrical-Grid`
(BPA/NYISO validation). Numerical equivalence with the reference is certified
by `tests/test_equivalence.py` and documented in EQUIVALENCE.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["KernelConfig", "project", "stratify"]


@dataclass
class KernelConfig:
    """Universal kernel parameters (fixed across domains — AS-1 C5).

    Time is measured in stream bins; defaults assume hourly bins, matching
    the validated reference configuration.
    """

    tau_memory: float = 24 * 14   # bins: memory scale of Ξ (~2 weeks at 1h bins)
    lambda_eq: float = 1.0        # permissivity equilibrium
    lambda_recovery: float = 0.005  # bounded recovery rate r (P4)
    lambda_min: float = 0.1      # floor of permissivity
    theta_scale: float = 2.0     # Θ(λ) = theta_scale · λ (strictly increasing)
    g_smooth: int = 24           # bins: smoothing window for D⁺M
    kappa: float = 0.05          # erosion coefficient of λ by excess (Ξ−Θ)⁺


def project(
    omega: np.ndarray,
    expected: np.ndarray,
    cfg: KernelConfig | None = None,
    sigma_op: np.ndarray | None = None,
) -> pd.DataFrame:
    """Project an observable stream onto the aptadynamic coordinates Γ.

    Parameters
    ----------
    omega : array of shape (n,)
        The dimensionless, normalized observable stream ω(t) (AS-1 C1, C4).
    expected : array of shape (n,)
        The strictly causal expectation ω̂(t) = E[ω(t) | past only] (C2).
        Positions where no causal expectation exists yet (warm-up) are NaN;
        Δ is defined as 0 there and the rows are marked invalid.
    cfg : KernelConfig, optional
        Universal kernel parameters. MUST be identical across domains (C5).
    sigma_op : boolean array of shape (n,), optional
        Operational-state indicator σ_op(t). Defaults to ω(t) > 0.

    Returns
    -------
    DataFrame with columns:
        delta, xi, lambda, theta, M, G, latent_collapse, stratum, valid
    """
    if cfg is None:
        cfg = KernelConfig()

    obs = np.asarray(omega, dtype=float)
    exp_ = np.asarray(expected, dtype=float)
    if obs.shape != exp_.shape:
        raise ValueError("omega and expected must have the same shape")

    valid = ~np.isnan(exp_)
    delta = np.zeros(len(obs))
    delta[valid] = np.abs(obs[valid] - exp_[valid]) / (exp_[valid] + 1.0)

    n = len(delta)
    a = np.exp(-1.0 / cfg.tau_memory)
    xi = np.zeros(n)
    lam = np.full(n, cfg.lambda_eq)
    excess_acc = np.zeros(n)  # accumulated excess 𝒜(t): monotone, never erased
    theta = np.zeros(n)
    theta[0] = cfg.theta_scale * cfg.lambda_eq

    for i in range(1, n):
        # P2 — non-Markovian accumulator (exponential causal kernel)
        xi[i] = a * xi[i - 1] + (1 - a) * delta[i]
        # P3 — erosion by excess over the endogenous threshold
        excess = max(xi[i] - theta[i - 1], 0.0)
        excess_acc[i] = excess_acc[i - 1] + excess
        # P4 — bounded recovery; note: nothing here ever modifies xi
        d_lam = -cfg.kappa * excess + cfg.lambda_recovery * (cfg.lambda_eq - lam[i - 1])
        lam[i] = np.clip(lam[i - 1] + d_lam, cfg.lambda_min, cfg.lambda_eq)
        # P3 — threshold strictly increasing in permissivity
        theta[i] = cfg.theta_scale * lam[i]

    m = theta - xi
    g = np.gradient(
        pd.Series(m).rolling(cfg.g_smooth, min_periods=1).mean().to_numpy()
    )

    if sigma_op is None:
        sigma_op = obs > 0
    sigma_op = np.asarray(sigma_op, dtype=bool)

    out = pd.DataFrame(
        {
            "delta": delta,
            "xi": xi,
            "lambda": lam,
            "theta": theta,
            "M": m,
            "G": g,
        }
    )
    # P6 — latent collapse: operational ∧ margin ≥ 0 ∧ margin generation < 0
    out["latent_collapse"] = sigma_op & (m >= 0) & (g < 0) & valid
    out["stratum"] = np.where(valid, stratify(m, g), 1)
    out["valid"] = valid
    return out


def stratify(m: np.ndarray, g: np.ndarray) -> np.ndarray:
    """Regime stratification S₁–S₄ on the (M, G) plane (AS-1 §6).

    S₁ viable   : M > 0, G ≥ 0   — margin held or growing
    S₂ tension  : M > 0, G < 0   — margin positive but being consumed
    S₃ critical : M ≤ 0, G ≥ 0   — margin exhausted, recovering
    S₄ collapse : M ≤ 0, G < 0   — margin exhausted and falling
    """
    s = np.ones(len(m), dtype=int)
    s[(m > 0) & (g < 0)] = 2
    s[(m <= 0) & (g >= 0)] = 3
    s[(m <= 0) & (g < 0)] = 4
    return s
