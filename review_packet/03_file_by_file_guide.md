# What Each File Does

A plain-English guide to every file in the project.

---

## Doctrine Layer — New in This Submission

### `quantum_uncertainty.py` — The Uncertainty Classifier
Wraps every quantum output in an explicit `UncertaintyEnvelope` before it touches the contract layer.

Five classes: `HIGH_CONFIDENCE`, `LOW_CONFIDENCE`, `DEGRADED`, `UNTRANSLATABLE`, `REJECTED`.

Key rule: **quantum uncertainty ≠ operational failure**. An UNTRANSLATABLE result is a safe HOLD, not a crash.

---

### `contract_semantics.py` — The Determinism + Convergence Proof
Proves two things:
1. Same seed + same inputs = identical contract every time (determinism).
2. Different quantum distributions can map to the same contract (convergence — doctrine absorbs bounded variance).

---

### `degraded_runtime.py` — The Outcome Evaluator
Maps a contract into one of five explicit operational outcomes:

| Outcome | Meaning |
|---------|---------|
| OK | Safe participation allowed |
| DEGRADED | Participation allowed with warning lineage |
| HOLD | No action — conditions not safe enough |
| REJECT | Contract invalid, discard |
| HALT | System safety stop |

Every boundary has a written justification in the source code.

---

### `lineage.py` — The Provenance Tracker
Attaches a full audit trail to every contract: who produced it, what algorithm, what confidence method, what uncertainty class, what seed, what timestamp. Full reconstruction from the final contract — no hidden state.

---

### `authority_boundary_test.py` — The Anti-Authority Proof
The most important file to read for understanding the safety model.

Proves that even at maximum confidence (0.9326), the system emits a **recommendation**, not a command. Authority always stays with the caller.

```
authority_transferred : False  ← always
authority_holder      : CALLER ← always
```

---

### `run_semantics_runtime.py` — The Runtime Proof
Runs all 5 cases (A–E) and proves each produces a clear, structured outcome. No silent states. Exit code 0 = all pass.

---

## Core Gateway Layer

### `config.py` — The Settings Panel
All constants in one place: confidence thresholds, rate limits, message length cap, log format, seed. Every value is overridable via `.env` file. Validated at startup — invalid settings abort with a clear error.

---

### `models.py` — The Data Shapes
Three frozen (immutable) dataclasses:
- `TransmissionRequest` — what you send in
- `QuantumDistribution` — the raw quantum output
- `ClassicalContract` — the final deterministic decision

All three validate their inputs on construction. Frozen means they cannot be altered after creation.

---

### `logger.py` — The Black Box Recorder
Thread-safe structured logger. JSON format in production (one line per event, easy for monitoring tools). Text format in development. All context goes into a `ctx` dict to avoid collisions with Python's reserved log record fields.

---

### `quantum_producer.py` — The Quantum Sender (Layer 1)
Encodes the message into a superdense coding quantum circuit, runs it through Qiskit AER with a noise model, and returns a `QuantumDistribution`. Seed-locked for determinism.

---

### `translation_layer.py` — The Translator (Layer 2)
Takes the `QuantumDistribution` and produces a `ClassicalContract`. Raises `TranslationError` if the contract must be rejected. Logs at WARNING level for rejections (so monitoring systems catch them). Raw counts never leave this file.

---

### `hybrid_gateway.py` — The Orchestrator (Layers 3–5)
Runs the full pipeline. Enforces rate limiting (token-bucket). Guards against replay attacks (thread-safe registry). Never raises — every failure is captured in the ACK string. Exposes `health_check()`.

---

### `determinism_proof.py` — The Consistency Checker (Layer 6)
Runs the same transmission 5 times with the same seed and verifies all outputs are identical. Exit 0 = pass.

---

## Adapter / Execution Layer

### `execution_contract.py` — The Generic Contract (v2.0.0)
`ComputationExecutionContract` wraps any producer's output (quantum, classical, or hybrid) into a uniform envelope. The runtime core processes this without ever checking `producer_type` for branching.

---

### `adapters.py` — The Adapters
Three adapters convert producer-specific outputs into `ComputationExecutionContract`:
- `QuantumAdapter` — from `QuantumDistribution`
- `ClassicalAdapter` — from a plain dict with `result` and `confidence`
- `HybridAdapter` — merges quantum + classical by confidence-weighted selection

---

### `runtime_core.py` — The Blind Core
Executes every contract through the same code path regardless of `producer_type`. Validates, checks for replay, applies confidence thresholds, returns `ExecutionResult`. Never raises.

---

### `governance.py` — The Policy Layer
Wraps `RuntimeCore` with five enforcement policies: unauthorized producer, contract downgrade, invalid contract, low confidence, replay mismatch. Strict mode halts immediately; permissive mode logs and continues.

---

### `observability.py` — The Trace Store
Records every execution, adapter, lineage, and governance event. Bounded to 10,000 entries (deque). Supports replay reconstruction with hash-chain integrity verification.

---

### `distributed_simulation.py` — The Multi-Node Proof
Simulates N nodes processing the same contracts and verifies ledger hash agreement across all nodes. Proves the system behaves consistently in a distributed context.

---

## Tests

### `tests/test_all.py`
52 tests covering the core gateway: input validation, quantum producer, translation layer, gateway pipeline, failure scenarios, determinism proof, thread safety.

### `tests/test_adapter_layer.py`
70 tests covering the adapter layer: execution contracts, adapters, runtime core, governance, observability, distributed simulation, cross-phase integration.

**Total: 122 tests, all passing.**

---

## Configuration

| File | Purpose |
|------|---------|
| `requirements.txt` | Production dependencies (`qiskit>=2.0.0`, `qiskit-aer>=0.15.0`) |
| `requirements-dev.txt` | Adds pytest |
| `.env.example` | Every config key with its default value — copy to `.env` to customise |
