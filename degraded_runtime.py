"""
degraded_runtime.py — Phase 3: Degraded Operation Semantics

Defines and enforces five operational outcomes:
  OK       — safe participation allowed
  DEGRADED — participation allowed with warning lineage
  HOLD     — no action emitted
  REJECT   — contract invalid
  HALT     — system safety stop

Each boundary is explicitly justified below.
"""

from dataclasses import dataclass
from enum import Enum

import config
from models import ClassicalContract


# ---------------------------------------------------------------------------
# Operational outcomes
# ---------------------------------------------------------------------------

class OperationalOutcome(str, Enum):
    OK       = "OK"
    DEGRADED = "DEGRADED"
    HOLD     = "HOLD"
    REJECT   = "REJECT"
    HALT     = "HALT"


# ---------------------------------------------------------------------------
# Operational posture record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OperationalPosture:
    """
    The output of degraded_runtime evaluation.
    This is a POSTURE — it advises the operator, it does NOT execute autonomously.
    """
    outcome:       OperationalOutcome
    trace_id:      str
    confidence:    float
    action_label:  str   # human-readable label
    justification: str   # WHY this boundary was crossed
    emit_action:   bool  # whether downstream action is permitted

    def to_dict(self) -> dict:
        return {
            "outcome":       self.outcome.value,
            "trace_id":      self.trace_id,
            "confidence":    self.confidence,
            "action_label":  self.action_label,
            "justification": self.justification,
            "emit_action":   self.emit_action,
        }


# ---------------------------------------------------------------------------
# Boundary definitions (explicit justification for each)
# ---------------------------------------------------------------------------
#
# OK       confidence >= CONFIDENCE_THRESHOLD (default 0.70)
#          Justification: translation is sufficiently reliable for safe participation.
#          Downstream action: PERMITTED.
#
# DEGRADED CORRUPTION_THRESHOLD <= confidence < CONFIDENCE_THRESHOLD (0.40–0.70)
#          Justification: translation succeeded but signal was weak. Participation
#          is allowed only with explicit lineage warning so downstream consumers
#          can make an informed choice.
#          Downstream action: PERMITTED WITH WARNING LINEAGE.
#
# HOLD     confidence translatable but noise_factor > 0.50 OR uncertainty = DEGRADED class
#          Justification: high environmental noise makes the result unreliable even if
#          technically translated. No action should be emitted until conditions improve.
#          Downstream action: SUPPRESSED.
#
# REJECT   confidence < CORRUPTION_THRESHOLD (default 0.40), OR bit mismatch
#          Justification: contract cannot be formed safely. The translation layer
#          has already raised TranslationError. Contract is invalid.
#          Downstream action: SUPPRESSED. Contract discarded.
#
# HALT     Replay detected, rate limit exceeded, or system integrity violation.
#          Justification: safety stop. Something outside normal bounds occurred.
#          Continuing would risk executing stale or malformed contracts.
#          Downstream action: SUPPRESSED. Operator alert required.
#
# ---------------------------------------------------------------------------

def evaluate(
    contract: ClassicalContract,
    *,
    noise_factor: float = 0.0,
    replay_detected: bool = False,
    rate_limited: bool = False,
) -> OperationalPosture:
    """
    Evaluate a ClassicalContract and return the operational posture.

    Parameters
    ----------
    contract         : The contract from the translation layer.
    noise_factor     : Noise level from the quantum distribution.
    replay_detected  : True if the trace_id was already seen.
    rate_limited     : True if rate limit was exceeded.

    Returns
    -------
    OperationalPosture — advisory, not autonomous.
    """

    # HALT conditions — system safety stops (checked first, highest priority)
    if replay_detected:
        return OperationalPosture(
            outcome=OperationalOutcome.HALT,
            trace_id=contract.trace_id,
            confidence=contract.confidence,
            action_label="HALT:REPLAY_DETECTED",
            justification="Duplicate trace_id: potential replay attack. Safety stop.",
            emit_action=False,
        )

    if rate_limited:
        return OperationalPosture(
            outcome=OperationalOutcome.HALT,
            trace_id=contract.trace_id,
            confidence=contract.confidence,
            action_label="HALT:RATE_LIMIT_EXCEEDED",
            justification="Transmission rate exceeded operational limit. Safety stop.",
            emit_action=False,
        )

    # REJECT — contract status already determined invalid by translation layer
    if contract.transmission_status == "REJECTED":
        return OperationalPosture(
            outcome=OperationalOutcome.REJECT,
            trace_id=contract.trace_id,
            confidence=contract.confidence,
            action_label="REJECT:INVALID_CONTRACT",
            justification=(
                f"Contract rejected by translation layer: confidence={contract.confidence:.4f} "
                f"below corruption floor {config.CORRUPTION_THRESHOLD} or bit mismatch."
            ),
            emit_action=False,
        )

    # HOLD — high noise even if technically translated
    if noise_factor > 0.50 and contract.transmission_status != "OK":
        return OperationalPosture(
            outcome=OperationalOutcome.HOLD,
            trace_id=contract.trace_id,
            confidence=contract.confidence,
            action_label="HOLD:HIGH_NOISE",
            justification=(
                f"noise_factor={noise_factor:.2f} exceeds 0.50 with non-OK status. "
                "Suppressing action until channel conditions improve."
            ),
            emit_action=False,
        )

    # DEGRADED — low confidence but above rejection floor
    if contract.transmission_status == "DEGRADED":
        return OperationalPosture(
            outcome=OperationalOutcome.DEGRADED,
            trace_id=contract.trace_id,
            confidence=contract.confidence,
            action_label=f"DEGRADED:confidence={contract.confidence:.4f}",
            justification=(
                f"Confidence {contract.confidence:.4f} in [{config.CORRUPTION_THRESHOLD}, "
                f"{config.CONFIDENCE_THRESHOLD}). Participation allowed with warning lineage."
            ),
            emit_action=True,
        )

    # OK — nominal path
    return OperationalPosture(
        outcome=OperationalOutcome.OK,
        trace_id=contract.trace_id,
        confidence=contract.confidence,
        action_label=f"OK:{contract.decoded_message}",
        justification=(
            f"Confidence {contract.confidence:.4f} >= threshold {config.CONFIDENCE_THRESHOLD}. "
            "Safe participation allowed."
        ),
        emit_action=True,
    )


# ---------------------------------------------------------------------------
# Entry point — self-demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from models import ClassicalContract
    import uuid

    def _demo_contract(status: str, confidence: float) -> ClassicalContract:
        return ClassicalContract(
            trace_id=str(uuid.uuid4()),
            confidence=confidence,
            decoded_message="NODE_READY",
            transmission_status=status,
            uncertainty_score=round(1.0 - confidence, 4),
            contract_version=config.CONTRACT_VERSION,
        )

    cases = [
        ("OK",       _demo_contract("OK",       0.93), 0.12, False, False),
        ("DEGRADED", _demo_contract("DEGRADED", 0.55), 0.30, False, False),
        ("HOLD",     _demo_contract("DEGRADED", 0.55), 0.75, False, False),
        ("REJECT",   _demo_contract("REJECTED", 0.25), 0.95, False, False),
        ("HALT",     _demo_contract("OK",       0.93), 0.12, True,  False),
    ]

    print("\n=== DEGRADED RUNTIME SEMANTICS ===")
    for label, contract, noise, replay, rate in cases:
        posture = evaluate(contract, noise_factor=noise, replay_detected=replay, rate_limited=rate)
        print(f"  [{label:8s}] outcome={posture.outcome.value:8s}  emit={posture.emit_action}  "
              f"label={posture.action_label}")
        print(f"           justification: {posture.justification}")
