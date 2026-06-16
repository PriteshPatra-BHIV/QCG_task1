 # Replay Doctrine

> Canonical replay semantics for the QCG hybrid runtime.

---

## What exactly is being replayed?

Replay is the **re-execution of a previously-observed pipeline segment** to verify that it produces deterministically identical results. Replay is **verification**, not re-processing. The goal is to prove reproducibility, not to generate new results.

Each replay target re-runs a specific scope of the pipeline and compares the deterministic projection of the output (timestamps excluded) against the original.

---

## Replay Target Taxonomy

### 1. Payload Replay

| Dimension | Value |
|-----------|-------|
| **What is replayed** | The raw producer output through the same adapter |
| **What it proves** | Adapter determinism — same raw input always produces the same contract |
| **Scope** | Adapter layer (`QuantumAdapter`, `ClassicalAdapter`, `HybridAdapter`) |
| **Method** | `ReplayEngine.replay_payload(raw_input, adapter, message)` |
| **Comparison** | `DeterminismOracle.assert_contract_determinism()` — deterministic projection only |
| **Timestamps** | Excluded from comparison (observability metadata) |

**What exactly is being replayed?** The transformation from raw producer output to `ComputationExecutionContract`. The same `QuantumDistribution` or classical output dict is passed through the same adapter twice. Both resulting contracts must have identical deterministic fields.

---

### 2. Contract Replay

| Dimension | Value |
|-----------|-------|
| **What is replayed** | The same `ComputationExecutionContract` through `RuntimeCore.execute()` |
| **What it proves** | Runtime determinism — same contract always produces the same `ExecutionResult` |
| **Scope** | `RuntimeCore.execute()` |
| **Method** | `ReplayEngine.replay_contract(contract, runtime)` |
| **Comparison** | `DeterminismOracle.assert_execution_determinism()` — deterministic projection only |
| **Caveat** | Two separate `RuntimeCore` instances must be used because the replay guard prevents duplicate `trace_id` execution on the same instance |

**What exactly is being replayed?** The contract's journey through the blind runtime. The same frozen contract is passed to two independent RuntimeCore instances. Both must produce identical ACKs, confidence values, and runtime hashes.

---

### 3. Execution Replay

| Dimension | Value |
|-----------|-------|
| **What is replayed** | The same contract through the full governance + runtime pipeline |
| **What it proves** | Governance + runtime determinism — policy enforcement and execution are both reproducible |
| **Scope** | `GovernanceLayer.enforce()` → `RuntimeCore.execute()` |
| **Method** | `ReplayEngine.replay_execution(contract, governance_layer_factory)` |
| **Comparison** | Deterministic projection of `ExecutionResult` + violation type list |

**What exactly is being replayed?** The full pre-execution policy check (producer authorization, version enforcement, schema validation) followed by blind execution. Both the execution result and the governance violation list must be deterministically identical.

---

### 4. Trace Replay

| Dimension | Value |
|-----------|-------|
| **What is replayed** | Two execution results are compared for semantic equivalence |
| **What it proves** | Meaning preservation — the ACK outcome category and confidence band are preserved even if observability timestamps differ |
| **Scope** | `ExecutionResult` comparison |
| **Method** | `ReplayEngine.replay_trace(result_a, result_b)` |
| **Comparison** | ACK prefix match, confidence band match, producer type match |

**What exactly is being replayed?** The *meaning* of two results is compared. This is weaker than exact deterministic match — it verifies semantic equivalence. Two results are trace-equivalent if they have the same ACK category (OK/DEGRADED/HALT), the same confidence band, and the same producer type, even if their exact confidence values or timestamps differ.

---

### 5. Distributed Replay

| Dimension | Value |
|-----------|-------|
| **What is replayed** | The same contract through N independent node instances |
| **What it proves** | Multi-node determinism — independent runtime instances produce identical results |
| **Scope** | N × (`GovernanceLayer` + `RuntimeCore`) |
| **Method** | `ReplayEngine.replay_distributed(contract, node_count)` |
| **Comparison** | All N results must have identical deterministic projections |
| **Limitation** | Currently simulation-level only (single process). Does NOT prove real distributed determinism. |

**What exactly is being replayed?** The same contract is processed by N independent governance+runtime instances. All N must produce identical ACKs, confidence values, and runtime hashes. This proves that the code path is deterministic across instances, but does NOT prove network-level agreement (no real networking exists).

---

## Replay Guarantees and Limitations

| Guarantee | Status |
|-----------|--------|
| Payload replay proves adapter determinism | ✅ Proven |
| Contract replay proves runtime determinism | ✅ Proven |
| Execution replay proves governance+runtime determinism | ✅ Proven |
| Trace replay proves semantic equivalence | ✅ Proven |
| Distributed replay proves multi-node simulation determinism | ✅ Proven (simulation only) |
| Distributed replay proves real network determinism | ❌ NOT proven |

---

*Source of truth: `replay_doctrine.py` (code), this document (specification).*
