"""
canonical_replay_authority.py — Phase 3: Canonical Replay Service

Single replay authority for QCG. All replay decisions originate here.
No other component may generate replay verdicts.

Responsibilities
----------------
- replay registration
- duplicate detection
- stale detection
- sequence tracking
- replay lineage generation
- persistence

Public API
----------
submit()              — register an artifact; returns ReplayVerdict
lookup()              — retrieve decision for a known artifact_id
verification_report() — full state snapshot for observability
sequence_status()     — current sequence counter + last assigned
lineage()             — ordered list of ReplayLineageRecord for all VALID decisions

Requirements met
----------------
Thread Safe     — inherited from ReplayRegistry (threading.Lock)
Deterministic   — same input always produces same verdict
Restart Safe    — backed by ReplayRegistry's file-persistence
Observable      — verification_report() and lineage() expose full state
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

import config
from replay_registry import ReplayRegistry, RegistryDecision

# Schema version for lineage records produced by this authority
_SCHEMA_VERSION = "1.0.0"
_ORIGIN = "CanonicalReplayAuthority"


# ---------------------------------------------------------------------------
# ReplayLineageRecord — Phase 5 field set, built here for Phase 3 use
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReplayLineageRecord:
    """
    Immutable lineage record for one replay decision.
    Satisfies all Phase 5 required fields.
    """
    replay_id:          str   # UUID-5 of this lineage record
    message_id:         str   # artifact / trace identifier submitted
    sequence_number:    int   # 0 if verdict is not VALID
    decision:           str   # VALID | DUPLICATE | STALE | FUTURE
    decision_timestamp: str   # ISO-8601 UTC
    origin_component:   str   # always "CanonicalReplayAuthority"
    schema_version:     str   # _SCHEMA_VERSION
    trace_reference:    str   # echo of message_id (callers may override)
    parent_reference:   str   # sequence_number - 1, as str; "" if seq <= 1
    verification_hash:  str   # SHA-256 of canonical fields

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# ReplayVerdict — what callers receive from submit()
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReplayVerdict:
    """
    Canonical replay decision returned to every caller.
    Maps the underlying RegistryDecision to the single-authority vocabulary.
    """
    message_id:      str
    sequence_number: int
    status:          str   # VALID | DUPLICATE | STALE | FUTURE
    reason:          str
    lineage_record:  ReplayLineageRecord

    @property
    def is_valid(self) -> bool:
        return self.status == "VALID"


# ---------------------------------------------------------------------------
# CanonicalReplayAuthority
# ---------------------------------------------------------------------------

class CanonicalReplayAuthority:
    """
    The single replay authority for QCG.

    All components that previously made their own replay decisions
    (RuntimeCore, Receiver, QuantumGateway, execution_process) must
    call this class instead and consume the returned ReplayVerdict.
    """

    def __init__(self, registry: ReplayRegistry | None = None):
        # Callers may inject a custom registry (e.g. in-memory for tests).
        # Default: use the global file-backed singleton path from config.
        self._registry = registry or ReplayRegistry()
        # Ordered lineage log — VALID records only, keyed by message_id
        self._lineage: dict[str, ReplayLineageRecord] = {}
        # Replay _all_ decisions (including rejections) for lookup
        self._all_verdicts: dict[str, ReplayVerdict] = {}

    # ------------------------------------------------------------------
    # submit() — primary entry point
    # ------------------------------------------------------------------

    def submit(
        self,
        message_id: str,
        issued_at: float | None = None,
        trace_reference: str | None = None,
    ) -> ReplayVerdict:
        """
        Register an artifact and return a canonical replay verdict.

        Parameters
        ----------
        message_id      : unique identifier for the execution artifact
        issued_at       : Unix timestamp when the artifact was originally issued
        trace_reference : optional caller-supplied reference (defaults to message_id)
        """
        decision: RegistryDecision = self._registry.submit(message_id, issued_at=issued_at)
        record = self._build_lineage_record(decision, trace_reference or message_id)

        verdict = ReplayVerdict(
            message_id=decision.message_id,
            sequence_number=decision.sequence_number,
            status=decision.status,
            reason=decision.reason,
            lineage_record=record,
        )

        # Store for lookup() and lineage()
        self._all_verdicts[message_id] = verdict
        if decision.status == "VALID":
            self._lineage[message_id] = record

        return verdict

    # ------------------------------------------------------------------
    # lookup() — retrieve the last verdict for a known artifact
    # ------------------------------------------------------------------

    def lookup(self, message_id: str) -> ReplayVerdict | None:
        """
        Return the stored verdict for message_id, or None if unknown.
        Does NOT submit — read-only.
        """
        return self._all_verdicts.get(message_id)

    # ------------------------------------------------------------------
    # verification_report() — full observable state snapshot
    # ------------------------------------------------------------------

    def verification_report(self) -> dict:
        """
        Return a complete state snapshot for monitoring and audit.
        No side effects.
        """
        return {
            "authority":        _ORIGIN,
            "schema_version":   _SCHEMA_VERSION,
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "sequence_counter": self._registry.sequence_count,
            "total_submitted":  len(self._all_verdicts),
            "valid_count":      len(self._lineage),
            "rejected_count":   len(self._all_verdicts) - len(self._lineage),
            "persisted_entries":self._registry.entry_count,
        }

    # ------------------------------------------------------------------
    # sequence_status() — current sequence tracking state
    # ------------------------------------------------------------------

    def sequence_status(self) -> dict:
        """
        Return the current sequence counter and the last assigned sequence
        number, for monitoring.
        """
        counter = self._registry.sequence_count
        last_record: ReplayLineageRecord | None = (
            list(self._lineage.values())[-1] if self._lineage else None
        )
        return {
            "sequence_counter":     counter,
            "last_sequence_number": last_record.sequence_number if last_record else 0,
            "last_message_id":      last_record.message_id if last_record else None,
        }

    # ------------------------------------------------------------------
    # lineage() — ordered list of VALID decision records
    # ------------------------------------------------------------------

    def lineage(self) -> list[ReplayLineageRecord]:
        """
        Return all VALID ReplayLineageRecords in sequence order.
        Rejected decisions are excluded — they did not enter the record.
        """
        return sorted(self._lineage.values(), key=lambda r: r.sequence_number)

    # ------------------------------------------------------------------
    # reset() — for testing only
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear in-memory state and backing registry. For testing only."""
        self._registry.reset()
        self._lineage.clear()
        self._all_verdicts.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_lineage_record(
        self,
        decision: RegistryDecision,
        trace_reference: str,
    ) -> ReplayLineageRecord:
        """Build a ReplayLineageRecord from a RegistryDecision."""
        now_iso = datetime.now(timezone.utc).isoformat()
        seq = decision.sequence_number

        parent_reference = str(seq - 1) if seq > 1 else ""

        # Canonical fields for hash — deterministic, no timestamps
        canonical = json.dumps({
            "message_id":      decision.message_id,
            "sequence_number": seq,
            "decision":        decision.status,
            "origin":          _ORIGIN,
            "schema_version":  _SCHEMA_VERSION,
            "trace_reference": trace_reference,
            "parent_reference":parent_reference,
        }, sort_keys=True)
        verification_hash = hashlib.sha256(canonical.encode()).hexdigest()

        replay_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, canonical))

        return ReplayLineageRecord(
            replay_id=replay_id,
            message_id=decision.message_id,
            sequence_number=seq,
            decision=decision.status,
            decision_timestamp=now_iso,
            origin_component=_ORIGIN,
            schema_version=_SCHEMA_VERSION,
            trace_reference=trace_reference,
            parent_reference=parent_reference,
            verification_hash=verification_hash,
        )


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all consumers in one process
# ---------------------------------------------------------------------------

_authority: CanonicalReplayAuthority | None = None


def get_authority(registry: ReplayRegistry | None = None) -> CanonicalReplayAuthority:
    """
    Return the process-level CanonicalReplayAuthority singleton.
    Pass a registry only on first call (or when overriding in tests).
    """
    global _authority
    if _authority is None:
        _authority = CanonicalReplayAuthority(registry)
    return _authority


def reset_authority(registry: ReplayRegistry | None = None) -> CanonicalReplayAuthority:
    """Replace the singleton. For testing only."""
    global _authority
    _authority = CanonicalReplayAuthority(registry)
    return _authority
