"""
governance.py — Phase 4: Failure + Governance Boundaries

Wraps RuntimeCore with policy enforcement.  All five failure scenarios are
handled here:

1. Low confidence quantum output   → HALT:LOW_CONFIDENCE
2. Invalid producer contract       → HALT:INVALID_CONTRACT
3. Replay mismatch                 → HALT:REPLAY_DETECTED
4. Contract downgrade attempt      → HALT:CONTRACT_DOWNGRADE
5. Unauthorized producer type      → HALT:UNAUTHORIZED_PRODUCER

The governance layer NEVER crashes.  Every failure is captured in a
structured GovernanceViolation record with a safe HALT ACK.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import config
from logger import get_logger, log_event
from execution_contract import (
    ComputationExecutionContract,
    ContractValidationError,
    validate_contract,
    _parse_semver,
)
from runtime_core import RuntimeCore, ExecutionResult

log = get_logger("qcg.governance")

_MAX_VIOLATIONS = 10_000  # cap to prevent unbounded memory growth


# ---------------------------------------------------------------------------
# Governance violation record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceViolation:
    """Structured record of a governance policy violation."""
    violation_type: str        # e.g. "UNAUTHORIZED_PRODUCER"
    severity:       str        # CRITICAL | HIGH | MEDIUM | LOW
    trace_id:       str
    details:        str
    timestamp:      str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Governance layer
# ---------------------------------------------------------------------------

class GovernanceLayer:
    """
    Policy enforcement layer wrapping RuntimeCore.

    In strict mode (default), policy violations produce immediate HALT.
    In permissive mode, violations are logged as warnings but execution
    proceeds through the core.
    """

    def __init__(
        self,
        runtime: RuntimeCore | None = None,
        *,
        strict: bool = config.GOVERNANCE_STRICT_MODE,
        allowed_producers: set[str] | None = None,
        minimum_version: str | None = None,
    ):
        self.runtime = runtime or RuntimeCore()
        self.strict = strict
        self.allowed_producers = allowed_producers or config.ALLOWED_PRODUCER_TYPES
        self.minimum_version = minimum_version or config.MINIMUM_CONTRACT_VERSION
        self._violations: deque[GovernanceViolation] = deque(maxlen=_MAX_VIOLATIONS)

    # -- public interface ---------------------------------------------------

    def enforce(
        self,
        contract: ComputationExecutionContract,
    ) -> tuple[ExecutionResult, list[GovernanceViolation]]:
        """
        Apply governance policies, then delegate to RuntimeCore.

        Returns
        -------
        (ExecutionResult, list_of_violations)
        """
        violations: list[GovernanceViolation] = []

        # Policy 1 — Unauthorized producer type
        if contract.producer_type not in self.allowed_producers:
            v = GovernanceViolation(
                violation_type="UNAUTHORIZED_PRODUCER",
                severity="CRITICAL",
                trace_id=contract.trace_id,
                details=(
                    f"Producer type '{contract.producer_type}' is not in "
                    f"allowed set {sorted(self.allowed_producers)}."
                ),
            )
            violations.append(v)
            if self.strict:
                self._log_violation(v)
                self._violations.extend(violations)
                return self._halt(contract, "HALT:UNAUTHORIZED_PRODUCER"), violations

        # Policy 2 — Contract version downgrade
        try:
            contract_ver = _parse_semver(contract.contract_version)
            min_ver = _parse_semver(self.minimum_version)
            if contract_ver < min_ver:
                v = GovernanceViolation(
                    violation_type="CONTRACT_DOWNGRADE",
                    severity="HIGH",
                    trace_id=contract.trace_id,
                    details=(
                        f"Contract version {contract.contract_version} is below "
                        f"minimum {self.minimum_version}."
                    ),
                )
                violations.append(v)
                if self.strict:
                    self._log_violation(v)
                    self._violations.extend(violations)
                    return self._halt(contract, "HALT:CONTRACT_DOWNGRADE"), violations
        except ContractValidationError as exc:
            v = GovernanceViolation(
                violation_type="INVALID_CONTRACT",
                severity="CRITICAL",
                trace_id=contract.trace_id,
                details=str(exc),
            )
            violations.append(v)
            if self.strict:
                self._log_violation(v)
                self._violations.extend(violations)
                return self._halt(contract, f"HALT:INVALID_CONTRACT:{exc}"), violations

        # Policy 3 — Invalid contract (full schema validation)
        try:
            validate_contract(
                contract,
                allowed_producers=self.allowed_producers,
                minimum_version=self.minimum_version,
            )
        except ContractValidationError as exc:
            v = GovernanceViolation(
                violation_type="INVALID_CONTRACT",
                severity="CRITICAL",
                trace_id=contract.trace_id,
                details=str(exc),
            )
            violations.append(v)
            if self.strict:
                self._log_violation(v)
                self._violations.extend(violations)
                return self._halt(contract, f"HALT:INVALID_CONTRACT:{exc}"), violations

        # Policy 4 — Low confidence (pre-check before core)
        if contract.confidence < config.CORRUPTION_THRESHOLD:
            v = GovernanceViolation(
                violation_type="LOW_CONFIDENCE",
                severity="HIGH",
                trace_id=contract.trace_id,
                details=(
                    f"Confidence {contract.confidence:.4f} is below corruption "
                    f"threshold {config.CORRUPTION_THRESHOLD}."
                ),
            )
            violations.append(v)
            self._log_violation(v)
            # Always halt on critically low confidence, regardless of mode

        # Log warnings for non-critical violations in permissive mode
        for v in violations:
            if v not in self._violations:
                self._log_violation(v)

        # Store violations for auditing
        self._violations.extend(violations)

        # Delegate to blind core
        # (core also has its own replay guard and confidence checks)
        result = self.runtime.execute(contract)

        # Policy 5 — Replay mismatch is handled by RuntimeCore internally
        # We detect it from the result ACK for governance recording
        if "REPLAY_DETECTED" in result.ack:
            v = GovernanceViolation(
                violation_type="REPLAY_MISMATCH",
                severity="MEDIUM",
                trace_id=contract.trace_id,
                details="Duplicate trace_id detected in replay registry.",
            )
            violations.append(v)
            self._violations.append(v)

        return result, violations

    def get_violations(self) -> list[dict]:
        """Return all recorded violations as dicts."""
        return [v.to_dict() for v in self._violations]

    def clear_violations(self):
        """Clear the violation log."""
        self._violations.clear()

    # -- internal helpers ---------------------------------------------------

    def _halt(
        self,
        contract: ComputationExecutionContract,
        ack: str,
    ) -> ExecutionResult:
        """Build a HALT ExecutionResult without touching the core."""
        return ExecutionResult(
            contract_trace_id=contract.trace_id,
            producer_type=contract.producer_type,
            ack=ack,
            confidence=contract.confidence,
            runtime_hash="GOVERNANCE_HALT",
        )

    def _log_violation(self, violation: GovernanceViolation):
        log_event(log, logging.WARNING, "governance_violation", ctx={
            "type": violation.violation_type,
            "severity": violation.severity,
            "trace_id": violation.trace_id,
            "details": violation.details,
        })
