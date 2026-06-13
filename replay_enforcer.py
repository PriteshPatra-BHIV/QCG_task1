"""
replay_enforcer.py — Phase 3: Replay Attack Protection

Provides sequence-tracked, TTL-enforced replay rejection.

Every execution artifact receives:
  - sequence_id  : monotonically increasing integer
  - issued_at    : UTC timestamp for TTL enforcement

Decisions returned:
  ACCEPTED           — new artifact within TTL
  REJECTED_DUPLICATE — artifact already seen (same artifact_id)
  REJECTED_STALE     — artifact outside TTL window
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import config

# Default TTL pulled from config
DEFAULT_TTL_SECONDS: float = config.REPLAY_TTL_SECONDS

# Evict expired cache entries when cache exceeds this size
_EVICTION_THRESHOLD: int = 10_000


@dataclass(frozen=True)
class ReplayDecision:
    artifact_id: str
    sequence_id: int        # 0 if rejected before assignment
    status: str             # ACCEPTED | REJECTED_DUPLICATE | REJECTED_STALE
    reason: str


class ReplayEnforcer:
    """
    Thread-safe replay cache with monotonic sequence tracking and TTL.

    Each artifact_id is accepted exactly once within its TTL window.
    Duplicate submissions are rejected as REJECTED_DUPLICATE.
    Artifacts presented after TTL expiry are rejected as REJECTED_STALE.
    """

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._sequence_counter: int = 0
        # artifact_id -> (sequence_id, issued_at_monotonic)
        self._cache: dict[str, tuple[int, float]] = {}

    def submit(self, artifact_id: str, issued_at: float | None = None) -> ReplayDecision:
        """
        Submit an artifact for replay enforcement.

        Parameters
        ----------
        artifact_id : unique identifier of the execution artifact
        issued_at   : monotonic time the artifact was originally issued
                      (defaults to now — useful for testing stale scenarios)
        """
        now = time.monotonic()
        if issued_at is None:
            issued_at = now

        # Stale check (before cache lookup — stale wins over duplicate)
        age = now - issued_at
        if age > self._ttl:
            return ReplayDecision(
                artifact_id=artifact_id,
                sequence_id=0,
                status="REJECTED_STALE",
                reason=f"artifact age {age:.1f}s exceeds TTL {self._ttl:.1f}s",
            )

        with self._lock:
            if artifact_id in self._cache:
                seq, _ = self._cache[artifact_id]
                return ReplayDecision(
                    artifact_id=artifact_id,
                    sequence_id=seq,
                    status="REJECTED_DUPLICATE",
                    reason=f"artifact_id already processed as sequence {seq}",
                )

            self._sequence_counter += 1
            seq = self._sequence_counter
            self._cache[artifact_id] = (seq, issued_at)
            self._evict_if_needed(now)

        return ReplayDecision(
            artifact_id=artifact_id,
            sequence_id=seq,
            status="ACCEPTED",
            reason="",
        )

    def _evict_if_needed(self, now: float) -> None:
        """Remove expired entries when cache grows large. Called under lock."""
        if len(self._cache) < _EVICTION_THRESHOLD:
            return
        expired = [
            aid for aid, (_, issued) in self._cache.items()
            if now - issued > self._ttl
        ]
        for aid in expired:
            del self._cache[aid]
        # If nothing expired but cache is still at threshold, evict oldest by issued_at
        if len(self._cache) >= _EVICTION_THRESHOLD:
            oldest = sorted(self._cache.items(), key=lambda kv: kv[1][1])
            for aid, _ in oldest[:max(1, _EVICTION_THRESHOLD // 10)]:
                del self._cache[aid]

    def reset(self) -> None:
        """Clear cache and reset sequence counter (for testing)."""
        with self._lock:
            self._cache.clear()
            self._sequence_counter = 0

    @property
    def sequence_count(self) -> int:
        with self._lock:
            return self._sequence_counter


if __name__ == "__main__":
    import time

    print("=== REPLAY ENFORCER DEMO ===\n")
    enforcer = ReplayEnforcer(ttl_seconds=5.0)

    print("[1] Valid execution — ACCEPTED")
    d1 = enforcer.submit("artifact-001")
    print(f"    {d1.status}  seq={d1.sequence_id}")

    print("[2] Duplicate replay — REJECTED_DUPLICATE")
    d2 = enforcer.submit("artifact-001")
    print(f"    {d2.status}  reason={d2.reason}")

    print("[3] New artifact — ACCEPTED")
    d3 = enforcer.submit("artifact-002")
    print(f"    {d3.status}  seq={d3.sequence_id}")

    print("[4] Stale artifact (issued 10s ago, TTL=5s) — REJECTED_STALE")
    stale_issued_at = time.monotonic() - 10.0
    d4 = enforcer.submit("artifact-003", issued_at=stale_issued_at)
    print(f"    {d4.status}  reason={d4.reason}")

    print("\n[DONE] All enforcement cases demonstrated.")
