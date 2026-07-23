# PRAMA Protokol — Universal Kernel Contract

**Status:** normative for version `0.3.0`.

This document defines the complete software contract of the universal kernel.
No external repository, domain implementation or empirical study is required
to interpret it.

## 1. Scope

PRAMA Protokol maps a normalized observable stream and its strictly causal
expectation to a structural state trajectory. It does not ingest raw records,
construct outcomes, encode topology or contain domain policy.

Dependency is one-way: an implementation supplies an Observation Interface
and calls the kernel. The kernel never imports or requires an implementation.
Data, labels, empirical gates and conclusions remain outside the universal
state recurrence.

The normative API is `KernelV3` / `project_v3` in Python and the `v3` module in
Rust. The previous projection API remains available as a compatibility
surface and is still covered by its frozen regression vectors.

## 2. Inputs and validity

For source rows `k = 0, …, n−1`, the kernel receives:

- `omega[k]`: dimensionless normalized observable `ω_k`;
- `expected[k]`: strictly causal expectation `ω̂_k`;
- `u_lambda[k]`: optional non-negative capacity input, default `0`;
- `sigma_op[k]`: optional Boolean operational indicator, default `omega > 0`;
- an explicit `KernelConfigV3`.

Leading `expected=NaN` rows are excluded before state initialization and emit
no state. After the first emitted state, a missing expectation fails closed as
`internal_missing_after_start`. Infinite values, negative expectations,
negative or non-finite capacity input, shape mismatches and non-Boolean
operational indicators fail before mutating state.

If all source rows are warm-up, batch projection fails with `no_valid_rows`.
An internal gap is never converted into `Δ=0`, because that would simulate
relaxation and alter memory.

## 3. Configuration

All temporal parameters are expressed in emitted stream bins.

| Parameter | Default | Role |
|---|---:|---|
| `h` | `1.0` | state-step size |
| `tau` | `336.0` | causal retention scale |
| `theta_scale` | `2.0` | endogenous-threshold scale |
| `lambda_0` | `1.0` | initial capacity |
| `lambda_min` | `0.1` | capacity floor |
| `lambda_max` | `1.0` | capacity ceiling |
| `kappa_v3` | `9.957514604354753e-7` | accumulated-debt coupling |
| `g_smooth` | `24` | trailing margin window |
| `delta_ref` | `1.0` | discrepancy reference |

The causal retention is derived, never independently tuned:

```text
r = exp(−h / tau).
```

The full configuration and bin scale must be declared before evaluation.

## 4. State recurrence

Initial state:

```text
Ξ_0 = 0
A_0 = 0
λ_0 = lambda_0
Θ_0 = theta_scale · λ_0.
```

Each valid input `k` produces state `k+1`:

```text
Δ_k       = |ω_k − ω̂_k| / (ω̂_k + 1)
Δ̃_k      = Δ_k / delta_ref
e_k       = max(Ξ_k − Θ_k, 0)
A_{k+1}   = A_k + h e_k

λ_raw,k+1 = λ_k − kappa_v3 h A_{k+1} + h u_lambda,k
λ_{k+1}   = clip(λ_raw,k+1, lambda_min, lambda_max)
Θ_{k+1}   = theta_scale · λ_{k+1}

Ξ_{k+1}   = r Ξ_k + (1−r) Δ̃_k
M_{k+1}   = Θ_{k+1} − Ξ_{k+1}.
```

`A` is monotone accumulated excess debt. Capacity input acts through
`u_lambda`; it does not erase `A` or overwrite `Ξ`. The clip impulse is

```text
π_{k+1} = λ_{k+1} − λ_raw,k+1.
```

## 5. Causal margin trend

Let `W = g_smooth` and `n` be the number of emitted rows after inserting the
current margin. `smooth_M` is the trailing arithmetic mean over
`W_n = min(n,W)` margins.

Between rebuilds, the ring is updated by subtracting the outgoing value and
adding the incoming value. To prevent unbounded cancellation drift, the sum is
rebuilt whenever `n mod W = 0`, including the first full window. Rebuilding
traverses the logical window from oldest to newest and accumulates from `0.0`
using ordinary binary64 addition.

Batch and streaming execution use the same calendar and order:

```text
G_1 = 0
G_n = smooth_M,n − smooth_M,n−1,    n > 1.
```

Warm-up is defined on emitted states, not excluded source timestamps.

## 6. Outputs

Every emitted row contains:

```text
delta, delta_tilde, e, xi, A, lambda, theta, M, G,
u_lambda, sigma_op, valid, input_index, state_index.
```

`input_index` counts emitted inputs from zero and
`state_index=input_index+1`. All emitted rows have `valid=true`; invalid
internal rows fail closed rather than entering the trajectory.

The kernel emits state coordinates, not a verdict. Classification, scoring,
alerts and interventions require separate declared contracts.

## 7. Numerical audit

`NumericAuditV3` exposes read-only state for independent verification:

- emitted-row and periodic-rebuild counts;
- ring length, ring sum and smoothed margin;
- accumulated `ΣA`, `Σu_lambda` and `Σπ`;
- step and cumulative capacity-ledger residuals.

The protected identities are

```text
r_k = λ_k − λ_{k−1} + kappa_v3 h A_k − h u_k − π_k = 0

R_T = (λ_T−λ_0)
      + kappa_v3 h ΣA_k
      − h Σu_k
      − Σπ_k = 0.
```

Certification uses independent binary64 error budgets for the ring and the
capacity ledger. A coupling term may be certified only when its accumulated
scale is distinguishable from the declared floating-point tolerance.

## 8. Observation Interface obligations

The implementation owns the mapping from raw measurements to `omega`,
`expected`, `u_lambda` and `sigma_op`. It must establish:

- strict observability at emission;
- a strictly causal expectation;
- dimensionless, explicit normalization;
- genuine discrepancy rather than rescaled raw activity;
- sufficient temporal support relative to `tau`;
- frozen configuration and gate thresholds;
- an identified observation epoch;
- non-circular outcomes for empirical claims.

The normative `prama_protokol.compliance` module is bound to
`KernelConfigV3`, `project_v3` and `GammaV3`; every record identifies that API
and the `prama.compliance.v3` schema. The separately named
`compliance_legacy` module covers only the frozen compatibility projection.
Checks without thresholds are informational, never implicit passes.

## 9. Certification and change control

The Python implementation is the executable reference. Certification requires
independent golden vectors, Python and Rust tests, batch/streaming identity,
cross-language equivalence, a long adversarial sequence and mutation tests for
the protected debt coupling and periodic ring rebuild.

Arithmetic equivalence certifies implementation identity only. Any recurrence,
alignment or output-semantics change requires a new version, an append-only
anomaly entry, new vectors and joint recertification.

## 10. Claim boundary

PRAMA Protokol does not, by itself, forecast an event, attribute a cause,
estimate a probability or time to failure, define an intervention, validate an
Observation Interface or establish empirical usefulness.

This repository intentionally contains no domain adapters, datasets, outcome
labels, topological models, dashboards or implementation-specific conclusions.
