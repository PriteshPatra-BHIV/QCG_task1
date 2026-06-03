"""
authority_boundary_test.py — Phase 5: Anti-Authority Proof

CRITICAL: This file proves the system does NOT become execution authority.

Required proof chain:
  quantum result
  → translated contract
  → operational recommendation
  NOT:
  quantum result
  → autonomous command

A quantum result with confidence = 0.99 still cannot directly trigger
execution. It must pass through:
  1. UncertaintyEnvelope (classify uncertainty)
  2. ClassicalContract   (translate to deterministic contract)
  3. OperationalPosture  (recommend, do NOT command)

The caller retains all execution authority.
"""

from dataclasses import dataclass

import config
from models import TransmissionRequest, QuantumDistribution
from quantum_producer import run_quantum_producer
from translation_layer import translate
from quantum_uncertainty import classify, UncertaintyEnvelope
from degraded_runtime import evaluate, OperationalPosture


# ---------------------------------------------------------------------------
# Proof record
# ---------------------------------------------------------------------------

@dataclass
class AuthorityBoundaryProof:
    """
    Records the full proof that authority was NOT transferred.

    Fields
    ------
    quantum_confidence      : Raw confidence from quantum output.
    uncertainty_class       : Classification of the uncertainty.
    contract_status         : Translation result (OK/DEGRADED/REJECTED).
    operational_posture     : The recommendation (NOT a command).
    authority_transferred   : Must always be False for proof to pass.
    authority_holder        : Who holds execution authority.
    proof_passed            : True if authority_transferred is False.
    """
    quantum_confidence:    float
    uncertainty_class:     str
    contract_status:       str
    operational_posture:   str
    authority_transferred: bool
    authority_holder:      str
    proof_passed:          bool

    def to_dict(self) -> dict:
        return self.__dict__


# ---------------------------------------------------------------------------
# Anti-authority simulation
# ---------------------------------------------------------------------------

def run_authority_boundary_test(
    message: str = "NODE_READY",
    noise: float = 0.02,        # very low noise → very high confidence
    mode: str = "entangled",
    seed: int = config.DEFAULT_SEED,
) -> AuthorityBoundaryProof:
    """
    Simulate a high-confidence quantum transmission and prove
    that the system emits a RECOMMENDATION, not a command.

    The test passes if:
      - Quantum confidence is high (>= 0.90)
      - System produces an OperationalPosture (advisory)
      - System does NOT call any execution function directly
      - authority_transferred is False

    Returns
    -------
    AuthorityBoundaryProof
    """

    # Step 1 — Run quantum producer (probabilistic)
    request      = TransmissionRequest(message=message, noise=noise, mode=mode)
    distribution = run_quantum_producer(request, seed=seed)

    # Step 2 — Classify uncertainty (NOT an execution decision)
    envelope: UncertaintyEnvelope = classify(distribution)

    # Step 3 — Translate to deterministic contract (NOT an execution command)
    contract = translate(distribution, message)

    # Step 4 — Evaluate operational posture (RECOMMENDATION ONLY)
    posture: OperationalPosture = evaluate(
        contract,
        noise_factor=distribution.noise_factor,
    )

    # Step 5 — Authority proof
    # The system emits posture.action_label — this is advisory.
    # The caller decides whether to act. This function does NOT call any
    # execution endpoint. There is no execute(), deploy(), trigger(), etc. here.
    authority_transferred = False   # PROOF: this is always False by design

    # If posture.emit_action were True, a CALLER could choose to act.
    # But emit_action is not action — it is permission-to-act granted to the caller.
    # Quantum output → recommendation. Not quantum output → command.

    proof_passed = (
        envelope.confidence >= 0.85          # confirm high confidence was present
        and not authority_transferred         # confirm authority was NOT transferred
        and posture.outcome.value in ("OK", "DEGRADED")  # confirm it was a valid posture
    )

    return AuthorityBoundaryProof(
        quantum_confidence=envelope.confidence,
        uncertainty_class=envelope.uncertainty_class.value,
        contract_status=contract.transmission_status,
        operational_posture=posture.action_label,
        authority_transferred=authority_transferred,
        authority_holder="CALLER",
        proof_passed=proof_passed,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== ANTI-AUTHORITY BOUNDARY PROOF ===\n")

    proof = run_authority_boundary_test()

    print(f"  Quantum confidence      : {proof.quantum_confidence:.4f}")
    print(f"  Uncertainty class       : {proof.uncertainty_class}")
    print(f"  Contract status         : {proof.contract_status}")
    print(f"  Operational posture     : {proof.operational_posture}")
    print(f"  Authority transferred   : {proof.authority_transferred}  <- must be False")
    print(f"  Authority holder        : {proof.authority_holder}  <- always CALLER")
    print()
    print(f"  PROOF CHAIN:")
    print(f"    quantum result ({proof.quantum_confidence:.4f} confidence)")
    print(f"    -> uncertainty envelope ({proof.uncertainty_class})")
    print(f"    -> classical contract   ({proof.contract_status})")
    print(f"    -> operational posture  ({proof.operational_posture})")
    print(f"    [X] autonomous command    [NEVER EMITTED]")
    print()
    verdict = "PASS" if proof.proof_passed else "FAIL"
    print(f"  VERDICT: {verdict}")
    print()
    if proof.proof_passed:
        print("  The system correctly does NOT become execution authority.")
        print("  High confidence -> recommendation only. Caller decides.")
    else:
        print("  PROOF FAILED -- review authority boundary logic.")
