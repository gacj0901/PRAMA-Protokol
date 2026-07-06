"""PRAMA Protokol — operational protocol of Aptadynamic Cybernetics.

Structural viability evaluation from observable behavior alone.

    from prama_protokol import project, KernelConfig
    gamma = project(omega, expected)          # Ω → Γ = (Δ, Ξ, λ, Θ, M, G)

Normative specification: Aptadynamic Cybernetics Specification (AS-1).
Formal reference: Logical–Mathematical Corpus, DOI 10.5281/zenodo.20369325.
"""

from .kernel import KernelConfig, project, stratify
from .interface import (
    ObservationInterface,
    CausalConditionalMean,
    causal_conditional_mean,
)
from . import compliance

__version__ = "0.1.0"

__all__ = [
    "KernelConfig",
    "project",
    "stratify",
    "ObservationInterface",
    "CausalConditionalMean",
    "causal_conditional_mean",
    "compliance",
]
