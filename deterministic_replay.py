"""
deterministic_replay.py — Phase 1: Deterministic Replay Package

ReplayContract       : Immutable snapshot of a communication contract's
                       deterministic + observability fields.
ReplayComparator     : Compares two ReplayContracts on deterministic fields only.
DeterministicComparisonResult : Outcome of a deterministic comparison.

Field Classification
--------------------
DETERMINISTIC  : message_id, payload_hash, confidence, translation_status,
                 transport_status
OBSERVABILITY  : created_at, issued_at, trace_timestamp

Replay equality is defined exclusively over DETERMINISTIC fields.
Observability fields are recorded for audit but never participate in
equality checks.  See docs/timestamp_isolation_doctrine.md.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Field classification registry
# ---------------------------------------------------------------------------

DETERMINISTIC_FIELDS: frozenset[str] = frozenset({
    "message_id",
    "payload_hash",
    "confidence",
    "translation_status",
    "transport_status",
})

OBSERVABILITY_FIELDS: frozenset[str] = frozenset({
    "created_at",
    "issued_at",
    "trace_timestamp",
})


# ---------------------------------------------------------------------------
# ReplayContract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReplayContract:
    """
    Immutable snapshot extracted from a CommunicationResponse for replay
    comparison purposes.

    Fields are classified at construction time.  Observability fields are
    stored for audit but excluded from __eq__ and hashing.
    """
    # DETERMINISTIC
    message_id:         str
    payload_hash:       str
    confidence:         float
    translation_status: str
    transport_status:   str
    # OBSERVABILITY (audit only)
    created_at:         str = ""
    issued_at:          str = ""
    trace_timestamp:    str = ""

    def deterministic_projection(self) -> dict:
        """Return only the deterministic fields as a dict."""
        return {
            "message_id":         self.message_id,
            "payload_hash":       self.payload_hash,
            "confidence":         self.confidence,
            "translation_status": self.translation_status,
            "transport_status":   self.transport_status,
        }

    def deterministic_hash(self) -> str:
        """SHA-256 of the deterministic projection (canonical JSON)."""
        raw = json.dumps(self.deterministic_projection(), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def from_response(response: Any) -> "ReplayContract":
        """
        Build a ReplayContract from a CommunicationResponse.
        Works with both dataclass objects and plain dicts.
        """
        def _get(obj, key, default=""):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        tc = _get(response, "translation_contract")
        ack = _get(response, "acknowledgement")

        return ReplayContract(
            message_id=_get(response, "message_id"),
            payload_hash=_get(tc, "payload_hash"),
            confidence=_get(tc, "confidence", 0.0),
            translation_status=_get(tc, "translation_status"),
            transport_status=_get(ack, "transport_status"),
            created_at=_get(tc, "created_at"),
            issued_at=_get(ack, "issued_at"),
            trace_timestamp="",
        )


# ---------------------------------------------------------------------------
# DeterministicComparisonResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeterministicComparisonResult:
    """Outcome of comparing two ReplayContracts on deterministic fields only."""
    passed:              bool
    deterministic_match: bool
    mismatched_fields:   tuple        # tuple of field names that differ
    observability_diffs: dict         # observability fields that differ (audit)
    projection_a:        dict
    projection_b:        dict

    @property
    def is_deterministic(self) -> bool:
        return self.deterministic_match


# ---------------------------------------------------------------------------
# ReplayComparator
# ---------------------------------------------------------------------------

class ReplayComparator:
    """
    Compares two ReplayContracts using only deterministic fields.

    Observability fields (timestamps) are recorded in the result for
    audit but never affect the passed/failed verdict.
    """

    def compare(
        self,
        a: ReplayContract,
        b: ReplayContract,
    ) -> DeterministicComparisonResult:
        proj_a = a.deterministic_projection()
        proj_b = b.deterministic_projection()

        mismatched = tuple(
            k for k in proj_a
            if proj_a[k] != proj_b.get(k)
        )
        deterministic_match = len(mismatched) == 0

        obs_a = {"created_at": a.created_at, "issued_at": a.issued_at,
                 "trace_timestamp": a.trace_timestamp}
        obs_b = {"created_at": b.created_at, "issued_at": b.issued_at,
                 "trace_timestamp": b.trace_timestamp}
        observability_diffs = {
            k: {"a": obs_a[k], "b": obs_b[k]}
            for k in obs_a
            if obs_a[k] != obs_b[k]
        }

        return DeterministicComparisonResult(
            passed=deterministic_match,
            deterministic_match=deterministic_match,
            mismatched_fields=mismatched,
            observability_diffs=observability_diffs,
            projection_a=proj_a,
            projection_b=proj_b,
        )

    def compare_many(
        self,
        contracts: list[ReplayContract],
    ) -> DeterministicComparisonResult:
        """
        Compare all contracts in the list against the first.
        Returns a single DeterministicComparisonResult reflecting whether
        all are identical on deterministic fields.
        """
        if len(contracts) < 2:
            raise ValueError("Need at least 2 contracts to compare.")

        reference = contracts[0]
        all_mismatches: set[str] = set()
        all_obs_diffs: dict = {}

        for c in contracts[1:]:
            result = self.compare(reference, c)
            all_mismatches.update(result.mismatched_fields)
            all_obs_diffs.update(result.observability_diffs)

        return DeterministicComparisonResult(
            passed=len(all_mismatches) == 0,
            deterministic_match=len(all_mismatches) == 0,
            mismatched_fields=tuple(sorted(all_mismatches)),
            observability_diffs=all_obs_diffs,
            projection_a=reference.deterministic_projection(),
            projection_b=contracts[-1].deterministic_projection(),
        )
