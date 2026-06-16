# REPLAY_DOCTRINE.md

> Phase 2 — Canonical Replay Doctrine
> Defines the single authority, its decision surface, and its explicit boundaries.

---

## Purpose

Replay protection in QCG exists to answer one question per message:

> Has this exact execution artifact been seen before, and is it still within its valid window?

The answer must come from exactly one component, using exactly one vocabulary, stored in exactly one place. This document defines that component, that vocabulary, and those boundaries.

---

## Authority Owned

**`ReplayRegistry` is the sole replay authority in QCG.**

It is the only component permitted to:

- Accept a new artifact into the replay record
- Declare an artifact a duplicate
- Declare an artifact stale
- Declare an artifact a future-gap anomaly
- Assign sequence numbers
- Persist replay state across restarts

Every other component must call `ReplayRegistry` for a verdict. No other component may maintain its own seen-set, replay cache, or sequence counter.

---

## Authority Explicitly Not Owned

The following components **must not** make independent replay decisions:

| Component | Current Drift | Required Change |
|-----------|--------------|-----------------|
| `RuntimeCore` | Owns `_replay_registry` dict, emits `HALT:REPLAY_DETECTED` | Must remove internal registry; accept verdict from `ReplayRegistry` as input |
| `Receiver` (`gateway.py`) | Owns `_seen` dict, emits `HALT:REPLAY_DETECTED` | Must remove internal seen-set; consume pre-computed verdict only |
| `QuantumGateway` (`hybrid_gateway.py`) | Owns `_replay_registry` dict at `industrial_endpoint` | Must remove internal registry; consume pre-computed verdict only |
| `execution_process.py` | Instantiates its own `ReplayEnforcer`, calls it directly | Must delegate to `ReplayRegistry` instead |
| `ReplayEnforcer` | Operates as an independent authority with its own state | Becomes a deprecated path; all callers redirect to `ReplayRegistry` |

---

## Decision Inputs

`ReplayRegistry.submit()` requires:

| Input | Type | Purpose |
|-------|------|---------|
| `message_id` | `str` | The unique identifier of the execution artifact |
| `issued_at` | `float \| None` | Unix timestamp when the artifact was originally issued; defaults to now |

No other inputs affect the verdict. The registry does not inspect payload content, producer type, or confidence values.

---

## Decision Outputs

Every call to `ReplayRegistry.submit()` returns a `RegistryDecision`:

| Field | Type | Meaning |
|-------|------|---------|
| `message_id` | `str` | Echo of the submitted identifier |
| `sequence_number` | `int` | Assigned sequence (0 if rejected before assignment) |
| `status` | `str` | One of the four canonical verdicts below |
| `reason` | `str` | Human-readable rejection explanation (empty on VALID) |

---

## Replay States

These are the only four valid verdicts in QCG. No other component may introduce additional replay vocabulary.

| Verdict | Condition | Sequence Assigned |
|---------|-----------|-------------------|
| `VALID` | New `message_id`, within TTL, sequence within gap limit | ✅ Yes |
| `DUPLICATE` | `message_id` already in registry | ❌ No (existing sequence returned) |
| `STALE` | `now - issued_at > TTL` (checked before duplicate) | ❌ No |
| `FUTURE` | Sequence gap exceeds `REPLAY_MAX_SEQUENCE_GAP` | ❌ No |

Stale detection fires before duplicate detection. A stale artifact is never registered. This prevents an attacker from pre-seeding a replay by submitting a stale artifact first.

---

## Replay Lineage

Every `VALID` decision creates a `_RegistryEntry` containing:

- `message_id` — the artifact identifier
- `sequence_number` — monotonically assigned, never reused
- `issued_at` — Unix timestamp of original issue

This entry is persisted to `replay_registry.json` on every acceptance using an atomic write (temp file + rename). The lineage record survives process restarts. On startup, `ReplayRegistry` loads its full prior state before accepting any new submissions.

---

## Failure Modes

| Failure | Behavior |
|---------|----------|
| File read error on startup | Registry starts empty; logs warning; does not crash |
| Corrupted JSON on startup | Registry starts empty; treats as fresh start |
| Concurrent submissions of same `message_id` | Lock guarantees exactly one `VALID`; all others receive `DUPLICATE` |
| Disk write failure on `_persist()` | Acceptance is rolled back; `VALID` verdict is not returned to caller |
| Process restart | Registry reloads from file; sequence counter and all prior entries restored |
| Cache growth | No eviction by default (registry is a permanent record); bounded by available disk |

---

## Authority Ceiling

`ReplayRegistry` decides **occurrence** — whether this artifact has been seen and whether it is within its valid window.

`ReplayRegistry` does **not** decide:

- Whether the artifact's payload is correct
- Whether the producer is authorized
- Whether the contract version is valid
- Whether the execution result should be trusted
- Whether the message is semantically meaningful

**Replay proves occurrence. Replay does NOT prove legitimacy.**

These decisions belong to `GovernanceLayer`, `RuntimeCore`, and `ProducerVerificationLayer` respectively. `ReplayRegistry` must not receive or store information that would allow it to make those decisions.

---

## Upstream Inputs

`ReplayRegistry` receives calls from:

- `execution_process.py` — submits `trace_id` before contract execution
- `CommunicationGateway` / `Receiver` — submits `message_id` before acknowledgement
- `QuantumGateway` — submits `trace_id` before endpoint delivery

All callers must use the `submit()` interface. No caller may bypass the registry by maintaining a local cache.

---

## Downstream Consumers

Components that consume `RegistryDecision` verdicts:

| Consumer | On `VALID` | On `DUPLICATE` / `STALE` / `FUTURE` |
|----------|-----------|--------------------------------------|
| `execution_process.py` | Proceed to trust verification + execution | Return `HALT:{status}` immediately |
| `Receiver` | Proceed to transport status resolution | Return `transport_status="HALT:REPLAY_{status}"` |
| `QuantumGateway` | Proceed to endpoint delivery | Return `"HALT:REPLAY_{status}"` |

---

## MDU Attachment Surface

The `_RegistryEntry` record is the natural attachment point for future MDU (Message Dispatch Unit) lineage tracking. When MDU requires replay lineage, it reads `ReplayRegistry` entries directly. `ReplayRegistry` must not be modified to serve MDU-specific concerns — MDU attaches to the existing record structure.

---

## TMS Placement

`ReplayRegistry` sits between the transport layer and the execution layer:

```
[Transport / Producer]
        |
        v
  ReplayRegistry.submit()   ← single replay decision point
        |
   VALID verdict
        |
        v
[GovernanceLayer + RuntimeCore]
```

The registry is called after message receipt and before any execution or governance logic. A non-`VALID` verdict short-circuits the pipeline immediately.

---

## Explicit Statement

> **Replay proves occurrence.**
> **Replay does NOT prove legitimacy.**

Occurrence: this artifact was received, it is within its valid window, and it has not been seen before.

Legitimacy: the artifact's producer is authorized, the payload is uncorrupted, and the execution is policy-compliant.

These are distinct claims. `ReplayRegistry` is the authority for the first. It has no opinion on the second.
