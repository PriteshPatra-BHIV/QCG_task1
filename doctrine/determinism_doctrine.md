# Determinism Doctrine

> Formal classification of determinism guarantees in the QCG hybrid runtime.

---

## Required Distinction

> **Quantum behavior determinism ≠ contract determinism.**
> The quantum simulator's output (QuantumDistribution) is deterministic given a seed.
> But that is PRNG determinism, not physical quantum determinism.
> Contract determinism means the *adapter output envelope* is identical for identical input — independent of whether the producer is quantum or classical.

> **Observability determinism ≠ execution correctness.**
> Reproducible trace hashes prove the *same execution path was taken*.
> They do NOT prove the execution result is *correct* — only that it is *consistently reproducible*.

---

## Category 1: Execution Determinism

| Dimension | Value |
|-----------|-------|
| **Definition** | `RuntimeCore.execute()` produces identical deterministic-projection outputs (ack, runtime_hash, confidence, contract_trace_id, producer_type) for identical contract inputs. `execution_timestamp` is excluded — it is observability metadata. |
| **Scope** | `RuntimeCore.execute()` in `runtime_core.py` |
| **Owner** | `RuntimeCore` |
| **Proof expectation** | `python determinism_proof.py` — same seed + same message → identical deterministic projections across N runs. Uses `DeterminismOracle.extract_deterministic_projection()` to exclude timestamps. |
| **Known limitations** | Replay guard (trace_id registry) prevents re-execution of the same trace_id on the same RuntimeCore instance. Two separate RuntimeCore instances must be used for comparison. Execution determinism does not imply correctness — only reproducibility. |

---

## Category 2: Contract Determinism

| Dimension | Value |
|-----------|-------|
| **Definition** | Adapter output (`ComputationExecutionContract`) is identical for identical raw producer input. Deterministic fields: `payload_hash`, `trace_id`, `confidence`, `payload`, `producer_type`, `contract_version`, `execution_constraints`. The `timestamp` field is observability-only and excluded from deterministic comparison. |
| **Scope** | `QuantumAdapter.adapt()`, `ClassicalAdapter.adapt()`, `HybridAdapter.adapt()` in `adapters.py` |
| **Owner** | Adapter layer |
| **Proof expectation** | `DeterminismOracle.assert_contract_determinism()` compares two contracts produced from the same input, ignoring timestamp. `ReplayEngine.replay_payload()` runs this check. |
| **Known limitations** | Depends on seed determinism of the quantum simulator (Qiskit Aer). Different seeds produce different distributions, therefore different contracts. Contract determinism is *conditional* on input determinism. |

---

## Category 3: Observability Determinism

| Dimension | Value |
|-----------|-------|
| **Definition** | Trace entry hashes and replay chain reconstructions are reproducible given the same inputs. `TraceEntry.entry_hash` is computed from `trace_id`, `trace_type`, `data`, and `timestamp`. Since timestamps are included in hash computation, observability determinism is anchored in wall-clock time. |
| **Scope** | `TraceStore` in `observability.py` |
| **Owner** | Observability layer (`TraceStore`) |
| **Proof expectation** | `TraceStore.reconstruct_replay()` verifies hash chain integrity by recomputing each entry's hash and comparing. Ordering uses deterministic sequence numbers, not timestamps. |
| **Known limitations** | `entry_hash` includes `timestamp`, so two independent recordings of the same execution will produce different entry hashes (different wall-clock times). This is by design — observability anchors in time. Observability determinism proves *"the same trace was recorded"*, not *"the execution was correct"*. |

---

## Category 4: Simulation Determinism

| Dimension | Value |
|-----------|-------|
| **Definition** | Simulated distributed nodes, running in a single process, produce identical execution results and identical hash-chain ledgers when processing the same contract sequence in the same order. |
| **Scope** | `DistributedSimulation` in `distributed_simulation.py` |
| **Owner** | `DistributedSimulation` / `SimulatedNode` |
| **Proof expectation** | `DistributedSimulation.run()` returns `DistributedProof` with `hash_agreement=True` and `passed=True`. All N nodes must have identical ledgers. |
| **Known limitations** | Single-process only. All nodes share the same memory space, clock, and Python interpreter. No network latency, no message loss, no Byzantine faults, no clock skew. Simulation determinism is a **pre-requisite** for distributed determinism, not a **substitute** for it. |

---

## Category 5: Distributed Determinism

| Dimension | Value |
|-----------|-------|
| **Definition** | Independent nodes, running in separate processes or machines with real network communication, would produce identical deterministic-projection outputs for the same contract input. |
| **Scope** | Not yet implemented. Theoretical target. |
| **Owner** | N/A (future distributed runtime) |
| **Proof expectation** | Not proven. Would require: multi-process execution, real network transport, consensus protocol, clock synchronization, Byzantine fault handling. |
| **Known limitations** | **Not proven by this system.** The current `DistributedSimulation` proves simulation determinism (Category 4) only. Distributed determinism requires network partition tolerance, consensus protocol correctness, and clock synchronization — none of which are implemented. Any claim of "distributed execution readiness" is premature. |

---

## Determinism Hierarchy

```
Distributed Determinism        ← NOT PROVEN (requires real networking)
        ↑ requires
Simulation Determinism         ← PROVEN (single-process, hash agreement)
        ↑ requires
Execution Determinism          ← PROVEN (same input → same output)
        ↑ requires
Contract Determinism           ← PROVEN (same raw input → same contract)
        ↑ requires
Seed / Input Determinism       ← BY DESIGN (Qiskit Aer seed parameter)
```

Each level requires the one below it. Failure at any level invalidates all levels above it.

---

*Source of truth: `determinism_doctrine.py` (code), this document (specification).*
