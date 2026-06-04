# Semantic Registry — Canonical Terms

> If a term is not here, it is not a first-class concept in the system.

---

## contract

**Definition:** A frozen, schema-validated envelope carrying opaque producer output through a uniform execution pipeline. A contract is a data structure (`ComputationExecutionContract`), not a legal agreement or bilateral promise. It is immutable after creation.

**Scope:** `execution_contract.py`, `adapters.py`, `runtime_core.py`, `governance.py`

**Distinguished from:**
- Legal contract — no bilateral agreement or enforcement exists
- Promise — a contract does not guarantee outcome, only structure
- Message — a contract wraps a message but is not the message itself

---

## replay

**Definition:** Re-execution of a previously-observed contract or pipeline segment to verify deterministic reproducibility. Five canonical replay targets exist: PAYLOAD (adapter determinism), CONTRACT (runtime determinism), EXECUTION (governance+runtime determinism), TRACE (meaning equivalence), DISTRIBUTED (multi-node determinism). Replay is verification, not re-processing.

**Scope:** `replay_doctrine.py`, `observability.py`, `runtime_core.py`

**Distinguished from:**
- Replay attack — malicious re-submission; detected by trace_id registry
- Retry — re-attempt after failure; replay is re-verification of success
- Idempotency — replay verifies determinism; idempotency prevents side effects

---

## confidence

**Definition:** The ratio of dominant measurement outcomes to total shots in a quantum distribution. Range `[0.0, 1.0]`. A confidence of `0.93` means 93% of the 1024 simulated shots landed on the dominant bitstring. This is a statistical frequency ratio, NOT a probability of correctness.

**Scope:** `translation_layer.py`, `runtime_core.py`, `governance.py`

**Thresholds:**

| Threshold | Value | Effect |
|-----------|-------|--------|
| `CONFIDENCE_THRESHOLD` | 0.70 | Below this: `ACK:DEGRADED` |
| `CORRUPTION_THRESHOLD` | 0.40 | Below this: `HALT:LOW_CONFIDENCE` |

**Distinguished from:**
- Probability of correctness — measures signal dominance, not whether the answer is "right"
- Certainty — the system never claims certainty
- Truth — confidence is a measurement statistic, not a truth claim

---

## truth

**Definition:** NOT USED in this system. The system operates on *confidence* (statistical measure) and *determinism* (reproducibility guarantee), not truth claims. No component asserts that a result is "true" — only that it is reproducible and above a confidence threshold.

**Scope:** N/A — deliberately excluded from the system vocabulary

**Distinguished from:**
- Confidence — a statistical ratio, not a truth value
- Determinism — reproducibility of output, not correctness of output
- Correctness — not claimed; only fidelity to protocol is verified

---

## governance

**Definition:** Policy enforcement layer that gates contract execution without modifying contract content or bypassing runtime logic. Governance owns pre-execution policy (producer authorization, version enforcement, schema validation) and post-execution observation (recording violations from RuntimeCore results). Governance does NOT own confidence thresholds, replay detection, or ACK generation.

**Scope:** `governance.py`, `governance_authority.py`

**Distinguished from:**
- Runtime execution — governance gates execution, does not perform it
- Validation — governance delegates schema validation to `validate_contract()`
- Administration — governance is automated policy, not human oversight

---

## execution

**Definition:** The act of processing a `ComputationExecutionContract` through `RuntimeCore.execute()`. Produces an `ExecutionResult` containing an ACK string, runtime hash, confidence, and timestamp. Execution is blind to producer type — quantum and classical contracts traverse the exact same code path with no branching.

**Scope:** `runtime_core.py`

**Distinguished from:**
- Governance — governance gates execution but does not perform it
- Adaptation — adapters create contracts; execution consumes them
- Observation — trace recording happens after execution, not during it

---

## authority

**Definition:** The explicit set of responsibilities a component controls (`authority_owned`) versus delegates (`authority_not_owned`). Every policy-enforcing component declares its authority boundary including a ceiling (maximum scope) and negative authority (things it is prohibited from doing). Authority is structural and peer-based, not hierarchical.

**Scope:** `governance_authority.py`

**Distinguished from:**
- Hierarchy — authority is peer-based, not parent-child
- Control — authority means responsibility, not absolute control
- Permission — authority declares what a component does, not what it may do

---

## hybrid

**Definition:** A merged contract produced by combining one QUANTUM and one CLASSICAL contract via confidence-weighted selection. The merge strategy, not the execution path, is what makes it hybrid. Once merged, a HYBRID contract traverses the same `RuntimeCore.execute()` code path as any other contract — no special hybrid execution exists.

**Scope:** `adapters.py` (HybridAdapter)

**Distinguished from:**
- Mixed execution — hybrid is a contract type, not an execution mode
- Ensemble — hybrid picks one primary, not a statistical ensemble
- Quantum-classical — hybrid is the merge result, not the merger process

---

## producer

**Definition:** A system that generates raw output before adaptation into a contract. Three producer types exist: QUANTUM (Qiskit Aer simulator), CLASSICAL (deterministic optimizer), and HYBRID (merger of quantum + classical). The producer creates raw data; the adapter transforms it into a `ComputationExecutionContract`. RuntimeCore never inspects or branches on producer type.

**Scope:** `quantum_producer.py`, `adapters.py`, `execution_contract.py`

**Distinguished from:**
- Adapter — the adapter transforms raw output into a contract; the producer creates the raw output
- RuntimeCore — the runtime executes contracts; it does not produce them
- Contract — the contract is the envelope; the producer is the source

---

## runtime

**Definition:** The blind execution engine (`RuntimeCore`) that processes any `ComputationExecutionContract` through an identical, producer-agnostic code path. The runtime owns confidence threshold enforcement, replay detection, ACK generation, and hash computation. It does NOT own producer authorization, contract version policy, or violation recording.

**Scope:** `runtime_core.py`

**Distinguished from:**
- Governance — governance is policy enforcement; runtime is execution
- Execution — execution is the act; runtime is the engine
- Observation — the runtime produces results; the trace store records them

---

## trace

**Definition:** An immutable, hash-verified record of a single step in the execution pipeline. Each `TraceEntry` contains: `trace_id` (linking to contract), `trace_type` (execution, adapter, producer_lineage, contract_lineage, governance), `data` (step-specific payload), `sequence` (deterministic ordering), `entry_hash` (SHA-256 integrity), and `timestamp` (observability anchor). Traces are append-only and frozen after creation.

**Scope:** `observability.py`

**Distinguished from:**
- Log — a trace is structured, hash-verified, and part of a reconstructible chain; a log is unstructured text
- Contract — a contract is input to execution; a trace is output of observation
- Proof — a trace is evidence; proof is the conclusion drawn from traces

---

*Source of truth: `semantic_registry.py`*
