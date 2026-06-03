"""
quantum_uncertainty.py — Phase 1: Quantum Uncertainty Doctrine

Explicitly models uncertainty classes and wraps every quantum output
in an UncertaintyEnvelope BEFORE it touches the operational contract layer.

CRITICAL SEPARATION:
  Quantum uncertainty ≠ operational failure.
  HIGH_CONFIDENCE noise   → still just uncertainty, not a command.
  UNTRANSLATABLE output   → operational posture = HOLD, not crash.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

import config
from models import QuantumDistribution


# ---------------------------------------------------------------------------
# Uncertainty classes
# ---------------------------------------------------------------------------

class UncertaintyClass(str, Enum):
    HIGH_CONFIDENCE  = "HIGH_CONFIDENCE"   # confidence >= CONFIDENCE_THRESHOLD
    LOW_CONFIDENCE   = "LOW_CONFIDENCE"    # confidence in [CORRUPTION_THRESHOLD, CONFIDENCE_THRESHOLD)
    DEGRADED         = "DEGRADED"          # noise_factor > 0.5, confidence still translatable
    UNTRANSLATABLE   = "UNTRANSLATABLE"    # cannot extract dominant bitstring reliably
    REJECTED         = "REJECTED"          # confidence < CORRUPTION_THRESHOLD


# Recommended operational posture per class — NOT a command, a recommendation.
_POSTURE: dict[UncertaintyClass, str] = {
    UncertaintyClass.HIGH_CONFIDENCE: "PROCEED",
    UncertaintyClass.LOW_CONFIDENCE:  "PROCEED_WITH_CAUTION",
    UncertaintyClass.DEGRADED:        "HOLD",
    UncertaintyClass.UNTRANSLATABLE:  "HOLD",
    UncertaintyClass.REJECTED:        "REJECT",
}

# Human-readable explanation codes
_EXPLANATION: dict[UncertaintyClass, str] = {
    UncertaintyClass.HIGH_CONFIDENCE: "UC-01: confidence above operational threshold",
    UncertaintyClass.LOW_CONFIDENCE:  "UC-02: confidence below threshold but above floor",
    UncertaintyClass.DEGRADED:        "UC-03: high noise detected; translation degraded",
    UncertaintyClass.UNTRANSLATABLE:  "UC-04: quantum distribution too uniform to decode",
    UncertaintyClass.REJECTED:        "UC-05: confidence below rejection floor",
}


# ---------------------------------------------------------------------------
# UncertaintyEnvelope
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UncertaintyEnvelope:
    """
    Wraps a quantum output with explicit uncertainty metadata.

    This is the BOUNDARY object — it separates quantum probabilistic
    behaviour from operational contract certainty downstream.

    Fields
    ------
    uncertainty_class            : One of the five UncertaintyClass values.
    confidence                   : Dominant bitstring probability [0.0, 1.0].
    translation_valid            : True if a contract CAN be formed.
    recommended_operational_posture : Advisory string — NOT an execution command.
    explanation_code             : Short human-readable code.
    noise_factor                 : Noise level from the quantum distribution.
    """
    uncertainty_class:               UncertaintyClass
    confidence:                      float
    translation_valid:               bool
    recommended_operational_posture: str
    explanation_code:                str
    noise_factor:                    float

    def to_dict(self) -> dict:
        return {
            "uncertainty_class":               self.uncertainty_class.value,
            "confidence":                      self.confidence,
            "translation_valid":               self.translation_valid,
            "recommended_operational_posture": self.recommended_operational_posture,
            "explanation_code":                self.explanation_code,
            "noise_factor":                    self.noise_factor,
        }


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

def _dominant_confidence(counts: dict) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return max(counts.values()) / total


def classify(
    distribution: QuantumDistribution,
    translation_result: str | None = None,   # "OK" | "DEGRADED" | "REJECTED" | None
) -> UncertaintyEnvelope:
    """
    Classify a QuantumDistribution into an UncertaintyEnvelope.

    Parameters
    ----------
    distribution       : Raw quantum output from the producer.
    translation_result : Optional result from translation_layer ("OK"|"DEGRADED"|"REJECTED").
                         If None, classification uses confidence + noise only.

    Returns
    -------
    UncertaintyEnvelope — the explicit uncertainty boundary object.

    NOTE: This function deliberately does NOT decide whether to act.
    It only classifies. The operational posture it emits is a RECOMMENDATION.
    """
    confidence   = round(_dominant_confidence(distribution.counts), 4)
    noise_factor = distribution.noise_factor

    # Untranslatable: all bitstrings nearly equal (max < 30% dominance)
    if confidence < 0.30:
        uc = UncertaintyClass.UNTRANSLATABLE
    elif confidence < config.CORRUPTION_THRESHOLD:
        uc = UncertaintyClass.REJECTED
    elif noise_factor > 0.50 and confidence < config.CONFIDENCE_THRESHOLD:
        # High noise AND low confidence → DEGRADED (not just low confidence)
        uc = UncertaintyClass.DEGRADED
    elif confidence < config.CONFIDENCE_THRESHOLD:
        uc = UncertaintyClass.LOW_CONFIDENCE
    else:
        uc = UncertaintyClass.HIGH_CONFIDENCE

    # Override with explicit translation result if provided
    if translation_result == "REJECTED":
        uc = UncertaintyClass.REJECTED
    elif translation_result == "DEGRADED" and uc == UncertaintyClass.HIGH_CONFIDENCE:
        uc = UncertaintyClass.LOW_CONFIDENCE

    translation_valid = uc not in (UncertaintyClass.REJECTED, UncertaintyClass.UNTRANSLATABLE)

    return UncertaintyEnvelope(
        uncertainty_class=uc,
        confidence=confidence,
        translation_valid=translation_valid,
        recommended_operational_posture=_POSTURE[uc],
        explanation_code=_EXPLANATION[uc],
        noise_factor=noise_factor,
    )
