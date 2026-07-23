# PRAMA Protokol — Python reference

The Python package is the executable reference for the universal projection
defined in [`../SPECIFICATION.md`](../SPECIFICATION.md). It is domain-blind and
self-contained: installation, execution and verification require no consumer
repository.

## Package boundary

The package accepts normalized arrays. It does not ingest raw domain data,
construct labels, know topology or import an implementation that consumes it.

```text
consumer-owned interface                   this package
raw measurements ──> (omega, expected, u_lambda, sigma_op) ──> Γv3
```

Dependency direction is consumer → `prama-protokol`. Reverse dependencies are
non-conformant.

## Contents

```text
src/prama_protokol/
├── kernel_v3.py    current batch/streaming state machine and numeric ledger
├── kernel.py       compatibility projection preserved by frozen vectors
├── interface.py          Observation Interface base and causal expectation builder
├── compliance.py         normative KernelV3 mechanical diagnostics
└── compliance_legacy.py  explicit compatibility diagnostics for kernel.py

tests/
├── test_kernel_v3.py    current recurrence, fail-closed and mutation tests
├── test_kernel.py       compatibility structural invariants
├── test_compliance.py   contract checks and fail-closed behavior
└── test_equivalence.py  exact golden-vector identity
```

The package emits

```text
delta, delta_tilde, e, xi, A, lambda, theta, M, G,
u_lambda, sigma_op, valid, input_index, state_index
```

with the recurrence, warm-up semantics and claim boundary fixed by the local
specification.

## Installation and verification

```bash
python -m pip install -e .
python -m pytest -q
```

Minimal use:

```python
import numpy as np
from prama_protokol import KernelConfigV3, project_v3

omega = np.array([0.8, 1.0, 1.4, 0.9])
expected = np.array([np.nan, 0.8, 0.9, 1.0])

gamma = project_v3(omega, expected, KernelConfigV3())
print(gamma.xi, gamma.lambda_, gamma.M, gamma.G)
```

## Observation Interface

Consumers may implement `ObservationInterface` or directly construct arrays.
The bundled `CausalConditionalMean` is a domain-free helper for categorical
contexts:

```python
from prama_protokol.interface import causal_conditional_mean

expected = causal_conditional_mean(
    values=omega,
    context=context_ids,
    min_context_count=10,
    min_global_count=720,
)
```

At index `t`, the expectation uses only indices `< t`. Leading unsupported
positions are `NaN` and emit no state. A missing value after activation fails
closed without mutating the streaming state.

## Compliance

`prama_protokol.compliance` is bound exclusively to `KernelV3/project_v3` and
emits `schema_version = prama.compliance.v3`. It provides mechanical checks for:

- C2 truncation causality;
- C3 anti-degeneration;
- inductive-ratio diagnostics;
- C4 informational density;
- memory support;
- N1 scale invariance.

The frozen pre-v3 checks remain available only through the explicitly named
`prama_protokol.compliance_legacy` module and do not certify `GammaV3`.

Thresholds omitted by the consumer are reported as informational. They do not
become implicit passes. Observable provenance, non-circular outcomes and
empirical claims remain consumer responsibilities.

## Certification

[`EQUIVALENCE.md`](EQUIVALENCE.md) records the golden-vector identity contract.
The Rust implementation is certified from within the same repository; its
record is [`../PRAMA-Protokol-rs/EQUIVALENCE-RS.md`](../PRAMA-Protokol-rs/EQUIVALENCE-RS.md).

Arithmetic identity is not empirical validation. A consumer must establish
usefulness prospectively under its own observation and outcome contracts.

The complete public recertification is re-runnable from the repository root:

```bash
python scripts/certify_v0_3_0.py
```

## License

AGPL-3.0-only.
