# PRAMA Protokol

**Operational protocol of Aptadynamic Cybernetics: structural viability evaluation from observable behavior alone.**

G.A.C.J. — ORCID: [0009-0009-5649-1359](https://orcid.org/0009-0009-5649-1359)
Part of the **AptadynamiK** program.
Normative specification: **Aptadynamic Cybernetics Specification (AS-1)** — see the [discipline repository](../aptadynamic-cybernetics).

> **Denomination.** The protocol is always referred to as **PRAMA Protokol** in full; the admissible short form is *the Protokol*. The token "PRAMA" is never used in isolation.

---

## What the Protokol does

The Protokol answers one question about any system: **is it sustaining itself, or merely appearing to?**

It projects a domain's observable event stream onto six universal coordinates,

```
                O_D                    π
  Domain 𝒟 ────────► Observables Ω ────────► Γ(t) = (Δ, Ξ, λ, Θ, M, G) ────► Regimes / Alerts
             (domain-specific,        (fixed kernel,
              strictly causal)         identical across domains)
```

and evaluates the single viability condition **Ξ(t) ≤ Θ(λ(t))** — accumulated structural tension against an endogenous, history-contracted threshold. It exposes a state called **latent collapse**: the system is operational, its margin is still positive, and its margin is being consumed (σ_op = 1 ∧ M ≥ 0 ∧ G < 0). This is a structural classification, not a validated early-warning claim.

The projection kernel π never models the phenomenon: no topology, no mechanism, no causal model of the domain enters it. Only the Observation Interface O_D is domain-specific. This separation is not rhetoric; it is an architectural constraint, mechanically auditable, with a defined empirical test (AS-1 §8).

## Components

```
┌─────────────────────────────────────────────────────┐
│                PRAMA Protokol Engine                │
│                                                     │
│  Observation Interface (O_D)   ← the ONLY domain-   │
│    raw measurements → normalized  specific part     │
│    causal observables Ω           (contract C1–C5)  │
│                                                     │
│  Reference Kernel (π)          ← universal, fixed,  │
│    Ω → Γ = (Δ,Ξ,λ,Θ,M,G)         identical across   │
│                                   domains           │
│                                                     │
│  Runtime Engine                ← orchestration:     │
│    ingest → omega → projection    streaming,        │
│    → regimes → alerts             batching, replay  │
│                                                     │
│  Compliance Module             ← verification that  │
│    conformance checks, study      the principles    │
│    discipline, audit records      hold in this      │
│                                   deployment        │
└─────────────────────────────────────────────────────┘
```

## Status

**Kernel v0.2.1 is extracted and equivalence-certified. Empirical incremental value is not validated.**

Arithmetic certification and empirical validation are different claims. Golden
vectors and Python/Rust equivalence certify the kernel implementation; they do
not establish that its projection outperforms simpler methods on real data.

| Study | Current status |
|---|---|
| **BPA G1** | `invalid_for_confirmatory_claim_C3_gate_failed`. The observation interface did not decouple sufficiently in evaluation, so the study establishes neither superiority nor defeat. |
| **NYISO G1** | Honest null under its frozen historical rules; no confirmatory advantage established. |
| **NYISO G2** | Valid preregistered confirmatory negative result. CH-L passed every gate, but the selected B-TRIV baseline outperformed the Protokol (`contrast = -0.049623`, one-sided `p = 1.0`); the frozen program-falsification rule was activated. |

G2 also retained a positive secondary contrast against B-AC1 (`+0.037987`,
Holm `p = 0.007499`). It does not replace the single primary comparison or
change the classification. See
[`G2_RESULT_H5.md`](https://github.com/gacj0901/Aptadynamic-Electrical-Grid/blob/main/G2_RESULT_H5.md).

Historical BPA ratio `16.0` and NYISO ratio `1.90` came from superseded,
exploratory procedures. They remain provenance, not current validation claims.

### Roadmap

1. ~~**Kernel extraction**~~ — complete; π is installable and domain-blind.
2. ~~**Compliance Module**~~ — complete for C2, C3, ρ_I, C4, MEM and N1.
3. ~~**Observation Interface base**~~ — complete.
4. **Empirical program** — retain negative and invalid results without
   re-tuning the universal kernel or rewriting frozen classifications.
5. **New domains** — require independent observation contracts and
   preregistration; equivalence certification alone is never evidence of
   empirical value.

Studies predating AS-1 are classified *exploratory*, per the specification's study discipline.

## How a new domain joins

Writing a domain implementation means writing **one component**: an Observation Interface satisfying the contract of AS-1 §5 —

- **C1 Strict observability** — only externally observable events; no hidden state.
- **C2 Strict causality** — expectations built from the strict past only.
- **C3 Genuine decoupling** — Δ measures deviation from the system's own causally expected behavior, never raw activity.
- **N1 Scale invariance** — dimensionless, normalization-explicit observables (historically AS-1 "C4"; in the deployed domain contract C4 is informational density).
- **C5 No retro-fitting** — kernel parameters fixed across domains; negative results reported as found.

The kernel is never modified. Each domain implementation lives in its own repository (`Aptadynamic-<Domain>`) together with its Validation Study.

## What the Protokol never does

Per AS-1 §7, a conformant deployment does **not** model the phenomenon, does **not** forecast event occurrence, does **not** produce point predictions of collapse time, and does **not** interpret — Γ is a measurement space; domain meaning is reconstructed by the domain expert. Claiming more than this on behalf of the framework is non-conformant communication.

## Authority

| Question | Authority |
|---|---|
| What must this Engine satisfy? | **AS-1** ([discipline repository](../aptadynamic-cybernetics)) |
| Why is it mathematically true? | **Logical–Mathematical Corpus** — DOI: [10.5281/zenodo.20369325](https://doi.org/10.5281/zenodo.20369325) |
| Does it work on real data? | **Validation Studies** (domain repositories) |

## License

Released under the GNU Affero General Public License v3.0 (AGPL-3.0). Commercial licensing, industrial collaborations and academic research partnerships may be available separately.
