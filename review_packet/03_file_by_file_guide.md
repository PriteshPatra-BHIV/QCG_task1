# What Each File Does

A plain-English guide to every file in the project.

---

## Doctrine Layer

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

## Communication Layer (new)

### `communication_contract.py` — The Universal Message Schema
Defines four frozen, immutable dataclasses that all producer types share:

- `CommunicationRequest` — inbound message from any producer (QUANTUM, CLASSICAL, HYBRID)
- `TranslationContract` — output of the translation step, carrying a content-addressed payload hash
- `AcknowledgementContract` — deterministic receipt from the receiver
- `CommunicationResponse` — full response envelope returned to the caller

Also provides `make_message_id()` (deterministic UUID-5), `resolve_translation_status()`, and `resolve_transport_status()`.

---

### `gateway.py` — The Producer-Agnostic Communication Gateway
The core of the communication layer. Contains:

- `QuantumProducer` — wraps the Qiskit pipeline into a CommunicationRequest
- `ClassicalProducer` — wraps a classical result dict into a CommunicationRequest
- `HybridProducer` — merges quantum + classical into a HYBRID CommunicationRequest
- `Receiver` — issues deterministic AcknowledgementContracts; detects replays; bounded seen-set (100,000 cap)
- `CommunicationGateway` — routes all producer types through the same `send()` method with rate limiting

**The gateway does not branch on source_type**. All 4 cross-system paths (Q→C, C→Q, H→C, H→Q) call `gateway.send()` identically.

---

### `simulation.py` — The Cross-System Simulation
Runs all 4 communication scenarios through the same `CommunicationGateway.send()` and prints a structured trace for each. Proves no special-case routing exists.

---

## Semantic & Authority Layer (new)

### `semantic_registry.py` — The Canonical Term Dictionary
Defines 12 first-class concepts with precise, unambiguous definitions:
`contract`, `truth`, `determinism`, `confidence`, `replay`, `governance`, `authority`, `hybrid`, `execution`, `producer`, `runtime`, `trace`.

Each entry includes: definition, scope (which files), what it's distinguished from, and usage examples. If a term isn't in this registry, it's not a first-class concept in the system.

---

### `governance_authority.py` — The Authority Boundary Declarations
Formally declares the authority of three components:

- `GovernanceLayer` — what it owns (producer authorization, version enforcement, violation recording) and what it may NOT do (inspect payload internals, modify contracts, duplicate RuntimeCore logic)
- `RuntimeCore` — what it owns (confidence thresholds, replay detection, ACK generation) and what it may NOT do (branch on producer_type, inspect payload)
- `TraceStore` — what it owns (append-only trace recording, hash chain integrity) and what it may NOT do (modify contracts, authorize execution)

Includes `validate_authority_boundaries()` — automated structural verification that checks source code, not assertions.

---

### `participation_proof.py` — The Runtime Participation Proof
Proves via **structural evidence** that QUANTUM and CLASSICAL producers both execute through the identical `RuntimeCore.execute()` code path:

1. Same interface (both return `ExecutionResult` with identical keys)
2. Different producer origin (QUANTUM vs CLASSICAL)
3. Same runtime instance — object identity verified
4. No producer-type branching — bytecode constants and names inspected; `QUANTUM`, `CLASSICAL`, `HYBRID` literals absent from `execute()`
5. Same bytecode object — code object id confirmed identical across both calls
6. Valid SHA-256 runtime hashes on both results
7. Contract version parity

Exit 0 = all 8 checks pass.

---

### `ecosystem_participation.py` — The Ecosystem Trust Engine
Demonstrates the gateway as a universal trust infrastructure for 6 ecosystem participants:

- Participant A: Quantum Producer
- Participant B: Classical Producer
- Participant C: NICAI (future consumer)
- Participant D: InsightFlow (future consumer)
- Participant E: Pravah (future consumer)
- Participant F: Sampada (future consumer)

Each participant goes through: NodeRegistry registration → contract signing → TrustChain handoffs → MerkleAuditTrail → ConsensusEngine → ReplayBundle verification.

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
Runs the same transmission 20 times with the same seed and verifies all outputs are identical. Also includes failure injection proof. Exit 0 = pass.

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

### `runtime_demo.py` — The Full 6-Phase Demo
Runs all 6 demonstration phases in sequence: contract creation, adapter mapping, runtime participation proof, governance boundary tests, observability + replay reconstruction, distributed readiness simulation.

---

## Trust Layer

| File | Role |
|------|------|
| `node_identity.py` | NodeIdentity, NodeSigner (ECDSA P-256), NodeProof |
| `provenance.py` | Contract signing and provenance verification |
| `consensus_simulation.py` | Distributed consensus with ECDSA attestations, 66% quorum |
| `replay_bundle.py` | Complete execution lineage artifact |
| `byzantine_simulation.py` | Byzantine fault tolerance (6 cases) |
| `audit_trail.py` | Merkle tamper-evident audit trail |
| `trust_chain.py` | Chain-of-custody with NodeRegistry |
| `determinism_doctrine.py` | Field classification oracle (DETERMINISTIC / OBSERVABILITY / RUNTIME_ONLY) |

---

## Execution Infrastructure

| File | Role |
|------|------|
| `replay_enforcer.py` | Sequence tracking, TTL, ACCEPTED/REJECTED_DUPLICATE/REJECTED_STALE |
| `producer_process.py` | Independent OS process: contract production |
| `execution_process.py` | Independent OS process: replay enforcement + execution |
| `consensus_process.py` | Independent OS process: consensus verification |
| `process_runner.py` | Orchestrator: spawns 3 processes, crash detection |

---

## Tests

### `tests/test_all.py`
65 tests covering the core gateway: input validation, quantum producer, translation layer, gateway pipeline, failure scenarios, determinism proof (5-run + 20-run), replay enforcer, trust chain, audit trail, consensus.

### `tests/test_adapter_layer.py`
74 tests covering the adapter layer: execution contracts, adapters, runtime core, governance, observability, distributed simulation, cross-phase integration.

### `tests/test_communication_layer.py`
74 tests covering the communication layer: CommunicationRequest, TranslationContract, AcknowledgementContract, CommunicationResponse, Receiver (including thread-safety), CommunicationGateway, QuantumProducer, ClassicalProducer, HybridProducer, all 4 cross-system paths.

**Total: 213 tests, all passing.**

---

## Configuration

| File | Purpose |
|------|---------|
| `requirements.txt` | Production dependencies (`qiskit>=2.0.0`, `qiskit-aer>=0.15.0`) |
| `requirements-dev.txt` | Adds pytest |
| `.env.example` | Every config key with its default value — copy to `.env` to customise |
