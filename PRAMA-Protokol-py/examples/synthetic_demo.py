"""PRAMA Protokol — synthetic demonstration of latent-collapse detection.

Run:
    python examples/synthetic_demo.py        (requires: pip install -e .)

The scenario
------------
A quiet system produces rare events (~2/day) for one "year". Midway through
the two-year record, something silent changes INSIDE it: its failures begin
to beget failures — each event now seeds follow-on events with a branching
ratio that creeps from 0.25 toward 0.90 over six months (a slow drift toward
criticality). Nothing external announces this. In the first weeks after
onset, daily volume (~2.6/day vs 1.84 before) is statistically unremarkable.

A volume monitor sees a normal system for months.

The Protokol reads the structure instead: decoupling Δ accumulates into Ξ,
historical permissivity λ erodes while recovery never rewrites Ξ, the
endogenous threshold Θ contracts, the margin M is consumed while operation
continues (the latent-collapse flag),
and finally the regime degrades S₁ → S₂ → S₃/S₄.

Everything below the interface section is universal: the kernel receives two
bare arrays and knows nothing about "hours", "events", or this story.
This constructed trajectory demonstrates API semantics; it is not empirical
validation or an operational early-warning claim.
"""

from __future__ import annotations

import numpy as np

from prama_protokol import KernelConfig, project
from prama_protokol.interface import causal_conditional_mean
from prama_protokol import compliance

# ----------------------------------------------------------------------
# 1. A synthetic domain (this part plays the role of the real world)
# ----------------------------------------------------------------------
rng = np.random.default_rng(2026)
N = 24 * 730                       # two years of hourly bins
onset = N // 2                     # midway, internal fragility begins
hour = np.arange(N) % 24

mu = 0.05                          # exogenous background rate (events/hour)
decay = np.exp(-1 / 6)             # follow-on pressure dissipates over ~6 h
branching = np.where(
    np.arange(N) < onset,
    0.25,                                                  # healthy: subcritical
    np.minimum(0.25 + 0.65 * (np.arange(N) - onset) / (24 * 180), 0.90),
)                                                          # silent drift → near-critical

raw = np.zeros(N)
excitation = 0.0
for i in range(N):                 # self-exciting event process (Hawkes-like)
    raw[i] = rng.poisson(mu + excitation)
    excitation = decay * excitation + branching[i] * raw[i] / 6.0

print(f"events/day before onset      : {raw[24*60:onset].mean()*24:5.2f}")
print(f"events/day, 1st month after  : {raw[onset:onset+24*30].mean()*24:5.2f}")
print("→ in the alert window, raw volume is statistically unremarkable.\n")

# ----------------------------------------------------------------------
# 2. Observation Interface O_D (consumer-owned; specification §6)
# ----------------------------------------------------------------------
def normalize(x: np.ndarray) -> np.ndarray:
    """N1 — explicit, strictly causal normalization by the running mean."""
    cm = np.cumsum(x) / (np.arange(len(x)) + 1)
    return x / np.maximum(cm, 1e-12)

def expectation(om: np.ndarray) -> np.ndarray:
    """C2/C3 — strictly causal conditional expectation (hour-of-day context)."""
    return causal_conditional_mean(om, hour[: len(om)], 10, 24 * 30)

omega = normalize(raw)
omega_hat = expectation(omega)

# ----------------------------------------------------------------------
# 3. Compliance record before interpreting any output
# ----------------------------------------------------------------------
record = compliance.run_all(raw, normalize, expectation)
for key in ("C2", "C3", "RHO_I", "C4", "MEM", "N1"):
    p = record[key]["passed"]
    status = "INFO" if p is None else ("PASS" if p else "FAIL")
    print(f"[{status}] {record[key]['check']}: {record[key]['detail']}")
print()

# ----------------------------------------------------------------------
# 4. Universal projection π : Ω → Γ (domain-blind from here on)
# ----------------------------------------------------------------------
gamma = project(omega, omega_hat, KernelConfig())

def summarize(label: str, sl: slice) -> None:
    g = gamma.iloc[sl]
    strata = g["stratum"].value_counts(normalize=True).sort_index()
    strata_txt = "  ".join(f"S{int(k)}:{v:5.1%}" for k, v in strata.items())
    print(
        f"{label:26s} ⟨M⟩ {g['M'].mean():+6.3f}   ⟨λ⟩ {g['lambda'].mean():.2f}   "
        f"⟨Ξ⟩ {g['xi'].mean():.2f}   {strata_txt}"
    )

warm = 24 * 60                     # skip interface warm-up
print("Period                     Protokol reading")
print("-" * 88)
summarize("healthy year", slice(warm, onset))
summarize("year after silent onset", slice(onset, N))
summarize("final quarter", slice(N - 24 * 90, N))

idx = np.arange(N)
lc = idx[(idx >= onset) & gamma["latent_collapse"].to_numpy()]
s34 = idx[(idx >= onset) & (gamma["stratum"].to_numpy() >= 3)]

print()
if len(lc):
    print(f"First latent-collapse flag  : day {(lc[0]-onset)/24:6.1f} after the silent onset")
if len(s34):
    print(f"Margin exhaustion (S₃/S₄)   : day {(s34[0]-onset)/24:6.1f} after the silent onset")
if len(lc) and len(s34):
    print(
        f"\nSynthetic separation: {(s34[0]-lc[0])/24:.0f} days between the first flag "
        "and margin exhaustion —"
    )
    print("months in which the system still LOOKED normal, and was not.")
    print("Note: λ ends at its floor. Under the bounded-recovery recurrence, tolerance")
    print("consumed on the way down is not recovered by quiet periods alone.")
