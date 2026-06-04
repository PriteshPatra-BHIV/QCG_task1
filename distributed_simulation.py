"""
distributed_simulation.py — Phase 6: Distributed Readiness Experiment

Simulates a distributed runtime without networking.

SCOPE DECLARATION
-----------------
What this proves:
    Deterministic hash agreement across simulated independent nodes
    processing identical contract sequences in a single process.

What this does NOT prove:
    - Network partition tolerance
    - Real inter-node communication
    - Byzantine fault tolerance
    - Clock synchronization
    - Consensus protocol correctness
    - Message delivery guarantees

Classification:
    SIMULATION-LEVEL verification.
    Pre-requisite for distributed execution readiness.
    NOT equivalent to distributed execution readiness.

Simulation topology:
    - 2 producers  : one QuantumAdapter, one ClassicalAdapter
    - 3 nodes      : each with its own RuntimeCore + GovernanceLayer + TraceStore
    - Ordered propagation : contracts propagate Node_1 → Node_2 → Node_3
    - Hash agreement      : all 3 nodes must agree on the final execution hash
"""

import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

import config
from logger import get_logger, log_event
from models import TransmissionRequest
from quantum_producer import run_quantum_producer
from adapters import QuantumAdapter, ClassicalAdapter
from execution_contract import ComputationExecutionContract
from runtime_core import RuntimeCore, ExecutionResult
from governance import GovernanceLayer
from observability import TraceStore

log = get_logger("qcg.distributed")


# ---------------------------------------------------------------------------
# Simulated Node
# ---------------------------------------------------------------------------

@dataclass
class SimulatedNode:
    """One node in the simulated distributed network."""
    node_id:    str
    runtime:    RuntimeCore    = field(default_factory=RuntimeCore)
    governance: GovernanceLayer | None = None
    traces:     TraceStore     = field(default_factory=TraceStore)
    ledger:     list           = field(default_factory=list)  # ordered hash chain

    def __post_init__(self):
        if self.governance is None:
            self.governance = GovernanceLayer(runtime=self.runtime)

    def process(self, contract: ComputationExecutionContract) -> ExecutionResult:
        """
        Process a contract through governance → runtime, record traces,
        and append to the local ledger.
        """
        result, violations = self.governance.enforce(contract)

        # Record execution trace
        self.traces.record_execution_trace(
            trace_id=contract.trace_id,
            contract_hash=contract.payload_hash,
            ack=result.ack,
            runtime_hash=result.runtime_hash,
            confidence=result.confidence,
        )

        # Record governance trace
        if violations:
            self.traces.record_governance_trace(
                trace_id=contract.trace_id,
                violations=[v.to_dict() for v in violations],
            )

        # Append to local ledger (ordered hash chain)
        prev_hash = self.ledger[-1] if self.ledger else "GENESIS"
        entry_raw = json.dumps({
            "prev_hash":     prev_hash,
            "trace_id":      contract.trace_id,
            "payload_hash":  contract.payload_hash,
            "runtime_hash":  result.runtime_hash,
            "ack":           result.ack,
        }, sort_keys=True)
        entry_hash = hashlib.sha256(entry_raw.encode()).hexdigest()
        self.ledger.append(entry_hash)

        log_event(log, logging.INFO, "node_processed", ctx={
            "node_id":      self.node_id,
            "trace_id":     contract.trace_id,
            "ack":          result.ack,
            "ledger_len":   len(self.ledger),
            "entry_hash":   entry_hash[:16],
        })

        return result


# ---------------------------------------------------------------------------
# Distributed proof
# ---------------------------------------------------------------------------

@dataclass
class DistributedProof:
    """Result of the distributed simulation."""
    passed:              bool
    node_count:          int
    producer_count:      int
    contracts_processed: int
    hash_agreement:      bool
    node_ledgers:        dict       # node_id → ledger
    propagation_log:     list[dict]
    scope:               str = "SIMULATION"                       # METADATA — classification
    timestamp:           str = field(                             # OBSERVABILITY
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "passed":              self.passed,
            "node_count":          self.node_count,
            "producer_count":      self.producer_count,
            "contracts_processed": self.contracts_processed,
            "hash_agreement":      self.hash_agreement,
            "node_ledgers":        self.node_ledgers,
            "propagation_log":     self.propagation_log,
            "scope":               self.scope,
            "timestamp":           self.timestamp,
        }


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

class DistributedSimulation:
    """
    Simulate a distributed runtime with ordered propagation.

    Classification: SIMULATION-LEVEL only.
    See SCOPE DECLARATION in module docstring for boundaries.
    """

    def __init__(
        self,
        node_count: int = config.SIMULATION_NODE_COUNT,
        seed: int = config.DEFAULT_SEED,
    ):
        self.seed = seed
        self.nodes = [
            SimulatedNode(node_id=f"node_{i}")
            for i in range(node_count)
        ]

    def run(self) -> DistributedProof:
        """
        Execute the distributed readiness experiment.

        1. Both producers generate contracts.
        2. Propagate through nodes in order.
        3. Each node processes independently.
        4. Verify hash agreement across all nodes.
        """
        log_event(log, logging.INFO, "distributed_experiment_start", ctx={
            "node_count": len(self.nodes),
            "scope": "SIMULATION",
        })

        # -- Step 1: Generate contracts from both producers ----------------

        # Quantum producer
        request = TransmissionRequest(
            message="NODE_READY", noise=0.12, mode="entangled"
        )
        distribution = run_quantum_producer(request, seed=self.seed)
        quantum_contract, q_trace = QuantumAdapter().adapt(distribution, "NODE_READY")

        # Classical producer
        classical_output = {
            "result":     "OPTIMISED_ROUTE_A",
            "confidence": 0.92,
            "metadata":   {"algorithm": "gradient_descent", "iterations": 1000},
        }
        classical_contract, c_trace = ClassicalAdapter().adapt(classical_output)

        contracts = [quantum_contract, classical_contract]

        # -- Step 2 & 3: Ordered propagation through nodes -----------------

        propagation_log: list[dict] = []
        total_processed = 0

        for contract in contracts:
            for node in self.nodes:
                result = node.process(contract)
                propagation_log.append({
                    "node_id":       node.node_id,
                    "trace_id":      contract.trace_id,
                    "producer_type": contract.producer_type,
                    "ack":           result.ack,
                    "runtime_hash":  result.runtime_hash,
                    "ledger_len":    len(node.ledger),
                })
                total_processed += 1

        # -- Step 4: Verify hash agreement ---------------------------------

        # All nodes should have the same ledger (same contracts, same order)
        node_ledgers = {
            node.node_id: list(node.ledger) for node in self.nodes
        }

        # Hash agreement: compare final ledger state across nodes
        final_hashes = [node.ledger[-1] if node.ledger else "" for node in self.nodes]
        hash_agreement = len(set(final_hashes)) == 1 and final_hashes[0] != ""

        # Full ledger agreement: all ledgers identical
        ledger_agreement = all(
            node.ledger == self.nodes[0].ledger for node in self.nodes
        )

        passed = hash_agreement and ledger_agreement

        proof = DistributedProof(
            passed=passed,
            node_count=len(self.nodes),
            producer_count=len(contracts),
            contracts_processed=total_processed,
            hash_agreement=hash_agreement,
            node_ledgers=node_ledgers,
            propagation_log=propagation_log,
            scope="SIMULATION",
        )

        log_event(log, logging.INFO, "distributed_experiment_result", ctx={
            "passed":         passed,
            "hash_agreement": hash_agreement,
            "ledger_agreement": ledger_agreement,
            "total_processed": total_processed,
            "scope": "SIMULATION",
        })

        # Human-readable summary
        print("\n" + "=" * 70)
        print("  DISTRIBUTED READINESS EXPERIMENT")
        print("  Scope: SIMULATION-LEVEL (not distributed execution readiness)")
        print("=" * 70)
        print(f"  Nodes:     {len(self.nodes)}")
        print(f"  Producers: {len(contracts)}")
        print(f"  Contracts processed: {total_processed}")
        print("-" * 70)

        for entry in propagation_log:
            print(f"  {entry['node_id']} <- {entry['producer_type']:10s} "
                  f"ack={entry['ack']:30s} ledger_len={entry['ledger_len']}")

        print("-" * 70)
        print(f"  Hash agreement:   {'YES' if hash_agreement else 'NO'}")
        print(f"  Ledger agreement: {'YES' if ledger_agreement else 'NO'}")

        for node_id, ledger in node_ledgers.items():
            print(f"  {node_id} final hash: {ledger[-1][:32]}..." if ledger else f"  {node_id}: EMPTY")

        print("-" * 70)
        verdict = "PASSED" if passed else "FAILED"
        print(f"  VERDICT: {verdict}")
        print("  NOTE: This proves simulation-level deterministic agreement only.")
        print("=" * 70 + "\n")

        return proof


if __name__ == "__main__":
    sim = DistributedSimulation()
    proof = sim.run()
    sys.exit(0 if proof.passed else 1)
