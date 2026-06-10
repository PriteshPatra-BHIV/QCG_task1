# DETERMINISM_DOCTRINE.md

> Formal classification of every field in every core model.
> Source of truth for what is DETERMINISTIC vs OBSERVABILITY vs RUNTIME_ONLY.

---

## Classification Definitions

| Class | Definition |
|-------|-----------|
| `DETERMINISTIC` | Identical for identical inputs, regardless of wall clock or run number. Must match across replay comparisons. |
| `OBSERVABILITY` | Wall-clock metadata. Records when something happened. Excluded from replay comparison. May differ between runs. |
| `RUNTIME_ONLY` | Generated transiently during execution; not persisted in the artifact. |

---

## ComputationExecutionContract (`execution_contract.py`)

| Field | Class | Reason |
|-------|-------|--------|
| `producer_type` | DETERMINISTIC | Determined by adapter selection, not time |
| `payload` | DETERMINISTIC | Hash of producer output |
| `confidence` | DETERMINISTIC | Computed from quantum distribution counts |
| `trace_id` | DETERMINISTIC | UUID-5 from deterministic seed |
| `contract_version` | DETERMINISTIC | Config constant |
| `execution_constraints` | DETERMINISTIC | Producer metadata, seed-derived |
| `payload_hash` | DETERMINISTIC | SHA-256 of canonical payload |
| `producer_id` | DETERMINISTIC | Node identity (stable across runs) |
| `producer_signature` | DETERMINISTIC | ECDSA P-256 signature over payload_hash (stable given same private key) |
| `contract_signature` | DETERMINISTIC | ECDSA P-256 signature over deterministic state dict |
| `timestamp` | OBSERVABILITY | Wall-clock creation time |

---

## ExecutionResult (`runtime_core.py`)

| Field | Class | Reason |
|-------|-------|--------|
| `contract_trace_id` | DETERMINISTIC | Passthrough from contract |
| `producer_type` | DETERMINISTIC | Passthrough from contract |
| `ack` | DETERMINISTIC | Determined by confidence thresholds |
| `confidence` | DETERMINISTIC | Passthrough from contract |
| `runtime_hash` | DETERMINISTIC | SHA-256 of (payload_hash, confidence, ack) |
| `execution_timestamp` | OBSERVABILITY | Wall-clock execution time |

---

## AuditEntry (`audit_trail.py`)

| Field | Class | Reason |
|-------|-------|--------|
| `sequence` | DETERMINISTIC | Monotonic counter, not time-based |
| `event_type` | DETERMINISTIC | Caller-specified |
| `event_hash` | DETERMINISTIC | SHA-256 of event_data (no timestamp in hash) |
| `node_id` | DETERMINISTIC | Node identity |
| `event_data` | DETERMINISTIC | Raw event payload |
| `timestamp` | OBSERVABILITY | Wall-clock append time |

Note: `leaf_hash` (property) is DETERMINISTIC because it uses `sequence`, `event_type`, `event_hash`, `node_id` only — not `timestamp`.

---

## TrustChainLink (`trust_chain.py`)

| Field | Class | Reason |
|-------|-------|--------|
| `from_node` | DETERMINISTIC | Node identity |
| `to_node` | DETERMINISTIC | Node identity |
| `action` | DETERMINISTIC | Caller-specified |
| `signature` | DETERMINISTIC | ECDSA P-256 signature over deterministic handoff dict |
| `payload_hash` | DETERMINISTIC | SHA-256 of artifact |
| `timestamp` | OBSERVABILITY | Wall-clock handoff time |

Note: `handoff_hash` (property) is DETERMINISTIC — it excludes `timestamp`.

---

## ConsensusProof (`consensus_simulation.py`)

| Field | Class | Reason |
|-------|-------|--------|
| `participating_nodes` | DETERMINISTIC | Determined by node list |
| `final_hash` | DETERMINISTIC | Majority runtime_hash |
| `agreement_percentage` | DETERMINISTIC | Math from node count |
| `consensus_reached` | DETERMINISTIC | Threshold comparison |
| `disagreements` | DETERMINISTIC | Determined by hash comparison |
| `consensus_round` | DETERMINISTIC | Caller-specified round counter |
| `quorum_size` | DETERMINISTIC | Math from node count |
| `node_attestations` | DETERMINISTIC | Signed per-node votes |
| `consensus_timestamp` | OBSERVABILITY | Wall-clock time |

---

## Timestamp Isolation Verification

Timestamps are excluded from replay comparison via:

```python
# determinism_doctrine.py — DeterminismOracle
def extract_deterministic_projection(self, obj) -> dict:
    # Returns only DETERMINISTIC fields; skips OBSERVABILITY
```

Used in:
- `determinism_proof.run_determinism_proof()` — 20-run comparison
- `replay_bundle.ReplayBundle.verify()` — bundle verification
- `adapters.py` — contract comparison in replay engine

---

## Enforcement Point

`DeterminismOracle` in `determinism_doctrine.py` is the **single authority** for
field classification. All replay comparisons must use its projections. Direct
field comparison of full dataclass dicts (which include timestamps) is forbidden
in replay paths.
