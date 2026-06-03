"""
lineage.py — Phase 4: Trace + Lineage Semantics

Every contract must expose its full provenance chain.
No hidden state. Full reconstruction from final contract.

ContractLineage fields (mandatory):
  trace_id
  producer_type
  algorithm_family
  translation_version
  confidence_generation_method
  uncertainty_class
  contract_version
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import config
from models import QuantumDistribution, ClassicalContract
from quantum_uncertainty import UncertaintyEnvelope, classify


# ---------------------------------------------------------------------------
# ContractLineage
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContractLineage:
    """
    Full provenance record for a contract.
    Attach to every ClassicalContract before it leaves the gateway.
    """
    trace_id:                    str
    producer_type:               str   # QUANTUM | CLASSICAL | HYBRID
    algorithm_family:            str   # e.g. "superdense_coding", "gradient_descent"
    translation_version:         str   # config.CONTRACT_VERSION
    confidence_generation_method: str  # e.g. "dominant_bitstring_ratio"
    uncertainty_class:           str   # UncertaintyClass value
    contract_version:            str
    noise_factor:                float
    shots:                       int
    seed:                        int
    timestamp:                   str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def reconstruct(cls, lineage_dict: dict) -> "ContractLineage":
        """Reconstruct a ContractLineage from its dict representation."""
        return cls(**lineage_dict)


# ---------------------------------------------------------------------------
# Builder — attaches lineage to a quantum contract
# ---------------------------------------------------------------------------

def build_lineage(
    contract: ClassicalContract,
    distribution: QuantumDistribution,
    envelope: UncertaintyEnvelope,
) -> ContractLineage:
    """
    Build a ContractLineage from the full pipeline context.

    Parameters
    ----------
    contract     : The final ClassicalContract from translation_layer.
    distribution : The QuantumDistribution that produced it.
    envelope     : The UncertaintyEnvelope classifying the distribution.

    Returns
    -------
    ContractLineage — immutable provenance record.
    """
    return ContractLineage(
        trace_id=contract.trace_id,
        producer_type="QUANTUM",
        algorithm_family="superdense_coding",
        translation_version=config.CONTRACT_VERSION,
        confidence_generation_method="dominant_bitstring_ratio",
        uncertainty_class=envelope.uncertainty_class.value,
        contract_version=contract.contract_version,
        noise_factor=distribution.noise_factor,
        shots=distribution.shots,
        seed=distribution.seed,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Lineage-aware pipeline helper
# ---------------------------------------------------------------------------

def run_with_lineage(
    message: str,
    noise: float,
    mode: str,
    seed: int = config.DEFAULT_SEED,
) -> tuple[ClassicalContract, ContractLineage, UncertaintyEnvelope]:
    """
    Run the full quantum pipeline and return:
      (contract, lineage, uncertainty_envelope)

    All three are required to prove no hidden state.
    """
    from models import TransmissionRequest
    from quantum_producer import run_quantum_producer
    from translation_layer import translate

    request      = TransmissionRequest(message=message, noise=noise, mode=mode)
    distribution = run_quantum_producer(request, seed=seed)
    envelope     = classify(distribution)
    contract     = translate(distribution, message)
    lineage      = build_lineage(contract, distribution, envelope)

    return contract, lineage, envelope


# ---------------------------------------------------------------------------
# Entry point — lineage reconstruction demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("\n=== LINEAGE RECONSTRUCTION DEMO ===")
    contract, lineage, envelope = run_with_lineage("NODE_READY", noise=0.12, mode="entangled")

    print("\n  CONTRACT:")
    print(f"    trace_id          : {contract.trace_id}")
    print(f"    confidence        : {contract.confidence}")
    print(f"    transmission_status: {contract.transmission_status}")

    print("\n  LINEAGE:")
    for k, v in lineage.to_dict().items():
        print(f"    {k:34s}: {v}")

    print("\n  UNCERTAINTY ENVELOPE:")
    for k, v in envelope.to_dict().items():
        print(f"    {k:34s}: {v}")

    # Reconstruction proof
    reconstructed = ContractLineage.reconstruct(lineage.to_dict())
    print(f"\n  RECONSTRUCTION MATCH: {reconstructed == lineage}")
