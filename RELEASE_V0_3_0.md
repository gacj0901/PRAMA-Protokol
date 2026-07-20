# PRAMA Protokol v0.3.0 — Release Register

**Status:** numerically certified.

**Date:** 2026-07-20.

**Outcome access:** `false`.

## Functional scope

Version 0.3.0 introduces the current universal state machine:

- explicit input-to-state timing;
- leading warm-up exclusion and fail-closed internal gaps;
- normalized discrepancy `Δ̃`;
- monotone accumulated excess debt `A`;
- bounded capacity `λ` with declared non-negative input `u_lambda`;
- endogenous threshold and viability margin;
- causal trailing-margin difference `G`;
- deterministic periodic logical-order ring rebuilds;
- read-only ring and capacity ledgers.

The compatibility projection remains available and retains its frozen
regression vectors.

## Certification result

The public runner [`scripts/certify_v0_3_0.py`](scripts/certify_v0_3_0.py)
completed successfully:

| Check | Result |
|---|---:|
| Python tests | 50 passed |
| Rust tests | 11 passed |
| Cross-language vectors | 13 passed |
| Long adversarial trajectory | 66,000 emitted rows |
| Periodic ring rebuilds | 2,750 |
| Maximum backward-difference residual | 0.0 |
| Maximum ring residual/tolerance | 0.014073748834823777 |
| Capacity-coupling separation ratio | 1421504639.6403677 |
| Omitted-coupling mutation | detected |
| Disabled-rebuild mutation | detected |

Machine-readable result:
[`results/v0_3_0_numeric_recertification.json`](results/v0_3_0_numeric_recertification.json)

Artifact SHA-256:

```text
1BE41F35EF4C3AB5230C950DFA6C0BBA1C4081EEF6A35801DDBF5524AA7AD7BF
```

The artifact embeds the versions, environment, suite results, kernel and test
hashes, golden-vector hashes, numerical maxima, mutation results and the
normative specification hash.

## Claim boundary

This release certifies arithmetic, temporal alignment, fail-closed behavior
and cross-language equivalence. It does not establish predictive or empirical
value for any implementation.
