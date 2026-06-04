"""
replay_doctrine.py — Canonical Replay Semantics

Defines the five replay targets and provides a ReplayEngine that can
independently verify deterministic reproducibility at each level.

Replay Targets
--------------
PAYLOAD     : Re-derive contract from the same raw producer output.
              Proves adapter determinism.

CONTRACT    : Re-execute the same ComputationExecutionContract through
              RuntimeCore.  Proves runtime determinism.

EXECUTION   : Re-run governance + runtime from the same contract.
              Proves governance + runtime determinism.

TRACE       : Verify that the meaning (ACK outcome, confidence band) is
              preserved even if observability timestamps differ.
              Proves semantic equivalence.

DISTRIBUTED : Verify that N independent nodes produce identical results
              from the same contract.  Proves distributed determinism.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from determinism_doctrine import DeterminismOracle


# ---------------------------------------------------------------------------
# Replay target taxonomy
# ---------------------------------------------------------------------------

class ReplayTarget(str, Enum):
    """Canonical replay target taxonomy."""
    PAYLOAD     = "PAYLOAD"
    CONTRACT    = "CONTRACT"
    EXECUTION   = "EXECUTION"
    TRACE       = "TRACE"
    DISTRIBUTED = "DISTRIBUTED"


# ---------------------------------------------------------------------------
# Replay verdict
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReplayVerdict:
    """Result of a replay verification."""
    target:              ReplayTarget
    passed:              bool
    deterministic_match: bool
    observability_diffs: dict
    evidence:            dict


# ---------------------------------------------------------------------------
# Replay engine
# ---------------------------------------------------------------------------

class ReplayEngine:
    """
    Executes canonical replay verifications at each target level.

    Each replay method re-runs the relevant pipeline segment and compares
    deterministic projections.  Observability differences (timestamps)
    are recorded but do not affect the pass/fail verdict.
    """

    def __init__(self):
        self._oracle = DeterminismOracle()

    def replay_payload(
        self,
        raw_input: Any,
        adapter: Any,
        message: str,
    ) -> ReplayVerdict:
        """
        PAYLOAD replay: re-derive contract from the same raw producer output.

        Proves that the adapter layer is deterministic — same raw input
        always produces the same contract (excluding timestamps).
        """
        # Run adapter twice
        if hasattr(adapter, "adapt"):
            # QuantumAdapter takes (distribution, message)
            # ClassicalAdapter takes (classical_output)
            import inspect
            sig = inspect.signature(adapter.adapt)
            params = list(sig.parameters.keys())
            if len(params) >= 2 and "message" not in str(sig):
                # QuantumAdapter: adapt(distribution, original_message)
                contract_a, _ = adapter.adapt(raw_input, message)
                contract_b, _ = adapter.adapt(raw_input, message)
            else:
                # ClassicalAdapter: adapt(classical_output)
                contract_a, _ = adapter.adapt(raw_input)
                contract_b, _ = adapter.adapt(raw_input)
        else:
            raise ValueError("Adapter must have an 'adapt' method.")

        verdict = self._oracle.assert_contract_determinism(contract_a, contract_b)
        return ReplayVerdict(
            target=ReplayTarget.PAYLOAD,
            passed=verdict.passed,
            deterministic_match=verdict.deterministic_match,
            observability_diffs=verdict.observability_diffs,
            evidence=verdict.evidence,
        )

    def replay_contract(
        self,
        contract: Any,
        runtime: Any,
    ) -> ReplayVerdict:
        """
        CONTRACT replay: re-execute the same contract through RuntimeCore.

        Proves that RuntimeCore.execute() is deterministic — same contract
        always produces the same ExecutionResult (excluding timestamps).

        Note: RuntimeCore has a replay guard (trace_id registry) that will
        HALT on duplicate trace_ids.  The runtime must be reset between
        calls, or two separate instances must be used.
        """
        from runtime_core import RuntimeCore

        # Use two separate RuntimeCore instances to avoid replay guard
        core_a = RuntimeCore()
        core_b = RuntimeCore()

        result_a = core_a.execute(contract)
        result_b = core_b.execute(contract)

        verdict = self._oracle.assert_execution_determinism(result_a, result_b)
        return ReplayVerdict(
            target=ReplayTarget.CONTRACT,
            passed=verdict.passed,
            deterministic_match=verdict.deterministic_match,
            observability_diffs=verdict.observability_diffs,
            evidence=verdict.evidence,
        )

    def replay_execution(
        self,
        contract: Any,
        governance_layer_factory: Any = None,
    ) -> ReplayVerdict:
        """
        EXECUTION replay: re-run governance + runtime from the same contract.

        Proves governance + runtime determinism.  Both layers produce
        identical deterministic outputs for the same input.
        """
        from runtime_core import RuntimeCore
        from governance import GovernanceLayer

        if governance_layer_factory is None:
            governance_layer_factory = lambda: GovernanceLayer(runtime=RuntimeCore())

        gov_a = governance_layer_factory()
        gov_b = governance_layer_factory()

        result_a, violations_a = gov_a.enforce(contract)
        result_b, violations_b = gov_b.enforce(contract)

        verdict = self._oracle.assert_execution_determinism(result_a, result_b)

        # Also compare violation types (deterministic)
        v_types_a = sorted([v.violation_type for v in violations_a])
        v_types_b = sorted([v.violation_type for v in violations_b])
        violations_match = v_types_a == v_types_b

        return ReplayVerdict(
            target=ReplayTarget.EXECUTION,
            passed=verdict.passed and violations_match,
            deterministic_match=verdict.deterministic_match and violations_match,
            observability_diffs=verdict.observability_diffs,
            evidence={
                **verdict.evidence,
                "violations_a": v_types_a,
                "violations_b": v_types_b,
                "violations_match": violations_match,
            },
        )

    def replay_distributed(
        self,
        contract: Any,
        node_count: int = 3,
    ) -> ReplayVerdict:
        """
        DISTRIBUTED replay: verify N independent nodes produce identical
        results from the same contract.

        Proves distributed determinism (at simulation level).
        """
        from runtime_core import RuntimeCore
        from governance import GovernanceLayer

        results = []
        for _ in range(node_count):
            core = RuntimeCore()
            gov = GovernanceLayer(runtime=core)
            result, _ = gov.enforce(contract)
            results.append(result)

        # Compare all against the first
        reference = results[0]
        all_match = True
        diffs = {}
        for i, result in enumerate(results[1:], start=1):
            verdict = self._oracle.assert_execution_determinism(reference, result)
            if not verdict.passed:
                all_match = False
                diffs[f"node_{i}"] = verdict.observability_diffs

        return ReplayVerdict(
            target=ReplayTarget.DISTRIBUTED,
            passed=all_match,
            deterministic_match=all_match,
            observability_diffs=diffs,
            evidence={
                "node_count": node_count,
                "reference_ack": reference.ack,
                "reference_hash": reference.runtime_hash,
                "all_acks": [r.ack for r in results],
                "all_hashes": [r.runtime_hash for r in results],
            },
        )

    def replay_trace(
        self,
        result_a: Any,
        result_b: Any,
    ) -> ReplayVerdict:
        """
        SEMANTIC replay: verify that two results have the same meaning
        (ACK outcome category, confidence band) even if observability
        timestamps differ.

        Semantic equivalence rules:
        - ACK prefix must match (ACK:OK == ACK:OK, HALT:X == HALT:X)
        - Confidence must be in the same band (OK / DEGRADED / HALT)
        - Producer type must match
        """
        import config

        # ACK semantic equivalence: same prefix
        ack_a_prefix = result_a.ack.split(":")[0] + ":" + result_a.ack.split(":")[1] if ":" in result_a.ack else result_a.ack
        ack_b_prefix = result_b.ack.split(":")[0] + ":" + result_b.ack.split(":")[1] if ":" in result_b.ack else result_b.ack
        ack_match = ack_a_prefix == ack_b_prefix

        # Confidence band equivalence
        def _band(conf: float) -> str:
            if conf < config.CORRUPTION_THRESHOLD:
                return "HALT"
            elif conf < config.CONFIDENCE_THRESHOLD:
                return "DEGRADED"
            return "OK"

        band_a = _band(result_a.confidence)
        band_b = _band(result_b.confidence)
        band_match = band_a == band_b

        # Producer type equivalence
        producer_match = result_a.producer_type == result_b.producer_type

        passed = ack_match and band_match and producer_match

        return ReplayVerdict(
            target=ReplayTarget.TRACE,
            passed=passed,
            deterministic_match=passed,
            observability_diffs={
                "ack_a": result_a.ack,
                "ack_b": result_b.ack,
                "confidence_a": result_a.confidence,
                "confidence_b": result_b.confidence,
            },
            evidence={
                "ack_prefix_a": ack_a_prefix,
                "ack_prefix_b": ack_b_prefix,
                "ack_match": ack_match,
                "band_a": band_a,
                "band_b": band_b,
                "band_match": band_match,
                "producer_match": producer_match,
            },
        )
