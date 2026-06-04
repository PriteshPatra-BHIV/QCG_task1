# Semantic Registry — QCG System

> Canonical definitions for all key terms. If a term is not here, it is not a first-class concept in the system.

---

## contract

**Definition:** A frozen, schema-validated envelope carrying opaque producer output through a uniform execution pipeline. A contract is a data structure (`ComputationExecutionContract`), not a legal agreement or bilateral promise. It is immutable after creation.

**Scope:** `execution_contract.py`, `adapters.py`, `runtime_core.py`, `governance.py`

**Distinguished from:**
- Legal contract — no bilateral agreement or enforcement exists
- Promise — a contract does not guarantee outcome, only structure
- Message — a contract wraps a message but is not the message itself

---

## truth

**Definition:** NOT USED in this system. The system operates on *confidence* (statistical measure) and *determinism* (reproducibility guarantee), not truth claims. No component asserts that a result is "true" — only that it is reproducible and above a confidence threshold.

**Scope:** N/A — deliberately excluded from the system vocabulary

**Distinguished from:**
- Confidence — a statistical ratio, not a truth value
- Determinism — reproducibility of output, not correctness of output
- Correctness — not claimed; only fidelity to protocol is verified

---

## determinism

**Definition:** Given identical inputs (message, seed, noise, mode) and identical configuration, the system produces identical deterministic-projection outputs across any number of runs. Timestamps are observability metadata excluded from the deterministic surface. Three sub-categories exist:

| Category | Scope | What is deterministic |
|----------|-------|-----------------------|
| Execution determinism | `RuntimeCore.execute()` | ack, runtime_hash, confidence |
| Contract determinism | Adapters | payload_hash, trace_id, confidence, payload |
| Observability determinism | Trace store | entry_hash (given same timestamp input) |

**Distinguished from:**
- Randomness — the system is deterministic given a seed
- Idempotency — replay guard prevents re-execution; determinism means same-input-same-output
- Truth — determinism guarantees reproducibility, not correctness

---

## confidence

**Definition:** The ratio of dominant measurement outcomes to total shots in a quantum distribution. Range `[0.0, 1.0]`. A confidence of `0.93` means 93% of the 1024 simulated shots landed on the dominant bitstring. This is a statistical frequency ratio, NOT a probability of correctness.

**Scope:** `translation_layer.py`, `runtime_core.py`, `governance.py`

**Thresholds:**

| Threshold | Value | Effect |
|-----------|-------|--------|
| `CONFIDENCE_THRESHOLD` | 0.70 | Below this → `ACK:DEGRADED` |
| `CORRUPTION_THRESHOLD` | 0.40 | Below this → `HALT:LOW_CONFIDENCE` |

**Distinguished from:**
- Probability of correctness — measures signal dominance, not whether the answer is "right"
- Certainty — the system never claims certainty
- Truth — confidence is a measurement statistic, not a truth claim

---

## replay

**Definition:** Re-execution of a previously-observed contract or pipeline segment to verify deterministic reproducibility. Five canonical replay targets exist:

| Target | What it verifies | Proves |
|--------|-----------------|--------|
| `PAYLOAD` | Re-derive contract from same raw input | Adapter determinism |
| `CONTRACT` | Re-execute same contract through RuntimeCore | Runtime determinism |
| `RUNTIME` | Re-run governance + runtime from same contract | Governance + runtime determinism |
| `CROSS_NODE` | N independent nodes process same contract | Distributed determinism |
| `SEMANTIC` | Same ACK category + confidence band | Meaning equivalence |

Replay is **verification**, not re-processing.

**Distinguished from:**
- Replay attack — malicious re-submission; detected by `trace_id` registry
- Retry — re-attempt after failure; replay is re-verification of success
- Idempotency — replay verifies determinism; idempotency prevents side effects

---

## governance

**Definition:** Policy enforcement layer that gates contract execution without modifying contract content or bypassing runtime logic.

**Authority owned:**
- Producer type authorization
- Contract version enforcement
- Contract schema validation
- Violation recording
- Strict / permissive mode switching

**Authority NOT owned:**
- Confidence threshold enforcement (→ RuntimeCore)
- Replay detection (→ RuntimeCore)
- ACK generation (→ RuntimeCore)
- Payload content inspection (→ Never)

**Distinguished from:**
- Runtime execution — governance gates execution, does not perform it
- Validation — governance delegates schema validation to `validate_contract()`
- Administration — governance is automated policy, not human oversight

---

## ownership

**Definition:** The explicit set of responsibilities a component controls (`authority_owned`) versus delegates (`authority_not_owned`). Every policy-enforcing component declares its authority boundary including a ceiling (maximum scope) and negative authority (things it is prohibited from doing).

**Structure:**

| Dimension | Meaning |
|-----------|---------|
| Authority Owned | What the component controls |
| Authority NOT Owned | What it explicitly delegates |
| Authority Ceiling | Maximum possible scope |
| Negative Authority | What it is prohibited from doing |

**Distinguished from:**
- Hierarchy — ownership is peer-based, not parent-child
- Control — ownership means responsibility, not absolute control

---

## hybrid

**Definition:** A merged contract produced by combining one QUANTUM and one CLASSICAL contract via confidence-weighted selection. The merge strategy, not the execution path, is what makes it hybrid. Once merged, a HYBRID contract traverses the same `RuntimeCore.execute()` code path as any other contract.

**Distinguished from:**
- Mixed execution — hybrid is a contract type, not an execution mode
- Ensemble — hybrid picks one primary, not a statistical ensemble
- Quantum-classical — hybrid is the merge result, not the merger process

---

*Source of truth: `semantic_registry.py`*
