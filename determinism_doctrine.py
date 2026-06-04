"""
determinism_doctrine.py — Formal Determinism Classification

Defines three determinism categories and provides the DeterminismOracle
for structurally classifying and comparing system outputs.

Determinism Categories
----------------------
EXECUTION    : RuntimeCore.execute() output.  Given identical contract input,
               the deterministic projection (ack, runtime_hash, confidence,
               contract_trace_id, producer_type) MUST be identical.
               ``execution_timestamp`` is OBSERVABILITY metadata — excluded.

CONTRACT     : ComputationExecutionContract fields.  payload_hash, trace_id,
               confidence, payload, producer_type, contract_version,
               execution_constraints are DETERMINISTIC.
               ``timestamp`` is OBSERVABILITY metadata — excluded.

OBSERVABILITY: Trace entries, replay proofs, governance violations.
               entry_hash is deterministic (computed from deterministic data
               + timestamp).  Timestamps are observability data that anchor
               traces in wall-clock time but are NOT required for
               deterministic reproducibility of execution outcomes.
"""

from dataclasses import dataclass, fields, asdict
from typing import Any


# ---------------------------------------------------------------------------
# Field classification
# ---------------------------------------------------------------------------

class FieldClass:
    """Classification labels for dataclass fields."""
    DETERMINISTIC = "deterministic"
    OBSERVABILITY = "observability"
    METADATA      = "metadata"


# Registry: (fully-qualified class name, field name) -> classification
_FIELD_CLASSIFICATIONS: dict[tuple[str, str], str] = {
    # ComputationExecutionContract
    ("ComputationExecutionContract", "producer_type"):         FieldClass.DETERMINISTIC,
    ("ComputationExecutionContract", "payload"):               FieldClass.DETERMINISTIC,
    ("ComputationExecutionContract", "confidence"):            FieldClass.DETERMINISTIC,
    ("ComputationExecutionContract", "trace_id"):              FieldClass.DETERMINISTIC,
    ("ComputationExecutionContract", "contract_version"):      FieldClass.DETERMINISTIC,
    ("ComputationExecutionContract", "execution_constraints"): FieldClass.DETERMINISTIC,
    ("ComputationExecutionContract", "payload_hash"):          FieldClass.DETERMINISTIC,
    ("ComputationExecutionContract", "timestamp"):             FieldClass.OBSERVABILITY,

    # ExecutionResult
    ("ExecutionResult", "contract_trace_id"):  FieldClass.DETERMINISTIC,
    ("ExecutionResult", "producer_type"):      FieldClass.DETERMINISTIC,
    ("ExecutionResult", "ack"):                FieldClass.DETERMINISTIC,
    ("ExecutionResult", "confidence"):         FieldClass.DETERMINISTIC,
    ("ExecutionResult", "runtime_hash"):       FieldClass.DETERMINISTIC,
    ("ExecutionResult", "execution_timestamp"): FieldClass.OBSERVABILITY,

    # GovernanceViolation
    ("GovernanceViolation", "violation_type"): FieldClass.DETERMINISTIC,
    ("GovernanceViolation", "severity"):       FieldClass.DETERMINISTIC,
    ("GovernanceViolation", "trace_id"):       FieldClass.DETERMINISTIC,
    ("GovernanceViolation", "details"):        FieldClass.DETERMINISTIC,
    ("GovernanceViolation", "timestamp"):      FieldClass.OBSERVABILITY,

    # TraceEntry
    ("TraceEntry", "trace_id"):   FieldClass.DETERMINISTIC,
    ("TraceEntry", "trace_type"): FieldClass.DETERMINISTIC,
    ("TraceEntry", "data"):       FieldClass.DETERMINISTIC,
    ("TraceEntry", "entry_hash"): FieldClass.OBSERVABILITY,
    ("TraceEntry", "timestamp"):  FieldClass.OBSERVABILITY,
    ("TraceEntry", "sequence"):   FieldClass.DETERMINISTIC,

    # ReplayProof
    ("ReplayProof", "trace_id"):   FieldClass.DETERMINISTIC,
    ("ReplayProof", "is_valid"):   FieldClass.DETERMINISTIC,
    ("ReplayProof", "chain"):      FieldClass.DETERMINISTIC,
    ("ReplayProof", "mismatches"): FieldClass.DETERMINISTIC,
    ("ReplayProof", "timestamp"):  FieldClass.OBSERVABILITY,

    # DistributedProof
    ("DistributedProof", "passed"):              FieldClass.DETERMINISTIC,
    ("DistributedProof", "node_count"):           FieldClass.DETERMINISTIC,
    ("DistributedProof", "producer_count"):       FieldClass.DETERMINISTIC,
    ("DistributedProof", "contracts_processed"):  FieldClass.DETERMINISTIC,
    ("DistributedProof", "hash_agreement"):       FieldClass.DETERMINISTIC,
    ("DistributedProof", "node_ledgers"):         FieldClass.DETERMINISTIC,
    ("DistributedProof", "propagation_log"):      FieldClass.DETERMINISTIC,
    ("DistributedProof", "scope"):                FieldClass.METADATA,
    ("DistributedProof", "timestamp"):            FieldClass.OBSERVABILITY,

    # AdapterTrace
    ("AdapterTrace", "adapter_type"):    FieldClass.DETERMINISTIC,
    ("AdapterTrace", "producer_type"):   FieldClass.DETERMINISTIC,
    ("AdapterTrace", "input_type"):      FieldClass.DETERMINISTIC,
    ("AdapterTrace", "input_hash"):      FieldClass.DETERMINISTIC,
    ("AdapterTrace", "output_trace_id"): FieldClass.DETERMINISTIC,
    ("AdapterTrace", "output_hash"):     FieldClass.DETERMINISTIC,
    ("AdapterTrace", "timestamp"):       FieldClass.OBSERVABILITY,
}


# ---------------------------------------------------------------------------
# Determinism verdict
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeterminismVerdict:
    """Result of a determinism comparison."""
    passed:             bool
    category:           str      # "execution" | "contract"
    deterministic_match: bool    # True if deterministic projections match
    observability_diffs: dict    # Fields that differ in observability layer
    evidence:           dict     # Full comparison evidence


# ---------------------------------------------------------------------------
# DeterminismOracle
# ---------------------------------------------------------------------------

class DeterminismOracle:
    """
    Classifies dataclass fields and provides deterministic-projection
    extraction for reproducibility comparisons.

    Usage
    -----
    >>> oracle = DeterminismOracle()
    >>> proj = oracle.extract_deterministic_projection(execution_result)
    >>> verdict = oracle.assert_execution_determinism(result_a, result_b)
    """

    def classify_field(self, class_name: str, field_name: str) -> str:
        """
        Return the determinism classification of a field.

        Returns 'deterministic', 'observability', or 'metadata'.
        Raises KeyError if the field is not registered.
        """
        key = (class_name, field_name)
        if key not in _FIELD_CLASSIFICATIONS:
            raise KeyError(
                f"Field ({class_name}, {field_name}) not registered in "
                f"determinism doctrine."
            )
        return _FIELD_CLASSIFICATIONS[key]

    def extract_deterministic_projection(self, obj: Any) -> dict:
        """
        Strip observability and metadata fields from a dataclass,
        returning only the deterministic core.
        """
        class_name = type(obj).__name__
        result = {}
        for f in fields(obj):
            key = (class_name, f.name)
            classification = _FIELD_CLASSIFICATIONS.get(key, FieldClass.DETERMINISTIC)
            if classification == FieldClass.DETERMINISTIC:
                result[f.name] = getattr(obj, f.name)
        return result

    def extract_observability_projection(self, obj: Any) -> dict:
        """Extract only observability fields from a dataclass."""
        class_name = type(obj).__name__
        result = {}
        for f in fields(obj):
            key = (class_name, f.name)
            classification = _FIELD_CLASSIFICATIONS.get(key, FieldClass.DETERMINISTIC)
            if classification == FieldClass.OBSERVABILITY:
                result[f.name] = getattr(obj, f.name)
        return result

    def assert_execution_determinism(
        self, result_a: Any, result_b: Any,
    ) -> DeterminismVerdict:
        """
        Compare two ExecutionResult objects for execution determinism.

        Deterministic fields must match exactly.
        Observability fields (execution_timestamp) may differ.
        """
        det_a = self.extract_deterministic_projection(result_a)
        det_b = self.extract_deterministic_projection(result_b)
        obs_a = self.extract_observability_projection(result_a)
        obs_b = self.extract_observability_projection(result_b)

        deterministic_match = det_a == det_b
        observability_diffs = {
            k: {"a": obs_a.get(k), "b": obs_b.get(k)}
            for k in set(obs_a) | set(obs_b)
            if obs_a.get(k) != obs_b.get(k)
        }

        return DeterminismVerdict(
            passed=deterministic_match,
            category="execution",
            deterministic_match=deterministic_match,
            observability_diffs=observability_diffs,
            evidence={
                "deterministic_a": det_a,
                "deterministic_b": det_b,
                "observability_a": obs_a,
                "observability_b": obs_b,
            },
        )

    def assert_contract_determinism(
        self, contract_a: Any, contract_b: Any,
    ) -> DeterminismVerdict:
        """
        Compare two ComputationExecutionContract objects for contract
        determinism.
        """
        det_a = self.extract_deterministic_projection(contract_a)
        det_b = self.extract_deterministic_projection(contract_b)
        obs_a = self.extract_observability_projection(contract_a)
        obs_b = self.extract_observability_projection(contract_b)

        deterministic_match = det_a == det_b
        observability_diffs = {
            k: {"a": obs_a.get(k), "b": obs_b.get(k)}
            for k in set(obs_a) | set(obs_b)
            if obs_a.get(k) != obs_b.get(k)
        }

        return DeterminismVerdict(
            passed=deterministic_match,
            category="contract",
            deterministic_match=deterministic_match,
            observability_diffs=observability_diffs,
            evidence={
                "deterministic_a": det_a,
                "deterministic_b": det_b,
                "observability_a": obs_a,
                "observability_b": obs_b,
            },
        )
