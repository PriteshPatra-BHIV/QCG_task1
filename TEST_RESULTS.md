# TEST_RESULTS.md

> Production Hardening Sprint — Evidence Record
> Run: 213 passed, 0 failed

```
platform win32 — Python 3.13.13, pytest-9.0.2
213 passed in 2.20s
```

---

## Determinism Tests

| Test | Status | Evidence |
|------|--------|----------|
| 20 consecutive runs identical (seed=42, noise=0.12) | PASS | `TestDeterminism20Run::test_20_runs_identical` |
| Timestamp mutation detected as observability diff | PASS | `test_failure_injection_timestamp_detected` |
| Payload mutation detected (hash changes) | PASS | `test_failure_injection_payload_mutation_detected` |
| Ordering mutation neutralised by `sort_keys=True` | PASS | `test_failure_injection_ordering_neutralised` |
| 5-run identical (legacy baseline) | PASS | `TestDeterminismProof::test_five_runs_identical` |
| Same seed produces identical counts | PASS | `test_same_seed_same_counts` |
| trace_id stable across 5 runs | PASS | `test_contract_trace_id_stable_across_runs` |

---

## Replay Tests

| Test | Expected | Status |
|------|----------|--------|
| New artifact submitted | `ACCEPTED`, seq=1 | PASS |
| Same artifact submitted twice | `REJECTED_DUPLICATE` | PASS |
| Artifact with `issued_at` 10s ago, TTL=1s | `REJECTED_STALE` | PASS |
| Sequence numbers are monotonically increasing | 1,2,3,4,5 | PASS |
| Stale check fires before duplicate check | `REJECTED_STALE` not `ACCEPTED` | PASS |
| Runtime replay guard (same trace_id second call) | `HALT:REPLAY_DETECTED` | PASS |
| Replay registry reset allows re-transmission | ACK without REPLAY | PASS |

---

## Process Tests

| Test | Status | Note |
|------|--------|------|
| Three independent OS processes | PASS | Distinct PIDs in `logs/process_*.log` |
| Producer crash simulation | PASS | `process_runner.py --crash producer` → `exitcode=1` |
| Execution crash simulation | PASS | `process_runner.py --crash execution` |
| Consensus crash simulation | PASS | `process_runner.py --crash consensus` |
| Normal pipeline end-to-end | PASS | `pipeline_ok=True`, consensus 100% |
| Concurrent replay guard (2 threads) | PASS | `TestFailureProof::test_concurrent_replay_guard` |

---

## Trust Tests

| Test | Expected | Status |
|------|----------|--------|
| Valid ECDSA trust chain (3 nodes, all registered) | `passed=True, errors=[]` | PASS |
| Forged ECDSA signature (unregistered node) | `passed=False, "not registered"` | PASS |

---

## Audit Tests

| Test | Expected | Status |
|------|----------|--------|
| Entry #2 Merkle inclusion proof | `verify_inclusion=True` | PASS |
| Tampered entry at index 1 | `verify_integrity=False` | PASS |

---

## Consensus Tests

| Test | Network | Expected | Status |
|------|---------|----------|--------|
| Honest network (3 nodes, ECDSA attestations) | All honest | `reached=True, 100%` | PASS |
| Faulty node (`CN_1` hash poisoned) | 1 faulty | `reached=True, CN_1 in disagreements` | PASS |
| Stale/missing node (`CN_2` absent) | 1 missing | `reached=True` (2/3 = 66%) | PASS |
| Spoofed node (`SN_0` faulty hash) | 1 spoofed | `reached=True, SN_0 in disagreements` | PASS |

---

## Full Suite Breakdown

| Suite | Tests | Status |
|-------|-------|--------|
| `tests/test_all.py::TestTransmissionRequest` | 10 | ALL PASS |
| `tests/test_all.py::TestConfigValidation` | 2 | ALL PASS |
| `tests/test_all.py::TestQuantumProducer` | 8 | ALL PASS |
| `tests/test_all.py::TestTranslationLayer` | 8 | ALL PASS |
| `tests/test_all.py::TestGatewayPipeline` | 9 | ALL PASS |
| `tests/test_all.py::TestFailureProof` | 7 | ALL PASS |
| `tests/test_all.py::TestDeterminismProof` | 4 | ALL PASS |
| `tests/test_all.py::TestDeterminism20Run` | 4 | ALL PASS |
| `tests/test_all.py::TestReplayEnforcer` | 5 | ALL PASS |
| `tests/test_all.py::TestTrustChain` | 2 | ALL PASS |
| `tests/test_all.py::TestAuditTrail` | 2 | ALL PASS |
| `tests/test_all.py::TestConsensus` | 4 | ALL PASS |
| `tests/test_adapter_layer.py` | 74 | ALL PASS |
| `tests/test_communication_layer.py` | 74 | ALL PASS |
| **Total** | **213** | **213 PASS / 0 FAIL** |
