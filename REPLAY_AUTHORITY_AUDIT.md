# REPLAY_AUTHORITY_AUDIT.md

> Phase 1 — Replay Authority Audit
> Documents every component in QCG that currently makes a replay decision.

---

## Audit Question

**Who currently decides replay truth?**

Four components independently make replay decisions. None delegates to the others.
This is the authority drift problem.

---

## Component Audit

---

### 1. `hybrid_gateway.py` — `industrial_endpoint()` / `QuantumGateway`

| Dimension | Detail |
|-----------|--------|
| **Decision produced** | `HALT:REPLAY_DETECTED` or allows execution |
| **Authority exercised** | Owns the `_replay_registry` dict; decides if a trace_id has been seen |
| **State owned** | `self._replay_registry: dict[str, str]` — maps `trace_id → decoded_message` |
| **Replay metadata stored** | `trace_id`, `decoded_message` |
| **Duplicate detection method** | `if contract.trace_id in replay_registry` — in-memory dict |
| **Persistence model** | None — memory only, lost on restart |
| **Verdict emitted** | Implicit: proceeds or returns `"HALT:REPLAY_DETECTED"` |

**Authority exercised here:** Full replay verdict — does not consult any other component.

---

### 2. `runtime_core.py` — `RuntimeCore._replay_registry`

| Dimension | Detail |
|-----------|--------|
| **Decision produced** | `HALT:REPLAY_DETECTED` via `ExecutionResult.ack` |
| **Authority exercised** | Owns a second independent replay registry; decides if a trace_id has been executed |
| **State owned** | `self._replay_registry: dict[str, str]` — maps `trace_id → payload_hash`, capped at 100,000 entries |
| **Replay metadata stored** | `trace_id`, `payload_hash` |
| **Duplicate detection method** | `if contract.trace_id in self._replay_registry` — in-memory dict with LRU-style eviction |
| **Persistence model** | None — memory only, lost on restart |
| **Verdict emitted** | Returns `ExecutionResult(ack="HALT:REPLAY_DETECTED")` |

**Authority exercised here:** Full replay verdict — independent of ReplayEnforcer, independent of QuantumGateway. Operates at the runtime layer without coordination.

---

### 3. `replay_enforcer.py` — `ReplayEnforcer`

| Dimension | Detail |
|-----------|--------|
| **Decision produced** | `ACCEPTED`, `REJECTED_DUPLICATE`, `REJECTED_STALE` |
| **Authority exercised** | Owns sequence assignment, TTL enforcement, duplicate detection |
| **State owned** | `self._cache: dict[str, tuple[int, float]]` — maps `artifact_id → (sequence_id, issued_at)`, capped at 10,000 |
| **Replay metadata stored** | `artifact_id`, `sequence_id`, `issued_at` (monotonic) |
| **Duplicate detection method** | `if artifact_id in self._cache` — in-memory dict |
| **Persistence model** | None — memory only, lost on restart |
| **Verdict emitted** | `ReplayDecision(status="ACCEPTED"|"REJECTED_DUPLICATE"|"REJECTED_STALE")` |

**Authority exercised here:** Full independent replay verdict with sequence tracking and TTL. Used only by `execution_process.py`. Not consulted by `QuantumGateway` or `RuntimeCore`.

---

### 4. `replay_registry.py` — `ReplayRegistry`

| Dimension | Detail |
|-----------|--------|
| **Decision produced** | `VALID`, `DUPLICATE`, `STALE`, `FUTURE` |
| **Authority exercised** | Owns sequence tracking with gap detection, TTL enforcement, persistent storage |
| **State owned** | `self._entries: dict[str, _RegistryEntry]` — maps `message_id → _RegistryEntry(message_id, sequence_number, issued_at)` |
| **Replay metadata stored** | `message_id`, `sequence_number`, `issued_at` (Unix timestamp) |
| **Duplicate detection method** | `if message_id in self._entries` — in-memory dict backed by JSON file |
| **Persistence model** | File-backed JSON (`replay_registry.json`), atomic write via temp file, loaded on start |
| **Verdict emitted** | `RegistryDecision(status="VALID"|"DUPLICATE"|"STALE"|"FUTURE")` |

**Authority exercised here:** Full independent replay verdict with the most features — persistence, gap detection (`FUTURE`), sequence validation. However, it is not called by `QuantumGateway`, `RuntimeCore`, or `Receiver`. It is an orphaned authority — it owns the most capability but is not the coordinator.

---

### 5. `gateway.py` — `Receiver`

| Dimension | Detail |
|-----------|--------|
| **Decision produced** | `HALT:REPLAY_DETECTED` returned in `AcknowledgementContract.transport_status` |
| **Authority exercised** | Owns a seen-set; decides if a `message_id` has already been acknowledged |
| **State owned** | `self._seen: dict[str, None]` — insertion-ordered set of `message_id` values, capped at 100,000 |
| **Replay metadata stored** | `message_id` only |
| **Duplicate detection method** | `if translation_contract.message_id in self._seen` — in-memory dict |
| **Persistence model** | None — memory only, lost on restart |
| **Verdict emitted** | Returns `AcknowledgementContract(transport_status="HALT:REPLAY_DETECTED")` |

**Authority exercised here:** Full replay verdict at the communication layer. Does not coordinate with `ReplayEnforcer`, `ReplayRegistry`, or `RuntimeCore`.

---

## Summary Table

| Component | Verdict Set | State Type | Persists | Coordinates With |
|-----------|-------------|------------|----------|-----------------|
| `QuantumGateway` (`hybrid_gateway.py`) | implicit allow / `HALT:REPLAY_DETECTED` | in-memory dict | ❌ | nobody |
| `RuntimeCore` (`runtime_core.py`) | `HALT:REPLAY_DETECTED` | in-memory dict (capped 100k) | ❌ | nobody |
| `ReplayEnforcer` (`replay_enforcer.py`) | `ACCEPTED` / `REJECTED_DUPLICATE` / `REJECTED_STALE` | in-memory dict (capped 10k) | ❌ | `execution_process.py` only |
| `ReplayRegistry` (`replay_registry.py`) | `VALID` / `DUPLICATE` / `STALE` / `FUTURE` | file-backed JSON | ✅ | nobody (orphaned) |
| `Receiver` (`gateway.py`) | `HALT:REPLAY_DETECTED` | in-memory dict (capped 100k) | ❌ | nobody |

---

## Identified Drift Points

1. **Five separate replay decision points** — none delegates to another.
2. **Four incompatible verdict vocabularies** — `ACCEPTED/REJECTED_*`, `VALID/DUPLICATE/STALE/FUTURE`, `HALT:REPLAY_DETECTED`, and implicit allow.
3. **One persistence-capable component (`ReplayRegistry`) is never called by any runtime path** — its capabilities are unused by the live system.
4. **Sequence tracking exists in two places** (`ReplayEnforcer`, `ReplayRegistry`) with no shared counter.
5. **A replay attack can pass `Receiver` but be caught by `RuntimeCore`** — or vice versa — with no shared record of what happened.
6. **Restart leaves the system blind** — every in-memory store resets; only `ReplayRegistry` survives but is not wired in.

---

## Answer: Who currently decides replay truth?

No single component. Replay truth is currently decided by whichever of the five components a given message path happens to pass through. The same `trace_id` could receive a different verdict depending on whether it arrived via `CommunicationGateway`, `QuantumGateway`, or `execution_process`. This is the authority drift the task exists to eliminate.
