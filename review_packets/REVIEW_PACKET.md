# REVIEW_PACKET — Hybrid Quantum Communication Gateway (QCG)

> Single source of truth for reviewers. Covers the complete system across all phases.
> Last verified: 2026-06-11 | Tests: 275 collected (0 failures) | Exit 0 on all proof scripts.

---

## 1. Entry Points

| Command | What it does |
|---------|-------------|
| `python simulation.py` | All 4 cross-system paths through `CommunicationGateway.send()`. |
| `python runtime_demo.py` | Full 6-phase demonstration (contract → adapters → participation → governance → observability → distributed). |
| `python determinism_proof.py` | 20-run proof: same seed + same message = identical output. Exit 0 = PASS. |
| `python determinism_20_run_proof.py` | Phase 1 hardening proof: 20 runs, deterministic hash identical, timestamps allowed to differ. Exit 0 = PASS. |
| `python replay_enforcement_proof.py` | Phase 2 durable replay proof: 6 cases (VALID, DUPLICATE, STALE, sequence, restart persistence). Exit 0 = PASS. |
| `python crash_recovery_proof.py` | Phase 3 crash recovery proof: registry survives crash, duplicates blocked after restart, process isolation confirmed. Exit 0 = PASS. |
| `python process_runner.py` | Three-process pipeline (Producer → Execution → Consensus). |
| `python process_runner.py --crash producer\|execution\|consensus` | Crash simulation for each stage. |
| `python replay_enforcer.py` | In-memory replay enforcer demo. |
| `pytest tests/ -v` | Full test suite. |

---

## 2. Architecture

```
[Producer Process]          producer_process.py          PID: independent
      |
      |  multiprocessing.Queue  (q_prod_exec)
      |  { type: CONTRACT, contract: {...}, producer_public_key: <hex>, issued_at: <float> }
      v
[Execution Process]         execution_process.py         PID: independent
      |  ReplayRegistry (persistent, file-backed)  →  VALID / DUPLICATE / STALE / FUTURE
      |  verify_contract_provenance()              →  VERIFIED / TAMPERED
      |  RuntimeCore.execute()                     →  ACK:OK / HALT:*
      |
      |  multiprocessing.Queue  (q_exec_cons)
      |  { type: EXECUTION_RESULT, result: {...}, contract: {...}, producer_public_key: <hex> }
      v
[Consensus Process]         consensus_process.py         PID: independent
      |  ConsensusEngine (3 nodes, ECDSA P-256, 66% quorum)
      |
      |  multiprocessing.Queue  (q_cons_out)
      |  { type: CONSENSUS_PROOF, proof: {...} }
      v
[Orchestrator]              process_runner.py
      |  join(timeout=30), exitcode crash detection, q_cons_out.get(timeout=5)
```

The communication layer runs above this pipeline and uses the same gateway path for all producer types:

```
CommunicationRequest (QUANTUM | CLASSICAL | HYBRID)
      |
      v  CommunicationGateway.send()   (gateway.py)
      |  rate limit check → HALT:RATE_LIMIT_EXCEEDED
      |  resolve_translation_status(confidence)
      |      >= 0.70  → OK
      |      >= 0.40  → DEGRADED
      |      <  0.40  → REJECTED
      |  TranslationContract (payload_hash = SHA-256)
      |  Receiver.receive() → replay detection
      v
AcknowledgementContract → CommunicationResponse
```

No branching on `source_type` anywhere in `send()`.

---

## 3. Determinism Architecture (Phase 1)

Every field in every contract is classified into one of three categories:

| Category | Meaning | Participates in replay equality |
|----------|---------|--------------------------------|
| `DETERMINISTIC` | Identical for identical inputs regardless of wall clock | YES |
| `OBSERVABILITY` | Wall-clock timestamps, audit anchors | NO |
| `RUNTIME_ONLY` | Ephemeral execution metadata | NO |

### Deterministic Fields (communication layer)

| Field | Contract | Classification |
|-------|----------|---------------|
| `message_id` | CommunicationRequest | DETERMINISTIC |
| `payload_hash` | TranslationContract | DETERMINISTIC |
| `confidence` | CommunicationRequest | DETERMINISTIC |
| `translation_status` | TranslationContract | DETERMINISTIC |
| `transport_status` | AcknowledgementContract | DETERMINISTIC |
| `created_at` | TranslationContract | OBSERVABILITY |
| `issued_at` | AcknowledgementContract | OBSERVABILITY |
| `trace_timestamp` | Trace entries | OBSERVABILITY |

Full field registry: `determinism_doctrine.py`, `deterministic_replay.py`  
Doctrine document: `docs/timestamp_isolation_doctrine.md`

### Replay Comparison

```python
# Two contracts are replay-equivalent iff:
A.deterministic_projection() == B.deterministic_projection()

# Timestamps are recorded but never affect the verdict:
result.observability_diffs  # → {"issued_at": {"a": "T1", "b": "T2"}}
result.passed               # → True (timestamps differ, determinism holds)
```

20-run proof: all 20 runs produce identical deterministic hash `ccf224978a4e24cb...`  
Observability diffs (2 timestamp fields) differ across runs — this is correct and expected.

---

## 4. Durable Replay Enforcement (Phase 2)

### ReplayRegistry vs ReplayEnforcer

| | `ReplayEnforcer` (replay_enforcer.py) | `ReplayRegistry` (replay_registry.py) |
|--|---------------------------------------|---------------------------------------|
| Storage | In-memory (`dict`) | File-backed JSON (atomic writes) |
| Restarts | Lost on process restart | Survives restarts (load-on-start) |
| Decision states | ACCEPTED / REJECTED_DUPLICATE / REJECTED_STALE | VALID / DUPLICATE / STALE / FUTURE |
| Sequence tracking | Monotonic counter | Monotonic counter + ordering validation |
| Use case | In-process enforcement | Durable cross-restart enforcement |

### Decision States

| State | Trigger |
|-------|---------|
| `VALID` | New message, within TTL, sequence accepted |
| `DUPLICATE` | `message_id` already processed (in registry) |
| `STALE` | Message age > TTL (fires before duplicate check) |
| `FUTURE` | Sequence number gap exceeds `MAX_SEQUENCE_GAP` (1000) |

### Persistence Guarantees

- Writes use atomic `tmp → replace` to prevent partial state on crash.
- On restart: new `ReplayRegistry(path=...)` loads existing file, restores counter and all entries.
- Sequence numbering continues from where it left off — no gaps, no resets.
- Corrupted file: starts fresh (safe degradation).

---

## 5. Multi-Process Execution (Phase 3)

### IPC Transport

`multiprocessing.Queue` — rationale: shared memory, zero-dependency, survives the same OS lifecycle as the processes. Upgrade path: ZeroMQ / gRPC socket (documented in Known Limitations).

### Message Schema

```json
// Producer → Execution
{
  "type": "CONTRACT",
  "contract": { "...ComputationExecutionContract fields..." },
  "producer_public_key": "<hex DER>",
  "issued_at": 1718000000.0
}

// Execution → Consensus
{
  "type": "EXECUTION_RESULT",
  "result": { "...ExecutionResult fields..." },
  "contract": { "...original signed contract..." },
  "producer_public_key": "<hex DER>",
  "issued_at": 1718000001.0
}
```

### Structured Log Schema

Every log entry from all three processes contains these mandatory fields:

```json
{
  "process_id":      12345,
  "role":            "EXECUTION",
  "event":           "executed",
  "message_id":      "proc-trace-001",
  "sequence_number": 1,
  "status":          "ACK:OK",
  "timestamp":       "2026-06-11T11:00:00Z"
}
```

Log files: `logs/process_1.log` (producer), `logs/process_2.log` (execution), `logs/process_3.log` (consensus).

### Crash Recovery

The `ReplayRegistry` (file-backed) is the crash recovery mechanism:

1. Execution process crashes mid-run.
2. Registry file already written to disk (atomic write on every VALID acceptance).
3. Execution process restarts → `ReplayRegistry(path=...)` loads from file.
4. Already-processed `message_id` values are rejected as `DUPLICATE`.
5. New messages accepted with sequence continuing from the last persisted counter.

Proof: `crash_recovery_proof.py` — 5 cases, all PASS.

---

## 6. Cryptography

All signatures use **ECDSA P-256 (secp256r1)** via the `cryptography` package.

| Operation | Algorithm | Location |
|-----------|-----------|----------|
| Key generation | ECDSA P-256, fresh per NodeSigner | `node_identity.NodeSigner.__init__` |
| Signing | `ec.ECDSA(hashes.SHA256())` | `NodeSigner.sign_payload` |
| Verification | Standard ECDSA verify, public key only | `verify_node_proof` |
| Public key format | DER SubjectPublicKeyInfo, hex | `NodeIdentity.public_key` |
| Signature format | DER-encoded ECDSA, hex | `NodeProof.signature` |

Private key never leaves the `NodeSigner` instance.

---

## 7. File Map

### Execution Hardening (this sprint)

| File | Purpose |
|------|---------|
| `deterministic_replay.py` | `ReplayContract`, `ReplayComparator`, `DeterministicComparisonResult` — field-level determinism comparison. |
| `replay_registry.py` | Persistent file-backed replay registry. VALID / DUPLICATE / STALE / FUTURE. Atomic writes. Restart survival. |
| `determinism_20_run_proof.py` | 20-run consistency proof — same deterministic hash across all runs. |
| `replay_enforcement_proof.py` | 6-case durable replay proof including restart persistence. |
| `crash_recovery_proof.py` | 5-case crash recovery proof + real OS process isolation proof. |
| `docs/timestamp_isolation_doctrine.md` | Formal doctrine: why timestamps are excluded, which fields are ignored, how comparison works. |

### Communication Layer

| File | Purpose |
|------|---------|
| `communication_contract.py` | `CommunicationRequest`, `TranslationContract`, `AcknowledgementContract`, `CommunicationResponse`. All `frozen=True`. |
| `gateway.py` | `CommunicationGateway`, `QuantumProducer`, `ClassicalProducer`, `HybridProducer`, `Receiver`, `_RateLimiter`. |
| `simulation.py` | All 4 cross-system paths (Q→C, C→Q, H→C, H→Q). |
| `docs/communication_taxonomy.md` | 9 communication participants, 7-hop message lifecycle. |
| `docs/failure_doctrine.md` | 6 failure types — detection, response, recovery posture. |
| `docs/communication_lineage.md` | Field-level lineage from creation to acknowledgement. |

### Execution Pipeline

| File | Purpose |
|------|---------|
| `producer_process.py` | Independent OS process: produces signed contract, puts on queue. |
| `execution_process.py` | Independent OS process: replay enforcement + provenance check + runtime execution. |
| `consensus_process.py` | Independent OS process: 3-node ECDSA consensus. |
| `process_runner.py` | Orchestrator: spawns 3 processes, crash detection, structured summary. |
| `replay_enforcer.py` | In-memory replay enforcer (sequence_id + TTL). |

### Runtime / Adapter Layer

| File | Purpose |
|------|---------|
| `adapters.py` | `QuantumAdapter`, `ClassicalAdapter`, `HybridAdapter`. |
| `execution_contract.py` | `ComputationExecutionContract` — canonical frozen contract, payload_hash, field classifications. |
| `runtime_core.py` | Blind execution engine. Confidence thresholds, replay detection, runtime hash. |
| `governance.py` | Pre-execution policy: producer type auth, version enforcement. |
| `determinism_doctrine.py` | `DeterminismOracle` — DETERMINISTIC vs OBSERVABILITY classification. |

### Trust Layer

| File | Purpose |
|------|---------|
| `node_identity.py` | `NodeIdentity`, `NodeSigner` — ECDSA P-256 signatures. |
| `provenance.py` | `verify_contract_provenance()` — VERIFIED / UNVERIFIED / TAMPERED. |
| `consensus_simulation.py` | `ConsensusEngine` — 2/3 quorum, signed `NodeAttestation` per node. |
| `replay_bundle.py` | `ReplayBundle` — 5-check verification. |
| `audit_trail.py` | `MerkleAuditTrail` — tamper-evident append-only log. |
| `trust_chain.py` | `NodeRegistry` + `TrustChain` — chain-of-custody. |

---

## 8. Failure Cases

All failures return a structured response. No component raises to its caller.

| Failure | Trigger | Response |
|---------|---------|---------|
| Rate limit exceeded | Token bucket exhausted | `HALT:RATE_LIMIT_EXCEEDED` |
| Low confidence | confidence < `CORRUPTION_THRESHOLD` (0.40) | `HALT:TRANSLATION_REJECTED:confidence=X` |
| Replay detected (gateway) | Duplicate `message_id` in `Receiver._seen` | `HALT:REPLAY_DETECTED` |
| Replay detected (runtime) | Duplicate `trace_id` in `RuntimeCore._replay_registry` | `HALT:REPLAY_DETECTED` |
| Duplicate (durable) | `message_id` in `ReplayRegistry` file | `HALT:DUPLICATE` |
| Stale message | age > `QCG_REPLAY_TTL_SECONDS` (300s) | `HALT:STALE` |
| Degraded signal | confidence in [0.40, 0.70) | `ACK:DEGRADED:confidence=X` |
| Provenance failure | ECDSA signature tampered | `HALT:PROVENANCE_FAILED:TAMPERED` |
| Invalid contract schema | Missing fields / bad version | `HALT:INVALID_CONTRACT:*` |
| Process crash | `exitcode != 0` | `crashes` dict in pipeline summary |
| Byzantine node | Node hash diverges from majority | Isolated in `disagreements`, quorum still reached if 2/3 honest |
| Forged trust chain link | Sender not in `NodeRegistry` | `verify_chain → passed=False` |
| Audit tamper | `entry_hash` mismatch | `verify_integrity → passed=False` |

---

## 9. Proof Evidence

| Claim | Proof | How to verify |
|-------|-------|--------------|
| 20 runs produce identical deterministic hash | `determinism_20_run_proof.py` | `python determinism_20_run_proof.py` → PASS |
| Timestamps excluded from determinism | `docs/timestamp_isolation_doctrine.md`, `TestReplayComparator::test_timestamp_diff_does_not_fail` | `pytest -k test_timestamp_diff` |
| Duplicate rejection | `TestReplayRegistry::test_duplicate_rejected` | `pytest -k test_duplicate_rejected` |
| Stale rejection fires before duplicate | `TestReplayRegistry::test_stale_beats_duplicate` | `pytest -k test_stale_beats_duplicate` |
| Registry survives process restart | `TestReplayRegistryPersistence::test_survives_restart` | `pytest -k test_survives_restart` |
| Atomic write (no partial state) | `TestReplayRegistryPersistence::test_atomic_write_no_partial_state` | `pytest -k test_atomic_write` |
| Crash recovery: registry loaded, duplicates blocked | `crash_recovery_proof.py` | `python crash_recovery_proof.py` → PASS |
| 3 independent OS processes (distinct PIDs) | `TestProcessIsolation::test_distinct_pids` | `pytest -k test_distinct_pids` |
| Process PIDs distinct in logs | `TestStructuredLogs::test_process_ids_are_distinct_across_logs` | `pytest -k test_process_ids_are_distinct` |
| Structured log fields present | `TestStructuredLogs::test_process_2_log_has_required_fields` | `pytest -k test_process_2_log` |
| Concurrent replay: exactly one VALID | `TestConcurrentReplay::test_concurrent_duplicate_only_one_valid` | `pytest -k test_concurrent_duplicate` |
| All 4 cross-system paths, same gateway | `TestCrossSystemPaths::test_all_paths_same_gateway_method` | `pytest -k test_all_paths` |
| ECDSA signatures, not HMAC | `node_identity.py` — `ec.ECDSA(hashes.SHA256())` | code inspection |
| Producer crash detected | `TestIPCTopology::test_crash_producer_detected` | `pytest -k test_crash_producer` |
| Governance never touches runtime authority | `governance_authority.py` — `validate_authority_boundaries()` | `python governance_authority.py` |

---

## 10. Test Coverage

```
tests/test_all.py                127 tests   (all phases, core pipeline, hardening, Phase 3)
tests/test_adapter_layer.py       74 tests   (adapter, governance, runtime, distributed)
tests/test_communication_layer.py 74 tests   (communication contract, gateway, producers)
                                 ─────────
Total                             275 tests, 0 failures
```

### New test classes (this sprint)

| Class | Tests | What it covers |
|-------|-------|---------------|
| `TestReplayContract` | 5 | Field extraction, projection, hash stability, immutability |
| `TestReplayComparator` | 6 | Timestamp diffs don't fail, deterministic diffs do, compare_many |
| `TestDeterministicComparisonResult` | 2 | `is_deterministic` property, failed result |
| `TestDeterminism20RunProof` | 4 | 20-run proof, hash identity, no mismatched fields |
| `TestReplayRegistry` | 14 | All 4 states, sequence, thread safety, entry management |
| `TestReplayRegistryPersistence` | 4 | Restart survival, duplicate-after-restart, corrupt file, atomic write |
| `TestReplayEnforcementProof` | 2 | Full 6-case proof, all cases |
| `TestCrashRecoveryProof` | 7 | All 5 crash recovery cases individually |
| `TestProcessIsolation` | 4 | Distinct PIDs, no cross-registry contamination |
| `TestConcurrentReplay` | 3 | 20-thread unique, 8-thread duplicate, enforcer concurrent |
| `TestStructuredLogs` | 4 | Required fields, process_id type, distinct PIDs across logs |
| `TestIPCTopology` | 6 | Clean pipeline, consensus result, 3 crash stages, distinct PIDs |

---

## 11. Production Readiness

| Concern | Status | Detail |
|---------|--------|--------|
| Deterministic field classification | PASS | `DETERMINISTIC_FIELDS` / `OBSERVABILITY_FIELDS` explicitly declared in `deterministic_replay.py` |
| Timestamp isolation | PASS | Observability fields never participate in replay equality — see `docs/timestamp_isolation_doctrine.md` |
| Replay persistence | PASS | `ReplayRegistry` file-backed, atomic writes, load-on-start |
| Crash recovery | PASS | Registry survives crash; duplicates blocked on restart; sequence continues |
| Process isolation | PASS | 3 independent OS processes with distinct PIDs verified in tests |
| Structured logs | PASS | All log entries contain `process_id`, `message_id`, `sequence_number`, `status`, `timestamp` |
| Thread safety | PASS | `ReplayRegistry` and `ReplayEnforcer` both use `threading.Lock`; concurrent tests validate |
| Bounded memory | PASS | `Receiver._seen` capped at 100,000; `ReplayEnforcer` evicts on overflow |
| Rate limiting | PASS | Token-bucket `_RateLimiter`, configurable via `QCG_RATE_LIMIT_PER_MINUTE` |
| ECDSA signatures | PASS | P-256 via `cryptography` package; private key never leaves `NodeSigner` |
| Immutable contracts | PASS | All contract dataclasses `frozen=True` |
| Config-driven thresholds | PASS | All constants in `config.py`, env-overridable via `.env` |
| Never raises to caller | PASS | `CommunicationGateway.send()` catches all exceptions |

---

## 12. Known Limitations

| Limitation | Impact | Mitigation path |
|-----------|--------|----------------|
| IPC transport is `multiprocessing.Queue` (shared memory) | Not a real network socket; processes must share OS | Replace with ZeroMQ / gRPC for true distributed deployment |
| `NodeRegistry` is in-memory | Lost on restart; no certificate rotation or revocation | Persistent store with TTL-based expiry |
| `ReplayRegistry` uses wall-clock `time.time()` for TTL | Subject to system clock skew between producer and enforcement point | Signed timestamps from a trusted time authority |
| Consensus nodes share OS process memory | Logically independent but not network-separated | Real transport between node processes |
| `MerkleAuditTrail` rebuilds on every append | Not suitable for high-throughput | Persistent incremental tree backend |
| `ReplayEnforcer` eviction is insert-triggered | Brief overage possible before eviction fires | Background sweeper thread |
| `issued_at` is producer-reported | Producer could forge recency | Countersign `issued_at` at gateway boundary |

---

## 13. Remaining Risks

| Risk | Severity | Status |
|------|----------|--------|
| Cross-process replay coordination | HIGH | `ReplayRegistry` is per-process file. Two execution processes on the same file would race. Single-process deployment is safe. Multi-instance requires shared lock or distributed cache. |
| Clock skew for TTL enforcement | MEDIUM | `issued_at` converted from wall-clock. Skew > TTL could incorrectly stale-reject valid messages. |
| Registry file corruption under concurrent writers | LOW | Atomic `tmp → replace` prevents partial reads but not concurrent write races if two processes target the same file. |

---

## 14. Deliverable Map

| Phase | Deliverable | File | Status |
|-------|------------|------|--------|
| 1 — Determinism Hardening | Field classification | `deterministic_replay.py` | DONE |
| 1 — Determinism Hardening | Timestamp isolation doctrine | `docs/timestamp_isolation_doctrine.md` | DONE |
| 1 — Determinism Hardening | 20-run consistency proof | `determinism_20_run_proof.py` | DONE |
| 2 — Durable Replay | Persistent registry | `replay_registry.py` | DONE |
| 2 — Durable Replay | Sequence tracking + 4 states | `replay_registry.py` | DONE |
| 2 — Durable Replay | Enforcement proof | `replay_enforcement_proof.py` | DONE |
| 3 — Multi-Process | Three independent processes | `producer_process.py`, `execution_process.py`, `consensus_process.py` | DONE |
| 3 — Multi-Process | IPC topology | `multiprocessing.Queue`, documented in ARCHITECTURE.md | DONE |
| 3 — Multi-Process | Crash recovery proof | `crash_recovery_proof.py` | DONE |
| 3 — Multi-Process | Structured execution logs | all process files updated | DONE |
| Comm. Layer | Contract schemas | `communication_contract.py` | DONE |
| Comm. Layer | Translation gateway | `gateway.py` | DONE |
| Comm. Layer | Cross-system simulation | `simulation.py` | DONE |
| Trust Layer | ECDSA identity + provenance | `node_identity.py`, `provenance.py` | DONE |
| Trust Layer | Consensus + audit trail | `consensus_simulation.py`, `audit_trail.py` | DONE |
| Trust Layer | Trust chain + replay bundle | `trust_chain.py`, `replay_bundle.py` | DONE |
| Testing | Full test suite | `tests/` | 251 tests, 0 failures |
