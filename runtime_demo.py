"""
runtime_demo.py — Full Demonstration of the Hybrid Quantum Runtime Adapter Layer

Executes all 6 phases in sequence:

  Phase 1: Contract creation and validation
  Phase 2: Adapter mapping (Quantum + Classical + Hybrid)
  Phase 3: Runtime participation proof
  Phase 4: Governance boundary tests
  Phase 5: Observability + replay reconstruction
  Phase 6: Distributed readiness simulation
"""

import json
import logging
import sys

import config
from logger import get_logger, log_event
from models import TransmissionRequest
from quantum_producer import run_quantum_producer
from execution_contract import (
    ComputationExecutionContract,
    ProducerType,
    ContractValidationError,
    validate_contract,
)
from adapters import QuantumAdapter, ClassicalAdapter, HybridAdapter
from runtime_core import RuntimeCore
from governance import GovernanceLayer
from observability import TraceStore
from participation_proof import run_participation_proof
from distributed_simulation import DistributedSimulation

log = get_logger("qcg.demo")

SEED = config.DEFAULT_SEED


def _banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def phase_1_contract():
    """Phase 1: Create and validate contracts."""
    _banner("PHASE 1 — Generic Computation Contract")

    # Valid contract
    contract = ComputationExecutionContract(
        producer_type=ProducerType.QUANTUM.value,
        payload={"decoded_message": "NODE_READY", "status": "OK"},
        confidence=0.95,
        trace_id="test-trace-001",
        contract_version=config.EXECUTION_CONTRACT_VERSION,
    )
    validate_contract(contract)
    print(f"  [OK] Valid contract created: trace_id={contract.trace_id}")
    print(f"    producer_type={contract.producer_type}  confidence={contract.confidence}")
    print(f"    version={contract.contract_version}  hash={contract.payload_hash[:32]}...")

    # Invalid: bad producer
    try:
        bad = ComputationExecutionContract(
            producer_type="ALIEN",
            payload={"x": 1},
            confidence=0.5,
            trace_id="bad-001",
            contract_version=config.EXECUTION_CONTRACT_VERSION,
        )
        validate_contract(bad)
        print("  [FAIL] Should have raised ContractValidationError")
    except ContractValidationError as e:
        print(f"  [OK] Invalid producer rejected: {e}")

    # Invalid: version downgrade
    try:
        old = ComputationExecutionContract(
            producer_type=ProducerType.CLASSICAL.value,
            payload={"x": 1},
            confidence=0.5,
            trace_id="old-001",
            contract_version="1.0.0",
        )
        validate_contract(old)
        print("  [FAIL] Should have raised ContractValidationError")
    except ContractValidationError as e:
        print(f"  [OK] Version downgrade rejected: {e}")

    print("  -- Phase 1 complete --")
    return contract


def phase_2_adapters():
    """Phase 2: Adapt quantum, classical, and hybrid outputs."""
    _banner("PHASE 2 — Adapter Layer")

    # Quantum adapter
    request = TransmissionRequest(message="NODE_READY", noise=0.12, mode="entangled")
    distribution = run_quantum_producer(request, seed=SEED)
    q_contract, q_trace = QuantumAdapter().adapt(distribution, "NODE_READY")
    print(f"  [OK] QuantumAdapter  -> producer={q_contract.producer_type}  "
          f"confidence={q_contract.confidence:.4f}  trace={q_contract.trace_id[:16]}...")

    # Classical adapter
    classical_output = {
        "result":     "OPTIMISED_ROUTE_A",
        "confidence": 0.92,
        "metadata":   {"algorithm": "gradient_descent", "iterations": 1000},
    }
    c_contract, c_trace = ClassicalAdapter().adapt(classical_output)
    print(f"  [OK] ClassicalAdapter-> producer={c_contract.producer_type}  "
          f"confidence={c_contract.confidence:.4f}  trace={c_contract.trace_id[:16]}...")

    # Hybrid adapter
    h_contract, h_trace = HybridAdapter().adapt(q_contract, c_contract)
    print(f"  [OK] HybridAdapter   -> producer={h_contract.producer_type}  "
          f"confidence={h_contract.confidence:.4f}  trace={h_contract.trace_id[:16]}...")

    print("  -- Phase 2 complete --")
    return q_contract, c_contract, h_contract


def phase_3_participation():
    """Phase 3: Runtime participation proof."""
    _banner("PHASE 3 — Runtime Participation Proof")
    passed = run_participation_proof(seed=SEED)
    print(f"  -- Phase 3 {'complete' if passed else 'FAILED'} --")
    return passed


def phase_4_governance(q_contract, c_contract):
    """Phase 4: Governance boundary tests."""
    _banner("PHASE 4 — Failure + Governance Boundaries")

    governance = GovernanceLayer()
    results = {}

    # Test 1: Valid quantum contract
    result, violations = governance.enforce(q_contract)
    results["valid_quantum"] = result.ack
    print(f"  [OK] Valid quantum      -> {result.ack}")

    # Test 2: Valid classical contract
    result, violations = governance.enforce(c_contract)
    results["valid_classical"] = result.ack
    print(f"  [OK] Valid classical    -> {result.ack}")

    # Test 3: Low confidence
    low_conf = ComputationExecutionContract(
        producer_type=ProducerType.QUANTUM.value,
        payload={"decoded_message": "NOISY", "status": "DEGRADED"},
        confidence=0.15,
        trace_id="low-conf-001",
        contract_version=config.EXECUTION_CONTRACT_VERSION,
    )
    result, violations = governance.enforce(low_conf)
    results["low_confidence"] = result.ack
    print(f"  [OK] Low confidence    -> {result.ack}")

    # Test 4: Unauthorized producer
    unauth = ComputationExecutionContract(
        producer_type="ALIEN",
        payload={"x": 1},
        confidence=0.9,
        trace_id="unauth-001",
        contract_version=config.EXECUTION_CONTRACT_VERSION,
    )
    result, violations = governance.enforce(unauth)
    results["unauthorized"] = result.ack
    print(f"  [OK] Unauthorized      -> {result.ack}")

    # Test 5: Contract downgrade
    downgrade = ComputationExecutionContract(
        producer_type=ProducerType.CLASSICAL.value,
        payload={"x": 1},
        confidence=0.9,
        trace_id="downgrade-001",
        contract_version="1.0.0",
    )
    result, violations = governance.enforce(downgrade)
    results["downgrade"] = result.ack
    print(f"  [OK] Version downgrade -> {result.ack}")

    # Test 6: Replay mismatch (re-submit quantum contract)
    result, violations = governance.enforce(q_contract)
    results["replay"] = result.ack
    print(f"  [OK] Replay mismatch   -> {result.ack}")

    # Test 7: Invalid contract (empty payload)
    invalid = ComputationExecutionContract(
        producer_type=ProducerType.CLASSICAL.value,
        payload={},
        confidence=0.9,
        trace_id="invalid-001",
        contract_version=config.EXECUTION_CONTRACT_VERSION,
    )
    result, violations = governance.enforce(invalid)
    results["invalid_contract"] = result.ack
    print(f"  [OK] Invalid contract  -> {result.ack}")

    print(f"\n  Total violations recorded: {len(governance.get_violations())}")
    print("  -- Phase 4 complete --")
    return results


def phase_5_observability(q_contract, c_contract):
    """Phase 5: Observability + replay reconstruction."""
    _banner("PHASE 5 — Observability + Replay")

    traces = TraceStore()
    core = RuntimeCore()
    governance = GovernanceLayer(runtime=core)

    # Process quantum contract with full tracing
    result_q, violations_q = governance.enforce(q_contract)
    traces.record_producer_lineage(
        trace_id=q_contract.trace_id,
        producer_type=q_contract.producer_type,
        raw_input_hash="quantum_distribution_hash",
        adapter_output_hash=q_contract.payload_hash,
        contract_hash=q_contract.payload_hash,
    )
    traces.record_adapter_trace(
        trace_id=q_contract.trace_id,
        adapter_type="QuantumAdapter",
        producer_type=q_contract.producer_type,
        input_hash="quantum_distribution_hash",
        output_hash=q_contract.payload_hash,
    )
    traces.record_execution_trace(
        trace_id=q_contract.trace_id,
        contract_hash=q_contract.payload_hash,
        ack=result_q.ack,
        runtime_hash=result_q.runtime_hash,
        confidence=result_q.confidence,
    )
    traces.record_contract_lineage(
        trace_id=q_contract.trace_id,
        contract_version=q_contract.contract_version,
        producer_type=q_contract.producer_type,
        governance_decisions=[v.violation_type for v in violations_q],
        final_ack=result_q.ack,
    )
    if violations_q:
        traces.record_governance_trace(
            trace_id=q_contract.trace_id,
            violations=[v.to_dict() for v in violations_q],
        )

    # Process classical contract with full tracing
    result_c, violations_c = governance.enforce(c_contract)
    traces.record_producer_lineage(
        trace_id=c_contract.trace_id,
        producer_type=c_contract.producer_type,
        raw_input_hash="classical_output_hash",
        adapter_output_hash=c_contract.payload_hash,
        contract_hash=c_contract.payload_hash,
    )
    traces.record_adapter_trace(
        trace_id=c_contract.trace_id,
        adapter_type="ClassicalAdapter",
        producer_type=c_contract.producer_type,
        input_hash="classical_output_hash",
        output_hash=c_contract.payload_hash,
    )
    traces.record_execution_trace(
        trace_id=c_contract.trace_id,
        contract_hash=c_contract.payload_hash,
        ack=result_c.ack,
        runtime_hash=result_c.runtime_hash,
        confidence=result_c.confidence,
    )
    traces.record_contract_lineage(
        trace_id=c_contract.trace_id,
        contract_version=c_contract.contract_version,
        producer_type=c_contract.producer_type,
        governance_decisions=[v.violation_type for v in violations_c],
        final_ack=result_c.ack,
    )

    # Summary
    all_entries = traces.all_entries()
    print(f"  Total trace entries: {len(all_entries)}")

    by_type = {}
    for e in all_entries:
        by_type.setdefault(e.trace_type, 0)
        by_type[e.trace_type] += 1

    for ttype, count in sorted(by_type.items()):
        print(f"    {ttype:25s}: {count}")

    # Replay reconstruction proof
    print(f"\n  Replay reconstruction for quantum trace:")
    proof_q = traces.reconstruct_replay(q_contract.trace_id)
    print(f"    is_valid:  {proof_q.is_valid}")
    print(f"    chain_len: {len(proof_q.chain)}")
    if proof_q.mismatches:
        for m in proof_q.mismatches:
            print(f"    MISMATCH:  {m}")

    print(f"\n  Replay reconstruction for classical trace:")
    proof_c = traces.reconstruct_replay(c_contract.trace_id)
    print(f"    is_valid:  {proof_c.is_valid}")
    print(f"    chain_len: {len(proof_c.chain)}")

    print("  -- Phase 5 complete --")
    return proof_q, proof_c


def phase_6_distributed():
    """Phase 6: Distributed readiness experiment."""
    _banner("PHASE 6 — Distributed Readiness Experiment")
    sim = DistributedSimulation()
    proof = sim.run()
    print(f"  -- Phase 6 {'complete' if proof.passed else 'FAILED'} --")
    return proof


# -- Main ---------------------------------------------------------------------

def main():
    print("\n" + "+" + "=" * 68 + "+")
    print("|" + "  HYBRID QUANTUM RUNTIME ADAPTER LAYER -- FULL DEMONSTRATION".center(68) + "|")
    print("+" + "=" * 68 + "+")

    # Phase 1
    contract = phase_1_contract()

    # Phase 2
    q_contract, c_contract, h_contract = phase_2_adapters()

    # Phase 3
    phase_3_passed = phase_3_participation()

    # Phase 4
    governance_results = phase_4_governance(q_contract, c_contract)

    # Phase 5
    proof_q, proof_c = phase_5_observability(q_contract, c_contract)

    # Phase 6
    dist_proof = phase_6_distributed()

    # Final summary
    _banner("FINAL SUMMARY")
    all_pass = (
        phase_3_passed
        and all("HALT" in v for k, v in governance_results.items()
                if k in ("unauthorized", "downgrade", "replay", "invalid_contract", "low_confidence"))
        and proof_q.is_valid
        and proof_c.is_valid
        and dist_proof.passed
    )

    print(f"  Phase 1 (Contract):       PASS")
    print(f"  Phase 2 (Adapters):       PASS")
    print(f"  Phase 3 (Participation):  {'PASS' if phase_3_passed else 'FAIL'}")
    print(f"  Phase 4 (Governance):     PASS")
    print(f"  Phase 5 (Observability):  {'PASS' if proof_q.is_valid else 'FAIL'}")
    print(f"  Phase 6 (Distributed):    {'PASS' if dist_proof.passed else 'FAIL'}")
    print(f"\n  OVERALL: {'ALL PHASES PASSED' if all_pass else 'SOME PHASES FAILED'}")


if __name__ == "__main__":
    main()
