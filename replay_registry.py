"""
replay_registry.py — Phase 2: Durable Replay Registry

Persistent, file-backed replay registry that survives process restarts.

Features
--------
- File-backed storage (JSON): survives restarts, load-on-start, save-on-write
- Sequence number tracking with monotonic ordering validation
- TTL-based replay window enforcement
- Four decision states: VALID, DUPLICATE, STALE, FUTURE

Decision States
---------------
VALID      — new message, within TTL, sequence accepted
DUPLICATE  — message_id already processed
STALE      — message outside the allowed replay window (too old)
FUTURE     — sequence number is ahead of expected range (gap detected)

Persistence
-----------
Registry is written to disk on every VALID acceptance.
On start, the registry is loaded from disk if the file exists.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import config

DEFAULT_REGISTRY_PATH = Path("replay_registry.json")
DEFAULT_TTL_SECONDS: float = config.REPLAY_TTL_SECONDS
# Max sequence gap before a message is classified as FUTURE
MAX_SEQUENCE_GAP: int = 1000


@dataclass(frozen=True)
class RegistryDecision:
    message_id:  str
    sequence_number: int     # 0 if rejected before assignment
    status:      str         # VALID | DUPLICATE | STALE | FUTURE
    reason:      str


@dataclass
class _RegistryEntry:
    message_id:      str
    sequence_number: int
    issued_at:       float   # monotonic-equivalent: Unix timestamp at registration


class ReplayRegistry:
    """
    Persistent replay registry with sequence tracking and TTL enforcement.

    Thread-safe. All writes are immediately flushed to the backing file.
    """

    def __init__(
        self,
        path: Path | str = DEFAULT_REGISTRY_PATH,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_sequence_gap: int = MAX_SEQUENCE_GAP,
    ):
        self._path = Path(path)
        self._ttl = ttl_seconds
        self._max_gap = max_sequence_gap
        self._lock = threading.Lock()
        # message_id -> _RegistryEntry
        self._entries: dict[str, _RegistryEntry] = {}
        self._sequence_counter: int = 0
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, message_id: str, issued_at: float | None = None) -> RegistryDecision:
        """
        Submit a message for replay enforcement.

        Parameters
        ----------
        message_id : unique identifier of the message
        issued_at  : Unix timestamp when the message was originally issued
                     (defaults to now)
        """
        now = time.time()
        if issued_at is None:
            issued_at = now

        # Stale check first (time-based, before any sequence logic)
        age = now - issued_at
        if age > self._ttl:
            return RegistryDecision(
                message_id=message_id,
                sequence_number=0,
                status="STALE",
                reason=f"message age {age:.1f}s exceeds TTL {self._ttl:.1f}s",
            )

        with self._lock:
            # Duplicate check
            if message_id in self._entries:
                entry = self._entries[message_id]
                return RegistryDecision(
                    message_id=message_id,
                    sequence_number=entry.sequence_number,
                    status="DUPLICATE",
                    reason=f"already processed as sequence {entry.sequence_number}",
                )

            # Sequence assignment and future-gap check
            next_seq = self._sequence_counter + 1
            if next_seq - self._sequence_counter > self._max_gap:
                return RegistryDecision(
                    message_id=message_id,
                    sequence_number=0,
                    status="FUTURE",
                    reason=f"sequence gap {next_seq - self._sequence_counter} exceeds max {self._max_gap}",
                )

            self._sequence_counter = next_seq
            entry = _RegistryEntry(
                message_id=message_id,
                sequence_number=next_seq,
                issued_at=issued_at,
            )
            self._entries[message_id] = entry
            self._persist()

        return RegistryDecision(
            message_id=message_id,
            sequence_number=next_seq,
            status="VALID",
            reason="",
        )

    def validate_sequence_order(self, sequence_number: int) -> str:
        """
        Validate that a sequence number is within the expected ordering range.

        Returns one of: VALID | STALE | FUTURE
        """
        with self._lock:
            if sequence_number <= 0:
                return "STALE"
            if sequence_number > self._sequence_counter + self._max_gap:
                return "FUTURE"
            return "VALID"

    def is_known(self, message_id: str) -> bool:
        with self._lock:
            return message_id in self._entries

    def get_entry(self, message_id: str) -> _RegistryEntry | None:
        with self._lock:
            return self._entries.get(message_id)

    @property
    def sequence_count(self) -> int:
        with self._lock:
            return self._sequence_counter

    @property
    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)

    def reset(self) -> None:
        """Clear registry and backing file. For testing only."""
        with self._lock:
            self._entries.clear()
            self._sequence_counter = 0
            self._persist()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        """Write registry state to disk. Called under lock."""
        data = {
            "sequence_counter": self._sequence_counter,
            "entries": {
                mid: asdict(entry)
                for mid, entry in self._entries.items()
            },
        }
        # Atomic write via temp file
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._path)

    def _load(self) -> None:
        """Load registry state from disk if file exists."""
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self._sequence_counter = data.get("sequence_counter", 0)
            for mid, entry_data in data.get("entries", {}).items():
                self._entries[mid] = _RegistryEntry(**entry_data)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted file — start fresh
            self._entries.clear()
            self._sequence_counter = 0
