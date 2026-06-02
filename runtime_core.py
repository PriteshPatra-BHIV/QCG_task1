"""
runtime_core.py — Phase 3: Blind Runtime Core

Processes ANY ComputationExecutionContract through an identical code path.
The core NEVER inspects producer_type for branching logic — that field is
metadata for observability and audit only.

This is the key proof surface: quantum and classical contracts both traverse
the exact same execute() method without any producer-aware conditional.
"""

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import config
from logger import get_logger, log_event
from execution_contract import (
    ComputationExecutionContract,
    ContractValidationError,
    validate_contract,
)

log = get_logger("qcg.runtime")


# ---------------------------------------------------------------------------
# Execution result — output of the blind core
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionResult:
    """
    Deterministic result produced by RuntimeCore.execute().

    Fields
    ------
    contract_trace_id   : The input contract's trace_id (passthrough).
    producer_type       : Passthrough metadata — NOT used for branching.
    ack                 : Deterministic acknowledgement string.
    confidence          : The confidence from the input contract.
    execution_timestamp : ISO-8601 time of execution.
    runtime_hash        : SHA-256 hash of the runtime path taken.
    """
    contract_trace_id:  str
    producer_type:      str
    ack:                str
    confidence:         float
    execution_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    runtime_hash:       str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Runtime core
# ---------------------------------------------------------------------------

class RuntimeCore:
    """
    Producer-agnostic execution engine.

    The execute() method processes every ComputationExecutionContract through
    the identical code path.  It validates the contract schema, applies
    confidence thresholds, produces a deterministic ACK, and records an
    execution trace hash — all without inspecting producer_type.
    """

    def __init__(self):
        self._replay_registry: dict[str, str] = {}
        self._registry_lock = threading.Lock()

    # -- public interface ---------------------------------------------------

    def execute(self, contract: ComputationExecutionContract) -> ExecutionResult:
        """
        Execute a contract through the blind core.

        Returns an ExecutionResult with a deterministic ACK.
        Never raises — all failures are captured in the ACK string.
        """
        # Step 1 — validate contract schema (producer-agnostic)
        try:
            validate_contract(contract)
        except ContractValidationError as exc:
            return self._halt(contract, f"HALT:INVALID_CONTRACT:{exc}")

        # Step 2 — replay guard (producer-agnostic)
        with self._registry_lock:
            if contract.trace_id in self._replay_registry:
                log_event(log, logging.WARNING, "runtime_replay_detected", ctx={
                    "trace_id": contract.trace_id,
                })
                return self._halt(contract, "HALT:REPLAY_DETECTED")
            self._replay_registry[contract.trace_id] = contract.payload_hash

        # Step 3 — confidence thresholds (producer-agnostic)
        if contract.confidence < config.CORRUPTION_THRESHOLD:
            ack = f"HALT:LOW_CONFIDENCE:{contract.confidence:.4f}"
            log_event(log, logging.WARNING, "runtime_low_confidence", ctx={
                "trace_id": contract.trace_id,
                "confidence": contract.confidence,
            })
            return self._result(contract, ack)

        if contract.confidence < config.CONFIDENCE_THRESHOLD:
            ack = f"ACK:DEGRADED:confidence={contract.confidence:.4f}"
        else:
            ack = "ACK:OK"

        log_event(log, logging.INFO, "runtime_execute_complete", ctx={
            "trace_id": contract.trace_id,
            "ack": ack,
            "confidence": contract.confidence,
        })

        return self._result(contract, ack)

    def reset_replay_registry(self):
        """Clear the replay registry (for testing)."""
        with self._registry_lock:
            self._replay_registry.clear()

    # -- internal helpers ---------------------------------------------------

    def _result(
        self,
        contract: ComputationExecutionContract,
        ack: str,
    ) -> ExecutionResult:
        """Build an ExecutionResult with a runtime hash."""
        # The runtime hash captures the exact path: contract hash + ack
        path_seed = json.dumps({
            "payload_hash": contract.payload_hash,
            "confidence":   contract.confidence,
            "ack":          ack,
        }, sort_keys=True)
        runtime_hash = hashlib.sha256(path_seed.encode()).hexdigest()

        return ExecutionResult(
            contract_trace_id=contract.trace_id,
            producer_type=contract.producer_type,
            ack=ack,
            confidence=contract.confidence,
            runtime_hash=runtime_hash,
        )

    def _halt(
        self,
        contract: ComputationExecutionContract,
        ack: str,
    ) -> ExecutionResult:
        """Convenience for HALT results."""
        log_event(log, logging.ERROR, "runtime_halt", ctx={
            "trace_id": contract.trace_id,
            "ack": ack,
        })
        return self._result(contract, ack)
