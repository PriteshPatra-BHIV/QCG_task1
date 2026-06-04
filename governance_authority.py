"""
governance_authority.py — Explicit Authority Declarations

Defines the formal authority boundary for GovernanceLayer:
    - What it OWNS (controls)
    - What it does NOT OWN (delegates)
    - Its CEILING (maximum possible scope)
    - NEGATIVE authority (what it is prohibited from doing)

This is the governance ownership contract.  Any behaviour outside
these boundaries is a governance violation against itself.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Authority declaration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthorityDeclaration:
    """
    Immutable declaration of a component's authority boundaries.

    Every component that enforces policy should declare its authority
    so that boundary violations can be detected structurally.
    """
    component:          str
    authority_owned:    tuple[str, ...]
    authority_not_owned: tuple[str, ...]
    execution_rights:   tuple[str, ...]
    authority_ceiling:  tuple[str, ...]
    negative_authority: tuple[str, ...]\n


# ---------------------------------------------------------------------------
# GovernanceLayer authority
# ---------------------------------------------------------------------------

GOVERNANCE_AUTHORITY = AuthorityDeclaration(
    component="GovernanceLayer",

    authority_owned=(
        "Producer type authorization — gate contracts by producer_type against allowed set",
        "Contract version enforcement — reject contracts below minimum_version",
        "Contract schema validation — delegate to validate_contract() for structural checks",
        "Violation recording — accumulate GovernanceViolation records for audit",
        "Strict / permissive mode switching — control whether violations halt or warn",
        "Post-execution observation — detect HALT:REPLAY_DETECTED from RuntimeCore result ACK",
    ),

    authority_not_owned=(
        "Payload content inspection — payload is opaque; governance MUST NOT read internals",
        "Adapter selection — choosing QuantumAdapter vs ClassicalAdapter vs HybridAdapter",
        "Quantum producer configuration — shots, seed, noise model parameters",
        "Runtime hash computation — SHA-256 of execution path is RuntimeCore's domain",
        "Confidence threshold enforcement — CORRUPTION_THRESHOLD and CONFIDENCE_THRESHOLD "
            "are RuntimeCore's responsibility; governance observes the result, not the threshold",
        "Replay detection (primary) — RuntimeCore owns the replay registry; governance "
            "observes REPLAY_DETECTED in the result ACK",
        "ACK generation — the specific ACK string format is RuntimeCore's output",
        "Trace store management — recording and querying traces is the observability layer's domain",
        "Network topology — no awareness of node count, routing, or distributed layout",
    ),

    execution_rights=(),

    authority_ceiling=(
        "Rate limiting policy — could add request-rate governance (currently in QuantumGateway)",
        "Circuit-breaker policy — could add automatic disable after N consecutive violations",
        "Audit log export — could add structured export of violation history",
        "Multi-tenancy policy — could add per-tenant producer authorization",
        "CANNOT modify contract content — contracts are frozen dataclasses",
        "CANNOT modify runtime execution logic — RuntimeCore.execute() is a black box to governance",
    ),

    negative_authority=(
        "MUST NOT inspect payload internals — payload dict is opaque to governance",
        "MUST NOT modify contract fields — ComputationExecutionContract is frozen",
        "MUST NOT bypass RuntimeCore for execution — all execution flows through core.execute()",
        "MUST NOT suppress violation recording — every detected violation MUST be recorded",
        "MUST NOT duplicate RuntimeCore's confidence threshold logic — confidence is "
            "RuntimeCore's domain; governance records the outcome, not the decision",
        "MUST NOT alter trace entries — TraceEntry is frozen; governance may create but not modify",
    ),
)


# ---------------------------------------------------------------------------
# RuntimeCore authority
# ---------------------------------------------------------------------------

RUNTIME_AUTHORITY = AuthorityDeclaration(
    component="RuntimeCore",

    authority_owned=(
        "Confidence threshold enforcement — CORRUPTION_THRESHOLD halts, CONFIDENCE_THRESHOLD degrades",
        "Replay detection — trace_id registry prevents duplicate execution",
        "ACK generation — determines OK, DEGRADED, or HALT:* string",
        "Runtime hash computation — SHA-256 of (payload_hash, confidence, ack)",
        "Contract schema validation (basic) — validates via validate_contract() before execution",
    ),

    authority_not_owned=(
        "Producer type authorization — GovernanceLayer decides which producers are allowed",
        "Contract version policy — GovernanceLayer enforces minimum version",
        "Violation recording — GovernanceLayer owns the violation audit trail",
        "Adapter mapping — Adapter layer owns raw-to-contract transformation",
        "Observability — TraceStore owns trace recording and replay reconstruction",
    ),

    execution_rights=(
        "MAY execute any valid ComputationExecutionContract regardless of producer type",
        "MAY halt execution for low confidence or replay detection",
        "MAY compute runtime hashes for any contract",
        "MAY NOT authorize or deny producers — that is governance's domain",
        "MAY NOT record governance violations — delegation boundary",
        "MAY NOT inspect payload internals — payload is opaque",
    ),

    authority_ceiling=(
        "Could add execution timeout policy",
        "Could add payload size limits",
        "CANNOT authorize or deny producers — that is governance's domain",
        "CANNOT record governance violations — that is governance's domain",
    ),

    negative_authority=(
        "MUST NOT inspect payload internals — payload is opaque",
        "MUST NOT branch on producer_type — this is the core proof surface",
        "MUST NOT record governance violations — delegation boundary",
        "MUST NOT modify contracts — contracts are frozen",
    ),
)


# ---------------------------------------------------------------------------
# TraceStore authority
# ---------------------------------------------------------------------------

TRACESTORE_AUTHORITY = AuthorityDeclaration(
    component="TraceStore",

    authority_owned=(
        "Trace recording — append-only storage of TraceEntry records",
        "Trace querying — filter by trace_id and/or trace_type",
        "Replay reconstruction — rebuild execution chain from stored traces",
        "Hash chain integrity — compute and verify entry_hash for each trace",
        "Sequence ordering — assign deterministic sequence numbers for replay ordering",
        "Governance trace recording — store governance decisions and violations",
    ),

    authority_not_owned=(
        "Contract validation — TraceStore does not validate contracts; that is GovernanceLayer + RuntimeCore",
        "Execution decisions — TraceStore does not decide ACK outcomes; that is RuntimeCore",
        "Governance policy — TraceStore does not enforce policy; that is GovernanceLayer",
        "Producer selection — TraceStore does not choose adapters or producers",
        "Runtime hash computation — TraceStore records hashes but does not compute them",
        "Confidence threshold enforcement — TraceStore records confidence but does not evaluate it",
    ),

    execution_rights=(),

    authority_ceiling=(
        "Could add trace export (to external systems)",
        "Could add trace retention policy (TTL, max entries)",
        "Could add trace indexing (for faster queries)",
        "CANNOT modify execution results — ExecutionResult is frozen",
        "CANNOT modify contracts — ComputationExecutionContract is frozen",
        "CANNOT enforce governance policy — recording only, not enforcement",
    ),

    negative_authority=(
        "MUST NOT modify contracts or execution results — both are frozen",
        "MUST NOT delete traces — append-only ledger",
        "MUST NOT authorize execution — seeing a trace does not grant permission to execute",
    ),
)


# ---------------------------------------------------------------------------
# Boundary validation
# ---------------------------------------------------------------------------

def validate_authority_boundaries(component_name: str = "GovernanceLayer") -> dict:
    """
    Structurally verify that the named component respects its declared
    authority boundaries.

    Returns a dict with verification results.
    """
    results = {"component": component_name, "checks": {}, "passed": True}

    if component_name == "GovernanceLayer":
        from governance import GovernanceLayer
        import inspect

        source = inspect.getsource(GovernanceLayer.enforce)

        # Check: governance does NOT access payload internals
        payload_access = (
            ".payload[" in source
            or ".payload.get(" in source
            or "payload[\"" in source
        )
        results["checks"]["no_payload_inspection"] = not payload_access
        if payload_access:
            results["passed"] = False

        # Check: governance does NOT modify contract fields
        contract_mutation = "object.__setattr__" in source
        results["checks"]["no_contract_mutation"] = not contract_mutation
        if contract_mutation:
            results["passed"] = False

        # Check: governance delegates to RuntimeCore for execution
        runtime_delegation = "self.runtime.execute(" in source
        results["checks"]["delegates_to_runtime"] = runtime_delegation
        if not runtime_delegation:
            results["passed"] = False

    elif component_name == "RuntimeCore":
        from runtime_core import RuntimeCore
        import inspect

        source = inspect.getsource(RuntimeCore.execute)

        # Check: runtime does NOT branch on producer_type
        producer_branch = (
            "producer_type ==" in source
            or "producer_type !=" in source
            or "\"QUANTUM\"" in source
            or "\"CLASSICAL\"" in source
            or "\"HYBRID\"" in source
        )
        results["checks"]["no_producer_branch"] = not producer_branch
        if producer_branch:
            results["passed"] = False

        # Check: runtime does NOT inspect payload
        payload_access = (
            ".payload[" in source
            or ".payload.get(" in source
        )
        results["checks"]["no_payload_inspection"] = not payload_access
        if payload_access:
            results["passed"] = False

    return results
