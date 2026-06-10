# REPLAY_ENFORCEMENT.md

> Phase 3: Replay Attack Protection — Specification and Evidence

---

## Objective

Move from replay *verification* (proving history) to replay *protection* (blocking attacks).

---

## Components

### 1. ReplayEnforcer (`replay_enforcer.py`)

Every execution artifact submitted receives:

- `sequence_id` — monotonically increasing integer, assigned at first acceptance
- `issued_at` — the monotonic timestamp used for TTL comparison

Decisions:

| Status | Condition |
|--------|-----------|
| `ACCEPTED` | New artifact_id, within TTL |
| `REJECTED_DUPLICATE` | artifact_id already in cache |
| `REJECTED_STALE` | `now - issued_at > TTL` (checked before duplicate) |

Stale detection fires before duplicate check — a stale artifact is never
admitted to the cache. This prevents an attacker from pre-seeding a replay
by presenting a stale artifact first.

### 2. RuntimeCore replay guard (`runtime_core.py`)

The existing `_replay_registry` (trace_id → payload_hash) provides a secondary
in-runtime layer. Any contract whose trace_id was already processed returns
`HALT:REPLAY_DETECTED`.

The two layers are independent and composable:
- `ReplayEnforcer` — pre-execution, IPC-level, TTL-aware
- `RuntimeCore._replay_registry` — in-execution, trace_id-scoped

---

## Sequence Tracking

```python
enforcer = ReplayEnforcer()  # TTL from config.REPLAY_TTL_SECONDS (default 300s)
d = enforcer.submit("artifact-001")
# d.sequence_id == 1  (monotonic, starts at 1)
# d.status     == "ACCEPTED"
```

Sequence IDs are:
- Assigned only on ACCEPTED decisions
- Never reused (monotonic counter, never decremented)
- Thread-safe (protected by `threading.Lock`)

---

## TTL / Stale Detection

Default TTL: `config.REPLAY_TTL_SECONDS` (default 300s, overridable via `QCG_REPLAY_TTL_SECONDS`).

```python
enforcer = ReplayEnforcer(ttl_seconds=60.0)
stale_issued = time.monotonic() - 120.0
d = enforcer.submit("old-artifact", issued_at=stale_issued)
# d.status == "REJECTED_STALE"
# d.reason == "artifact age 120.0s exceeds TTL 60.0s"
```

The `issued_at` parameter accepts a monotonic timestamp. The `execution_process`
converts wall-clock `issued_at` from the producer message to a monotonic offset:

```python
age = time.time() - issued_at_wall
issued_at_mono = time.monotonic() - age
```

## Cache Eviction

The cache is bounded. When it exceeds 10,000 entries, expired entries are evicted
on the next insert (under lock). This prevents unbounded memory growth in
long-running processes while maintaining O(1) average-case lookup.

---

## Evidence Matrix

| Case | Expected Status | Test |
|------|----------------|------|
| New artifact, within TTL | `ACCEPTED` | `TestReplayEnforcer.test_valid_execution_accepted` |
| Same artifact submitted twice | `REJECTED_DUPLICATE` | `TestReplayEnforcer.test_duplicate_rejected` |
| Artifact issued 10s ago, TTL=1s | `REJECTED_STALE` | `TestReplayEnforcer.test_stale_rejected` |
| Sequence numbers are monotonic | seq 1,2,3,4,5 | `TestReplayEnforcer.test_sequence_monotonic` |
| Stale beats duplicate | `REJECTED_STALE` not `ACCEPTED` | `TestReplayEnforcer.test_stale_beats_duplicate` |

---

## Known Limitations

- `issued_at` relies on the producer honestly reporting issue time. Production
  requires a cryptographically signed timestamp from a trusted time authority.
- TTL default (300s) is overridable via `QCG_REPLAY_TTL_SECONDS` but deployment
  SLA should determine the correct value.
- The replay cache does not persist across process restarts.
- Cache eviction is insert-triggered above 10,000 entries, not time-triggered.
  A short-TTL, high-volume scenario could briefly exceed this threshold.
