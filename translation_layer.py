"""
Layer 2 - Translation Layer
Converts a QuantumDistribution into a deterministic ClassicalContract.
No raw probabilities leak downstream.
"""

from __future__ import annotations

import uuid
import hashlib
import logging

import config
from logger import get_logger, log_event
from models import QuantumDistribution, ClassicalContract

log = get_logger("qcg.translation")


class TranslationError(Exception):
    """Raised when a ClassicalContract cannot be safely formed."""


def _dominant_bitstring(counts: dict) -> tuple[str, float]:
    total = sum(counts.values())
    dominant = max(counts, key=counts.get)
    return dominant, counts[dominant] / total


def _verify_bits(received_bits: str, original_message: str) -> tuple[str, bool]:
    digest = hashlib.sha256(original_message.encode()).hexdigest()
    expected = f"{int(digest[:2], 16) % 4:02b}"
    match = received_bits == expected
    label = original_message if match else f"CORRUPTED[expected={expected},got={received_bits}]"
    return label, match


def translate(distribution: QuantumDistribution, original_message: str) -> ClassicalContract:
    """
    Translate a QuantumDistribution into a ClassicalContract.
    Raises TranslationError if the contract status is REJECTED.
    """
    dominant_bits, confidence = _dominant_bitstring(distribution.counts)
    uncertainty_score = round(1.0 - confidence, 4)
    decoded_msg, is_match = _verify_bits(dominant_bits, original_message)

    if confidence < config.CORRUPTION_THRESHOLD:
        status = "REJECTED"
    elif not is_match:
        status = "REJECTED"
    elif confidence < config.CONFIDENCE_THRESHOLD:
        status = "DEGRADED"
    else:
        status = "OK"

    trace_id = str(uuid.uuid5(
        uuid.NAMESPACE_DNS,
        f"{original_message}:{distribution.seed}:{dominant_bits}",
    ))

    contract = ClassicalContract(
        trace_id=trace_id,
        confidence=round(confidence, 4),
        decoded_message=decoded_msg,
        transmission_status=status,
        uncertainty_score=uncertainty_score,
        contract_version=config.CONTRACT_VERSION,
    )

    log_event(log, logging.WARNING if status == "REJECTED" else logging.INFO, "translation_complete", ctx={
        "trace_id": trace_id,
        "dominant_bits": dominant_bits,
        "confidence": round(confidence, 4),
        "status": status,
        "decoded_msg": decoded_msg,
    })

    if status == "REJECTED":
        raise TranslationError(
            f"Contract REJECTED - confidence={confidence:.4f}, decoded='{decoded_msg}'"
        )

    return contract
