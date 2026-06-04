# Distributed Assumptions

> What the distributed simulation proves, what it does NOT prove, and its limitations.

---

## What Simulation Proves

1. **Deterministic hash agreement** — N simulated nodes processing the same contract sequence produce identical hash-chain ledgers.
2. **Execution determinism across instances** — Independent `RuntimeCore` + `GovernanceLayer` instances produce identical `ExecutionResult` deterministic projections for the same input.
3. **Ordered propagation consistency** — Contracts propagated in the same order to all nodes produce the same ledger state.
4. **Governance consistency** — All nodes apply the same governance policies and produce the same violation lists.

---

## What Simulation Does NOT Prove

1. **Network partition tolerance** — No network exists. All nodes run in the same process.
2. **Byzantine fault tolerance** — No adversarial nodes. All nodes execute the same code honestly.
3. **Consensus protocol correctness** — No consensus protocol exists. Contracts are simply passed to each node in order.
4. **Clock synchronization** — All nodes share the same system clock. No clock skew or drift.
5. **Message delivery guarantees** — No messages are sent. Contracts are directly passed as function arguments.
6. **Real inter-node communication** — No sockets, no RPC, no message queues. Everything is in-process method calls.
7. **Execution correctness** — Deterministic agreement does not mean the results are correct — only that all nodes agree on the same (potentially incorrect) result.

---

## Single-Process Limitations

- All nodes share the same Python interpreter, GIL, memory space, and PRNG state.
- No concurrency hazards from real network I/O.
- No serialization/deserialization of contracts (they are passed by reference).
- No latency, jitter, or packet loss.
- Failure modes (node crash, timeout, partial execution) are not simulated.

---

## Network Absence

The system has **zero networking capability**:

| Capability | Status |
|-----------|--------|
| TCP/UDP sockets | Not implemented |
| gRPC / REST APIs | Not implemented |
| Message queues (Kafka, RabbitMQ) | Not implemented |
| Peer discovery | Not implemented |
| Heartbeat / health checks between nodes | Not implemented |

The `SimulatedNode` class is a single-process wrapper around `RuntimeCore` + `GovernanceLayer` + `TraceStore`. The word "node" refers to an independent execution context, not a network endpoint.

---

## Trust Assumptions

1. **All nodes are honest** — No node will forge, alter, or withhold results.
2. **All nodes execute the same code** — No version skew between nodes.
3. **All nodes receive contracts in the same order** — No reordering, duplication, or loss.
4. **The simulation runner is trusted** — `DistributedSimulation.run()` orchestrates propagation without interference.
5. **The Python runtime is deterministic** — Given the same seed, Qiskit Aer produces the same results across runs.

---

## Hash Agreement Meaning

**What `hash_agreement = True` means:**
All N nodes computed the same SHA-256 hash chain from the same contract sequence. This proves that:
- The same contracts were processed.
- The same ACKs were generated.
- The same runtime hashes were computed.
- The ledger state is identical across all nodes.

**What `hash_agreement = True` does NOT mean:**
- The results are correct (only that all nodes agree).
- The system would behave the same over a real network.
- The system is Byzantine-fault-tolerant.
- The system handles node failures gracefully.

---

## Classification

| Dimension | Value |
|-----------|-------|
| Type | Simulation-level verification |
| Scope | Single process, ordered propagation |
| Status | Pre-requisite for distributed execution readiness |
| Equivalence | NOT equivalent to distributed execution readiness |

---

*Source of truth: `distributed_simulation.py` SCOPE DECLARATION.*
