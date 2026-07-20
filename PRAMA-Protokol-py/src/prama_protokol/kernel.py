"""PRAMA Protokol — Reference Kernel (π).

Universal aptadynamic projection:  Ω → Γ(t) = (Δ, Ξ, λ, Θ, M, G).

    Δ(t)  = |ω(t) − ω̂(t)| / (ω̂(t) + 1)      structural decoupling
    Ξ(t)  = ∫ K(t−τ) Δ(τ) dτ                 non-Markovian tension accumulator,
                                              exponential causal kernel
    λ(t)  = historical permissivity: eroded by excess (Ξ−Θ)⁺, bounded
            recovery that NEVER modifies Ξ
    Θ(λ)  = endogenous threshold, strictly increasing in λ
    M(t)  = Θ(λ) − Ξ                          viability margin
    G(t)  = D⁺M (smoothed)                    margin generation power

Latent collapse:  σ_op(t) = 1  ∧  M(t) ≥ 0  ∧  G(t) < 0.

Regime stratification S₁–S₄ on the (M, G) plane.

This module is the universal component of the protocol: it contains no domain
knowledge whatsoever. It never sees raw measurements; it receives the
observable stream ω and its strictly causal expectation ω̂, both produced by
an Observation Interface (see `prama_protokol.interface`). Its identity is
pinned by local golden vectors and cross-certified against the Rust
implementation contained in this repository.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["KernelConfig", "project", "stratify"]


@dataclass
class KernelConfig:
    """Universal kernel parameters, expressed in emitted stream bins.

    A consumer declares its bin scale and freezes the complete configuration
    before evaluation outcomes. The recurrence itself is domain-invariant.
    """

    tau_memory: float = 24 * 14   # bins: memory scale of Ξ
    lambda_eq: float = 1.0        # permissivity equilibrium
    lambda_recovery: float = 0.005  # bounded recovery rate
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
        The dimensionless, normalized observable stream ω(t) (C1, N1).
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
    if obs.size == 0:
        raise ValueError("omega and expected must be non-empty")

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
        # Non-Markovian accumulator (exponential causal kernel).
        xi[i] = a * xi[i - 1] + (1 - a) * delta[i]
        # Erosion by excess over the endogenous threshold.
        excess = max(xi[i] - theta[i - 1], 0.0)
        excess_acc[i] = excess_acc[i - 1] + excess
        # Bounded recovery; nothing here ever modifies xi.
        d_lam = -cfg.kappa * excess + cfg.lambda_recovery * (cfg.lambda_eq - lam[i - 1])
        lam[i] = np.clip(lam[i - 1] + d_lam, cfg.lambda_min, cfg.lambda_eq)
        # Threshold strictly increasing in permissivity.
        theta[i] = cfg.theta_scale * lam[i]

    m = theta - xi
    smoothed_margin = pd.Series(m).rolling(
        cfg.g_smooth, min_periods=1
    ).mean().to_numpy()
    # Strictly causal: G[0] = 0; G[t] = smooth_M[t] - smooth_M[t-1].
    g = np.diff(smoothed_margin, prepend=smoothed_margin[0])

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
    # Latent collapse: operational ∧ margin ≥ 0 ∧ margin generation < 0.
    out["latent_collapse"] = sigma_op & (m >= 0) & (g < 0) & valid
    out["stratum"] = np.where(valid, stratify(m, g), 1)
    out["valid"] = valid
    return out


def stratify(m: np.ndarray, g: np.ndarray) -> np.ndarray:
    """Regime stratification S₁–S₄ on the (M, G) plane (specification §4).

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
