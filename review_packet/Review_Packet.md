# Review Packet — Hybrid Quantum Communication Gateway (QCG)

> A complete, non-technical overview of the project — what it is, how it works,
> what each file does, how decisions are made, whether it's production ready,
> and how to run it.

**Last Updated:** 2025-06-03
**Status:** Production-ready (single-instance)
**Test Suite:** 122/122 passing

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [How a Message Travels Through the System](#2-how-a-message-travels-through-the-system)
3. [What Each File Does](#3-what-each-file-does)
4. [How the System Makes Decisions](#4-how-the-system-makes-decisions)
5. [Is This System Production Ready?](#5-is-this-system-production-ready)
6. [Quick Start — Run It in 5 Minutes](#6-quick-start--run-it-in-5-minutes)

---

## 1. What Is This Project?

### The One-Line Answer
A communication gateway that uses quantum physics to send messages — and converts the probabilistic quantum result into a deterministic, auditable decision that any classical system can consume safely.

### The Problem It Solves

Normal computers speak in certainties — yes or no, 0 or 1.

Quantum computers speak in probabilities — "maybe 0, maybe 1, here's the chance of each."

These two worlds don't naturally talk to each other. If you plug a quantum output directly into a classical system, the classical system has no safe way to interpret "70% chance it's a 1" — it needs a firm answer.

**This project builds the bridge.**

### What It Does — In Plain English

1. You send a message like `"NODE_READY"`.
2. The system encodes it using quantum physics (superdense coding) and simulates transmission through a noisy channel.
3. It receives a probabilistic result — a spread of possible outcomes with frequencies.
4. It classifies the uncertainty explicitly: is this HIGH_CONFIDENCE? DEGRADED? UNTRANSLATABLE?
5. It translates the result into a clean, structured decision: *"The message arrived. We're 93% sure. Status: OK."*
6. A classical system receives that decision and responds: `ACK:OK:NODE_READY`.
7. The quantum output never directly triggers any action. It produces a recommendation. The caller decides.

### The Key Rule

> Quantum output → classified uncertainty → deterministic contract → operational recommendation.
>
> Never: quantum output → autonomous command.

This rule is enforced in code and proven at runtime. It is not just a design principle.

### Key Guarantee

Same inputs + same seed = identical output, every time. This is verified by running the pipeline 5 times and confirming zero mismatches.

---

## 2. How a Message Travels Through the System

### The Journey of "NODE_READY"

**Step 1 — You provide three things:**
- The message: `NODE_READY`
- Channel noise level: `0.12` (12% interference)
- Transmission mode: `entangled`

**Step 2 — Quantum Encoding**

The message is converted to a 2-bit code via superdense coding and simulated through a quantum channel with the specified noise. The output is a probability distribution across 1024 shots:

```
{ "11": 697, "10": 162, "01": 86, "00": 79 }
```

"11" won 697 out of 1024 times — that is the dominant outcome.

**Step 3 — Uncertainty Classification**

Before any contract is formed, the distribution is classified:

```
confidence     = 697 / 1024 = 0.6807
uncertainty    = LOW_CONFIDENCE
posture        = PROCEED_WITH_CAUTION
```

This envelope is the explicit boundary. Probabilistic quantum behaviour stops here.

**Step 4 — Translation**

The dominant bitstring is checked against what was expected for "NODE_READY". If it matches and confidence is above the floor, a Classical Contract is formed:

```json
{
  "trace_id":            "c987207f-a809-54e9-b64b-e7940c28f291",
  "confidence":          0.6807,
  "decoded_message":     "NODE_READY",
  "transmission_status": "DEGRADED",
  "uncertainty_score":   0.3193,
  "contract_version":    "1.0.0"
}
```

No raw probabilities. No quantum counts. Just a structured decision.

**Step 5 — Operational Posture**

The contract is evaluated against context (noise level, replay registry, rate limits):

```
outcome      : DEGRADED
emit_action  : True  (participation allowed, warning lineage attached)
justification: Confidence 0.6807 in [0.40, 0.70). Participation allowed with warning lineage.
```

**Step 6 — ACK**

```
ACK:DEGRADED:NODE_READY:confidence=0.6807
```

The pipeline is complete. The quantum layer stayed probabilistic the whole time. The classical layer received a deterministic, auditable result.

---

## 3. What Each File Does

### Doctrine Layer (new in this submission)

| File | Phase | Role |
|------|-------|------|
| `quantum_uncertainty.py` | 1 | Classifies quantum output into 5 uncertainty classes. Hard boundary. |
| `contract_semantics.py` | 2 | Proves determinism (same seed → same contract) and convergence (different distributions → same contract). |
| `degraded_runtime.py` | 3 | Maps contracts to operational postures: OK, DEGRADED, HOLD, REJECT, HALT. |
| `lineage.py` | 4 | Builds and reconstructs full contract provenance. No hidden state. |
| `authority_boundary_test.py` | 5 | Proves the system never becomes execution authority, even at 0.99 confidence. |
| `run_semantics_runtime.py` | 6 | Runs all 5 runtime cases (A–E). No silent states. Exit 0 = all pass. |

### Core Gateway Layer

| File | Layer | Role |
|------|-------|------|
| `quantum_producer.py` | 1 | Qiskit superdense coding simulation. Returns QuantumDistribution. |
| `translation_layer.py` | 2 | Converts quantum output to ClassicalContract. Raises TranslationError on rejection. |
| `hybrid_gateway.py` | 3–5 | Orchestrates pipeline, rate limiting, replay guard, health check. |
| `determinism_proof.py` | 6 | 5-run seed-locked determinism verification. |

### Adapter / Runtime Layer

| File | Role |
|------|------|
| `execution_contract.py` | Generic ComputationExecutionContract (v2.0.0) wrapping any producer output. |
| `adapters.py` | QuantumAdapter, ClassicalAdapter, HybridAdapter — maps producer outputs to execution contracts. |
| `runtime_core.py` | Producer-blind execution core. Never inspects producer_type for branching. |
| `governance.py` | Policy enforcement wrapping RuntimeCore. 5 failure policies. Never crashes. |
| `observability.py` | TraceStore — records and reconstructs full execution lineage. Bounded to 10,000 entries. |
| `distributed_simulation.py` | Multi-node simulation with hash-chain ledger agreement proof. |

### Infrastructure

| File | Role |
|------|------|
| `config.py` | All constants, env-overridable. Validated at startup. |
| `models.py` | Frozen dataclasses: TransmissionRequest, QuantumDistribution, ClassicalContract. |
| `logger.py` | Structured JSON logger (production) or text (development). Thread-safe. |
| `requirements.txt` | Production dependencies (qiskit≥2.0.0, qiskit-aer≥0.15.0). |
| `.env.example` | All config keys with defaults. Copy to .env to customise. |

---

## 4. How the System Makes Decisions

### Uncertainty Classification (before any contract is formed)

| Class | Condition | Recommended Posture |
|-------|-----------|---------------------|
| HIGH_CONFIDENCE | confidence ≥ 0.70 | PROCEED |
| LOW_CONFIDENCE | confidence in [0.40, 0.70) | PROCEED_WITH_CAUTION |
| DEGRADED | noise > 0.50 AND confidence < 0.70 | HOLD |
| UNTRANSLATABLE | confidence < 0.30 (cannot decode) | HOLD |
| REJECTED | confidence < 0.40 | REJECT |

### Operational Outcomes (after translation)

| Outcome | Condition | Action permitted? |
|---------|-----------|-------------------|
| OK | confidence ≥ 0.70, message matches | Yes |
| DEGRADED | confidence in [0.40, 0.70), message matches | Yes, with warning lineage |
| HOLD | noise > 0.50 AND status ≠ OK | No |
| REJECT | confidence < 0.40 OR bit mismatch | No |
| HALT | replay detected OR rate limit exceeded | No |

### All HALT Responses

| Response | Cause |
|----------|-------|
| `HALT:TRANSLATION_FAILURE` | Signal too noisy to translate |
| `HALT:REPLAY_DETECTED` | Same trace_id received twice |
| `HALT:RATE_LIMIT_EXCEEDED` | Too many requests per minute |
| `HALT:INVALID_INPUT` | Empty, oversized, or invalid message |
| `HALT:CONTRACT_DOWNGRADE` | Contract version below minimum |
| `HALT:UNAUTHORIZED_PRODUCER` | Producer type not in allowed set |
| `HALT:UNEXPECTED` | Unhandled internal exception (always logged) |

The system never crashes. Every code path returns one of the above.

---

## 5. Is This System Production Ready?

**Short answer: Yes — for single-instance deployment.**

### Production Fixes Applied

| Fix | Why It Matters |
|-----|---------------|
| `ClassicalContract` made frozen | Contracts must be immutable. A mutable contract can be silently altered after formation, breaking the audit trail. |
| REJECTED translations log at WARNING | Monitoring systems filtering INFO would silently miss every rejection. Fixed to WARNING. |
| `TraceStore` bounded to 10,000 entries | Unbounded list in a long-running process → eventual OOM. Now uses `deque(maxlen=10_000)`. |
| `GovernanceLayer._violations` bounded the same | Same reason. |
| `from __future__ import annotations` added | Union type syntax `X \| Y` is not valid at runtime in Python < 3.10 without this. Added to 5 files. |
| `requirements.txt` corrected | Was pinned to `qiskit-aer==0.14.2` (incompatible with qiskit 2.x). Corrected to `>=0.15.0`. |
| `.env.example` completed | Was missing all adapter-layer config keys. Now includes every key read by `config.py`. |

### Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Replay registry in-memory | Replay protection breaks across restarts and multi-instance deployments | Use Redis or a DB for production multi-instance |
| TraceStore in-memory | Traces lost on restart; capped at 10,000 entries | Export to OpenTelemetry for distributed deployments |
| Quantum simulation synchronous | High request volumes will queue | Acceptable for current prototype scale |
| No cryptographic lineage signatures | Lineage cannot be third-party verified | Add HMAC if non-repudiation is required |

---

## 6. Quick Start — Run It in 5 Minutes

### Requirements
- Python 3.10+
- pip

### Install
```bash
pip install -r requirements.txt       # production
pip install -r requirements-dev.txt   # + pytest
```

### Run the doctrine proof
```bash
python run_semantics_runtime.py
# Expected: ALL CASES PASSED, exit 0
```

### Run the anti-authority proof
```bash
python authority_boundary_test.py
# Expected: VERDICT: PASS, exit 0
```

### Run the determinism proof
```bash
python determinism_proof.py
# Expected: passed=true, mismatches=[], exit 0
```

### Run the full gateway demo
```bash
python hybrid_gateway.py
# Expected last event: "ack": "ACK:OK:NODE_READY"
```

### Run all tests
```bash
pytest tests/ -v
# Expected: 122 passed
```

### (Optional) Configure
```bash
copy .env.example .env
# Edit .env to tune thresholds, log format, rate limits, etc.
```

---

*This document is the non-technical companion to `REVIEW_PACKET.md` (technical) and `TESTING_PACKET.md` (evidence).*
