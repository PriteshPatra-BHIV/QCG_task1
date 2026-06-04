# Authority Matrix

> Explicit authority boundaries for all policy-enforcing components.

---

## RuntimeCore

### Authority Owned
- Confidence threshold enforcement — `CORRUPTION_THRESHOLD` halts, `CONFIDENCE_THRESHOLD` degrades
- Replay detection — `trace_id` registry prevents duplicate execution
- ACK generation — determines `ACK:OK`, `ACK:DEGRADED`, or `HALT:*` string
- Runtime hash computation — SHA-256 of `(payload_hash, confidence, ack)`
- Contract schema validation (basic) — validates via `validate_contract()` before execution

### Authority NOT Owned
- Producer type authorization — GovernanceLayer decides which producers are allowed
- Contract version policy — GovernanceLayer enforces minimum version
- Violation recording — GovernanceLayer owns the violation audit trail
- Adapter mapping — Adapter layer owns raw-to-contract transformation
- Observability — TraceStore owns trace recording and replay reconstruction
- Payload content inspection — payload is opaque by design

### Execution Rights
- MAY execute any valid `ComputationExecutionContract` regardless of producer type
- MAY halt execution for low confidence or replay detection
- MAY compute runtime hashes for any contract
- MAY NOT authorize or deny producers — that is governance's domain
- MAY NOT record governance violations — delegation boundary
- MAY NOT inspect payload internals — payload is opaque

### Authority Ceiling
- Could add execution timeout policy
- Could add payload size limits
- CANNOT authorize or deny producers — that is governance's domain
- CANNOT record governance violations — that is governance's domain

---

## GovernanceLayer

### Authority Owned
- Producer type authorization — gate contracts by `producer_type` against allowed set
- Contract version enforcement — reject contracts below `minimum_version`
- Contract schema validation — delegate to `validate_contract()` for structural checks
- Violation recording — accumulate `GovernanceViolation` records for audit
- Strict / permissive mode switching — control whether violations halt or warn
- Post-execution observation — detect `HALT:REPLAY_DETECTED` and `HALT:LOW_CONFIDENCE` from RuntimeCore result ACK

### Authority NOT Owned
- Payload content inspection — payload is opaque; governance MUST NOT read internals
- Adapter selection — choosing QuantumAdapter vs ClassicalAdapter vs HybridAdapter
- Quantum producer configuration — shots, seed, noise model parameters
- Runtime hash computation — SHA-256 of execution path is RuntimeCore's domain
- Confidence threshold enforcement — `CORRUPTION_THRESHOLD` and `CONFIDENCE_THRESHOLD` are RuntimeCore's responsibility
- Replay detection (primary) — RuntimeCore owns the replay registry
- ACK generation — the specific ACK string format is RuntimeCore's output
- Trace store management — recording and querying traces is the observability layer's domain

### Authority Ceiling
- Could add rate limiting policy (currently in `QuantumGateway`)
- Could add circuit-breaker policy (automatic disable after N consecutive violations)
- Could add audit log export
- Could add multi-tenancy policy (per-tenant producer authorization)
- CANNOT modify contract content — contracts are frozen dataclasses
- CANNOT modify runtime execution logic — `RuntimeCore.execute()` is a black box to governance

---

## TraceStore

### Authority Owned
- Trace recording — append-only storage of `TraceEntry` records
- Trace querying — filter by `trace_id` and/or `trace_type`
- Replay reconstruction — rebuild execution chain from stored traces
- Hash chain integrity — compute and verify `entry_hash` for each trace
- Sequence ordering — assign deterministic sequence numbers for replay ordering
- Governance trace recording — store governance decisions and violations

### Authority NOT Owned
- Contract validation — TraceStore does not validate contracts; that is GovernanceLayer + RuntimeCore
- Execution decisions — TraceStore does not decide ACK outcomes; that is RuntimeCore
- Governance policy — TraceStore does not enforce policy; that is GovernanceLayer
- Producer selection — TraceStore does not choose adapters or producers
- Runtime hash computation — TraceStore records hashes but does not compute them
- Confidence threshold enforcement — TraceStore records confidence but does not evaluate it

### Authority Ceiling
- Could add trace export (to external systems)
- Could add trace retention policy (TTL, max entries)
- Could add trace indexing (for faster queries)
- CANNOT modify execution results — ExecutionResult is frozen
- CANNOT modify contracts — ComputationExecutionContract is frozen
- CANNOT enforce governance policy — recording only, not enforcement

---

## Mandatory Negative Declarations

| Component | May | May NOT |
|-----------|-----|---------|
| **Replay** | Reconstruct execution chains from traces | Confer legitimacy — a replayed result is verification evidence, not a new authorization |
| **Observability** | Visualize execution paths and trace chains | Authorize execution — seeing a trace does not grant permission to execute |
| **TraceStore** | Record and query traces | Modify contracts or execution results — both are frozen |
| **GovernanceLayer** | Halt execution on policy violations | Modify payloads — payload content is opaque to governance |
| **GovernanceLayer** | Record violations | Suppress violation recording — every violation MUST be recorded |
| **RuntimeCore** | Execute contracts and compute hashes | Branch on producer type — execution path must be producer-agnostic |
| **RuntimeCore** | Halt on low confidence or replay | Record governance violations — that is GovernanceLayer's domain |

---

*Source of truth: `governance_authority.py` (code), this document (specification).*
