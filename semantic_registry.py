"""
semantic_registry.py — Canonical Semantic Registry

Provides precise, unambiguous definitions for all key terms used in the
QCG system.  Every term includes its scope, what it is explicitly
distinguished from, and where in the codebase it materialises.

This registry is the single source of truth for terminology.
If a term is not in this registry, it is not a first-class concept
in the system.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SemanticEntry:
    """One entry in the semantic registry."""
    term:                str
    definition:          str
    scope:               str
    distinguished_from:  tuple[str, ...]
    usage_examples:      tuple[str, ...]


# ---------------------------------------------------------------------------
# Canonical registry
# ---------------------------------------------------------------------------

SEMANTIC_REGISTRY: dict[str, SemanticEntry] = {

    "contract": SemanticEntry(
        term="contract",
        definition=(
            "A frozen, schema-validated envelope carrying opaque producer output "
            "through a uniform execution pipeline.  A contract is a data structure "
            "(ComputationExecutionContract), not a legal agreement or bilateral "
            "promise.  It is immutable after creation."
        ),
        scope="execution_contract.py, adapters.py, runtime_core.py, governance.py",
        distinguished_from=(
            "Legal contract — no bilateral agreement or enforcement exists",
            "Promise — a contract does not guarantee outcome, only structure",
            "Message — a contract wraps a message but is not the message itself",
        ),
        usage_examples=(
            "ComputationExecutionContract in execution_contract.py",
            "ClassicalContract in models.py (translation-layer output)",
            "Adapters create contracts; RuntimeCore consumes them",
        ),
    ),

    "truth": SemanticEntry(
        term="truth",
        definition=(
            "NOT USED in this system.  The system operates on confidence "
            "(statistical measure) and determinism (reproducibility guarantee), "
            "not truth claims.  No component asserts that a result is 'true' — "
            "only that it is reproducible and above a confidence threshold."
        ),
        scope="N/A — deliberately excluded from the system vocabulary",
        distinguished_from=(
            "Confidence — a statistical ratio, not a truth value",
            "Determinism — reproducibility of output, not correctness of output",
            "Correctness — not claimed; only fidelity to protocol is verified",
        ),
        usage_examples=(
            "No code references 'truth' as a concept",
        ),
    ),

    "determinism": SemanticEntry(
        term="determinism",
        definition=(
            "Given identical inputs (message, seed, noise, mode) and identical "
            "configuration, the system produces identical deterministic-projection "
            "outputs across any number of runs.  Timestamps are observability "
            "metadata excluded from the deterministic surface.  Three sub-categories "
            "exist: execution determinism (RuntimeCore), contract determinism "
            "(adapters), and observability determinism (trace hashes)."
        ),
        scope="determinism_doctrine.py, determinism_proof.py, runtime_core.py",
        distinguished_from=(
            "Randomness — the system is deterministic given a seed; the seed "
            "controls the quantum simulation's PRNG",
            "Idempotency — replay guard prevents re-execution of the same trace_id; "
            "determinism means same-input-same-output, not re-executable",
            "Truth — determinism guarantees reproducibility, not correctness",
        ),
        usage_examples=(
            "DeterminismOracle in determinism_doctrine.py",
            "run_determinism_proof() in determinism_proof.py",
            "seed_simulator parameter in quantum_producer.py",
        ),
    ),

    "confidence": SemanticEntry(
        term="confidence",
        definition=(
            "The ratio of dominant measurement outcomes to total shots in a "
            "quantum distribution.  Range [0.0, 1.0].  A confidence of 0.93 "
            "means 93% of the 1024 simulated shots landed on the dominant "
            "bitstring.  This is a statistical frequency ratio, NOT a "
            "probability of correctness."
        ),
        scope="translation_layer.py, runtime_core.py, governance.py",
        distinguished_from=(
            "Probability of correctness — confidence measures signal dominance, "
            "not whether the answer is 'right'",
            "Certainty — the system never claims certainty",
            "Truth — confidence is a measurement statistic, not a truth claim",
        ),
        usage_examples=(
            "CONFIDENCE_THRESHOLD (0.70) in config.py — below this, ACK:DEGRADED",
            "CORRUPTION_THRESHOLD (0.40) in config.py — below this, HALT:LOW_CONFIDENCE",
            "ClassicalContract.confidence in models.py",
        ),
    ),

    "replay": SemanticEntry(
        term="replay",
        definition=(
            "Re-execution of a previously-observed contract or pipeline segment "
            "to verify deterministic reproducibility.  Five canonical replay "
            "targets exist: PAYLOAD (adapter determinism), CONTRACT (runtime "
            "determinism), RUNTIME (governance+runtime determinism), CROSS_NODE "
            "(distributed determinism), SEMANTIC (meaning equivalence).  "
            "Replay is verification, not re-processing."
        ),
        scope="replay_doctrine.py, observability.py, runtime_core.py",
        distinguished_from=(
            "Replay attack — malicious re-submission; detected by trace_id registry",
            "Retry — re-attempt after failure; replay is re-verification of success",
            "Idempotency — replay verifies determinism; idempotency prevents side effects",
        ),
        usage_examples=(
            "ReplayEngine in replay_doctrine.py",
            "ReplayTarget enum: PAYLOAD | CONTRACT | RUNTIME | CROSS_NODE | SEMANTIC",
            "RuntimeCore._replay_registry prevents duplicate execution",
            "TraceStore.reconstruct_replay() rebuilds execution chain",
        ),
    ),

    "governance": SemanticEntry(
        term="governance",
        definition=(
            "Policy enforcement layer that gates contract execution without "
            "modifying contract content or bypassing runtime logic.  Governance "
            "owns pre-execution policy (producer authorization, version enforcement, "
            "schema validation) and post-execution observation (recording violations "
            "from RuntimeCore results).  Governance does NOT own confidence "
            "thresholds, replay detection, or ACK generation."
        ),
        scope="governance.py, governance_authority.py",
        distinguished_from=(
            "Runtime execution — governance gates execution, does not perform it",
            "Validation — governance delegates schema validation to validate_contract()",
            "Administration — governance is automated policy, not human oversight",
        ),
        usage_examples=(
            "GovernanceLayer.enforce() in governance.py",
            "GovernanceViolation records in governance.py",
            "AuthorityDeclaration in governance_authority.py",
        ),
    ),

    "authority": SemanticEntry(
        term="authority",
        definition=(
            "The explicit set of responsibilities a component controls "
            "(authority_owned) versus delegates (authority_not_owned).  "
            "Every policy-enforcing component declares its authority boundary "
            "including a ceiling (maximum scope) and negative authority "
            "(things it is prohibited from doing).  Authority is structural, "
            "not hierarchical — GovernanceLayer and RuntimeCore are peers "
            "with non-overlapping authority."
        ),
        scope="governance_authority.py",
        distinguished_from=(
            "Hierarchy — authority is peer-based, not parent-child",
            "Control — authority means responsibility, not absolute control",
            "Permission — authority declares what a component does, not what it may do",
        ),
        usage_examples=(
            "GOVERNANCE_AUTHORITY in governance_authority.py",
            "RUNTIME_AUTHORITY in governance_authority.py",
            "RESPONSIBILITY BOUNDARY docstrings in governance.py and runtime_core.py",
        ),
    ),

    "hybrid": SemanticEntry(
        term="hybrid",
        definition=(
            "A merged contract produced by combining one QUANTUM and one "
            "CLASSICAL contract via confidence-weighted selection.  The merge "
            "strategy, not the execution path, is what makes it hybrid.  Once "
            "merged, a HYBRID contract traverses the same RuntimeCore.execute() "
            "code path as any other contract — no special hybrid execution exists."
        ),
        scope="adapters.py (HybridAdapter)",
        distinguished_from=(
            "Mixed execution — hybrid is a contract type, not an execution mode",
            "Ensemble — hybrid picks one primary, not a statistical ensemble",
            "Quantum-classical — hybrid is the merge result, not the merger process",
        ),
        usage_examples=(
            "HybridAdapter.adapt() in adapters.py",
            "ProducerType.HYBRID in execution_contract.py",
            "selection_strategy='confidence_weighted' in HybridAdapter payload",
        ),
    ),

    "execution": SemanticEntry(
        term="execution",
        definition=(
            "The act of processing a ComputationExecutionContract through "
            "RuntimeCore.execute().  Produces an ExecutionResult containing an "
            "ACK string, runtime hash, confidence, and timestamp.  Execution is "
            "blind to producer type \u2014 quantum and classical contracts traverse "
            "the exact same code path with no branching."
        ),
        scope="runtime_core.py",
        distinguished_from=(
            "Governance \u2014 governance gates execution but does not perform it",
            "Adaptation \u2014 adapters create contracts; execution consumes them",
            "Observation \u2014 trace recording happens after execution, not during it",
        ),
        usage_examples=(
            "RuntimeCore.execute() in runtime_core.py",
            "ExecutionResult dataclass in runtime_core.py",
            "Phase 3 in runtime_demo.py",
        ),
    ),

    "producer": SemanticEntry(
        term="producer",
        definition=(
            "A system that generates raw output before adaptation into a contract. "
            "Three producer types exist: QUANTUM (Qiskit Aer simulator), CLASSICAL "
            "(deterministic optimizer), and HYBRID (merger of quantum + classical). "
            "The producer creates raw data; the adapter transforms it into a "
            "ComputationExecutionContract.  RuntimeCore never inspects or branches "
            "on producer type."
        ),
        scope="quantum_producer.py, adapters.py, execution_contract.py",
        distinguished_from=(
            "Adapter \u2014 the adapter transforms raw output into a contract; "
            "the producer creates the raw output",
            "RuntimeCore \u2014 the runtime executes contracts; it does not produce them",
            "Contract \u2014 the contract is the envelope; the producer is the source",
        ),
        usage_examples=(
            "run_quantum_producer() in quantum_producer.py",
            "ProducerType enum in execution_contract.py",
            "QuantumAdapter, ClassicalAdapter in adapters.py",
        ),
    ),

    "runtime": SemanticEntry(
        term="runtime",
        definition=(
            "The blind execution engine (RuntimeCore) that processes any "
            "ComputationExecutionContract through an identical, producer-agnostic "
            "code path.  The runtime owns confidence threshold enforcement, replay "
            "detection, ACK generation, and hash computation.  It does NOT own "
            "producer authorization, contract version policy, or violation recording."
        ),
        scope="runtime_core.py",
        distinguished_from=(
            "Governance \u2014 governance is policy enforcement; runtime is execution",
            "Execution \u2014 execution is the act; runtime is the engine",
            "Observation \u2014 the runtime produces results; the trace store records them",
        ),
        usage_examples=(
            "RuntimeCore class in runtime_core.py",
            "RESPONSIBILITY BOUNDARY docstring in runtime_core.py",
            "RUNTIME_AUTHORITY in governance_authority.py",
        ),
    ),

    "trace": SemanticEntry(
        term="trace",
        definition=(
            "An immutable, hash-verified record of a single step in the execution "
            "pipeline.  Each TraceEntry contains: trace_id (linking to contract), "
            "trace_type (execution, adapter, producer_lineage, contract_lineage, "
            "governance), data (step-specific payload), sequence (deterministic "
            "ordering), entry_hash (SHA-256 integrity), and timestamp (observability "
            "anchor).  Traces are append-only and frozen after creation."
        ),
        scope="observability.py",
        distinguished_from=(
            "Log \u2014 a trace is structured, hash-verified, and part of a "
            "reconstructible chain; a log is unstructured text",
            "Contract \u2014 a contract is input to execution; a trace is output "
            "of observation",
            "Proof \u2014 a trace is evidence; proof is the conclusion drawn from traces",
        ),
        usage_examples=(
            "TraceEntry dataclass in observability.py",
            "TraceStore.record_*() methods in observability.py",
            "ReplayProof in observability.py",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def lookup(term: str) -> SemanticEntry:
    """
    Look up a term in the semantic registry.

    Raises KeyError if the term is not registered.
    """
    key = term.lower()
    if key not in SEMANTIC_REGISTRY:
        raise KeyError(
            f"Term '{term}' is not registered in the semantic registry. "
            f"Registered terms: {sorted(SEMANTIC_REGISTRY.keys())}"
        )
    return SEMANTIC_REGISTRY[key]


def all_terms() -> list[str]:
    """Return all registered terms."""
    return sorted(SEMANTIC_REGISTRY.keys())


def validate_registry() -> dict:
    """
    Validate the semantic registry for completeness.

    Returns a dict with validation results.
    """
    required_terms = {
        "contract", "replay", "confidence", "truth",
        "governance", "execution", "authority", "hybrid",
        "producer", "runtime", "trace",
        # Also included but not in the mandatory-11 list:
        "determinism",
    }
    registered = set(SEMANTIC_REGISTRY.keys())
    missing = required_terms - registered
    extra = registered - required_terms

    return {
        "complete": len(missing) == 0,
        "registered": sorted(registered),
        "missing": sorted(missing),
        "extra": sorted(extra),
    }
