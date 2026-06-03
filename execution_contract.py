"""
execution_contract.py — Phase 1: Generic Computation Contract

Defines the ComputationExecutionContract that wraps ANY producer's output
into a uniform envelope.  The core runtime processes this contract without
ever inspecting producer_type for branching logic.

Supported producers: CLASSICAL | QUANTUM | HYBRID
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import config


# ---------------------------------------------------------------------------
# Producer type enumeration
# ---------------------------------------------------------------------------

class ProducerType(str, Enum):
    """Canonical set of producer origins."""
    CLASSICAL = "CLASSICAL"
    QUANTUM   = "QUANTUM"
    HYBRID    = "HYBRID"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ContractValidationError(Exception):
    """Raised when a ComputationExecutionContract fails validation."""


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

def _canonical_hash(payload: dict) -> str:
    """Deterministic SHA-256 of a JSON-serialisable payload."""
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class ComputationExecutionContract:
    """
    Uniform envelope for any producer's output.

    Fields
    ------
    producer_type        : CLASSICAL | QUANTUM | HYBRID
    payload              : Opaque dict — core MUST NOT inspect internals.
    confidence           : float in [0.0, 1.0]
    trace_id             : Deterministic UUID-5 string.
    contract_version     : Semantic version (e.g. "2.0.0").
    execution_constraints: Producer-specific metadata (opaque to core).
    timestamp            : ISO-8601 creation time.
    payload_hash         : SHA-256 of canonical payload for integrity.
    """

    producer_type:         str
    payload:               dict
    confidence:            float
    trace_id:              str
    contract_version:      str
    execution_constraints: dict  = field(default_factory=dict)
    timestamp:             str   = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload_hash:          str   = ""

    def __post_init__(self):
        # Compute payload_hash if not provided
        if not self.payload_hash:
            object.__setattr__(self, "payload_hash", _canonical_hash(self.payload))

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _parse_semver(version: str) -> tuple[int, ...]:
    """Parse 'X.Y.Z' → (X, Y, Z).  Raises on bad format."""
    try:
        parts = tuple(int(p) for p in version.split("."))
        if len(parts) != 3:
            raise ValueError
        return parts
    except (ValueError, AttributeError):
        raise ContractValidationError(
            f"Invalid semantic version '{version}'. Expected format X.Y.Z"
        )


def validate_contract(
    contract: ComputationExecutionContract,
    *,
    allowed_producers: set[str] | None = None,
    minimum_version:   str | None      = None,
) -> None:
    """
    Validate a ComputationExecutionContract.

    Raises ContractValidationError on any violation.
    """

    allowed = allowed_producers or config.ALLOWED_PRODUCER_TYPES

    # --- producer_type ---
    if contract.producer_type not in allowed:
        raise ContractValidationError(
            f"Unauthorized producer type '{contract.producer_type}'. "
            f"Allowed: {sorted(allowed)}"
        )

    # --- payload ---
    if not isinstance(contract.payload, dict) or not contract.payload:
        raise ContractValidationError("payload must be a non-empty dict.")

    # --- confidence ---
    if not (0.0 <= contract.confidence <= 1.0):
        raise ContractValidationError(
            f"confidence must be in [0.0, 1.0], got {contract.confidence}"
        )

    # --- trace_id ---
    if not contract.trace_id or not isinstance(contract.trace_id, str):
        raise ContractValidationError("trace_id must be a non-empty string.")

    # --- contract_version ---
    ver = _parse_semver(contract.contract_version)
    min_ver_str = minimum_version or config.MINIMUM_CONTRACT_VERSION
    min_ver = _parse_semver(min_ver_str)
    if ver < min_ver:
        raise ContractValidationError(
            f"Contract version {contract.contract_version} is below "
            f"minimum {min_ver_str}. Contract downgrade not allowed."
        )

    # --- payload_hash integrity ---
    expected_hash = _canonical_hash(contract.payload)
    if contract.payload_hash != expected_hash:
        raise ContractValidationError(
            f"payload_hash mismatch. Expected {expected_hash}, "
            f"got {contract.payload_hash}"
        )

    # --- timestamp ---
    if not contract.timestamp:
        raise ContractValidationError("timestamp must be a non-empty string.")
