# Timestamp Isolation Doctrine

## Purpose

This document defines why timestamps are excluded from deterministic replay
comparison and specifies exactly which fields are ignored during replay
verification.

---

## Core Principle

**A deterministic system produces identical outputs for identical inputs,
regardless of when execution occurs.**

Timestamps record *when* something happened. They are observability data —
useful for audit, tracing, and debugging — but they are not part of the
*what* that the system computed.

Including timestamps in replay equality would make every execution unique by
definition, destroying the ability to verify determinism.

---

## Field Classification

### DETERMINISTIC fields — participate in replay equality

| Field               | Source Contract     | Rationale |
|---------------------|---------------------|-----------|
| `message_id`        | CommunicationRequest | Content-addressed UUID-5; identical for identical inputs |
| `payload_hash`      | TranslationContract  | SHA-256 of canonical payload; deterministic by construction |
| `confidence`        | CommunicationRequest | Producer-declared; identical for identical inputs |
| `translation_status`| TranslationContract  | Derived from confidence thresholds; deterministic |
| `transport_status`  | AcknowledgementContract | Derived from translation_status; deterministic |

### OBSERVABILITY fields — excluded from replay equality

| Field             | Source Contract          | Why excluded |
|-------------------|--------------------------|--------------|
| `created_at`      | TranslationContract      | Wall-clock timestamp of contract creation |
| `issued_at`       | AcknowledgementContract  | Wall-clock timestamp of ACK issuance |
| `trace_timestamp` | Trace / audit entries    | Wall-clock anchor for observability tooling |

---

## How Deterministic Comparison Is Performed

1. Extract the **deterministic projection** from each contract:
   ```python
   rc.deterministic_projection()
   # → {"message_id": ..., "payload_hash": ..., "confidence": ...,
   #    "translation_status": ..., "transport_status": ...}
   ```

2. Compute the **deterministic hash** (SHA-256 of canonical JSON):
   ```python
   rc.deterministic_hash()
   # → "a3f1..." — identical across all runs with identical inputs
   ```

3. Compare hashes or projections directly:
   ```python
   comparator = ReplayComparator()
   result = comparator.compare(contract_run_1, contract_run_2)
   assert result.passed  # True even though timestamps differ
   ```

4. Observability diffs are **recorded** in the result but **never affect the
   verdict**:
   ```python
   result.observability_diffs
   # → {"issued_at": {"a": "2024-01-01T...", "b": "2024-01-02T..."}}
   # This is expected and correct.
   ```

---

## Replay Verification Rule

Two contracts are considered **replay-equivalent** if and only if their
deterministic projections are identical.

```
replay_equal(A, B) ⟺ A.deterministic_projection() == B.deterministic_projection()
```

Timestamps, trace anchors, and any other wall-clock fields are explicitly
excluded from this definition.

---

## References

- `deterministic_replay.py` — `DETERMINISTIC_FIELDS`, `OBSERVABILITY_FIELDS`
- `determinism_doctrine.py` — `DeterminismOracle`, `FieldClass`
- `determinism_20_run_proof.py` — 20-run consistency proof
