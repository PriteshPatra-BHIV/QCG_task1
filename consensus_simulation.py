"""
consensus_simulation.py -- Phase 3: Distributed Consensus Simulation (Enhanced)

Simulates an independent consensus process across multiple nodes.
Each node processes the ComputationExecutionContract, signs its attestation,
and the ConsensusEngine aggregates results into a ConsensusProof with
round tracking, per-node attestations, and quorum verification.

Enhancements over v1:
- consensus_round + consensus_timestamp in ConsensusProof
- Per-node signed attestations (NodeAttestation)
- quorum_size computed field
- ConsensusEngine verifies attestation signatures before declaring consensus
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
import json
import hashlib

from execution_contract import ComputationExecutionContract
from runtime_core import RuntimeCore
from node_identity import NodeSigner, NodeProof, verify_node_proof
from provenance import verify_contract_provenance, ProvenanceStatus
import config


# ---------------------------------------------------------------------------
# Node Attestation — a node's signed vote on the agreement hash
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NodeAttestation:
    """A single node's signed attestation of the agreement hash."""
    node_id: str
    agreement_hash: str
    status: str               # "OK", "EXECUTION_HALT:...", "PROVENANCE_FAILURE:..."
    signature: str            # node signs the agreement_hash
    public_key: str           # for downstream verification

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Consensus Proof (Enhanced)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConsensusProof:
    participating_nodes: list[str]
    final_hash: str
    agreement_percentage: float
    consensus_reached: bool
    disagreements: dict[str, str]        # node_id -> reason
    consensus_round: int = 1
    quorum_size: int = 0
    node_attestations: dict[str, dict] = field(default_factory=dict)  # node_id -> attestation dict
    consensus_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Distributed Consensus Node
# ---------------------------------------------------------------------------

class DistributedConsensusNode:
    """A participant in the consensus network."""
    def __init__(self, node_id: str):
        self.signer = NodeSigner(node_id=node_id, node_role="EXECUTION_NODE")
        self.runtime = RuntimeCore()

    def process(
        self,
        contract: ComputationExecutionContract,
        producer_pub_key: str
    ) -> NodeAttestation:
        """
        Process a contract and return a signed attestation.
        """
        # 1. Verify Provenance
        prov_status = verify_contract_provenance(contract, producer_pub_key)
        if prov_status != ProvenanceStatus.VERIFIED:
            status = f"PROVENANCE_FAILURE:{prov_status}"
            # Sign empty hash to prove participation even on failure
            proof = self.signer.sign_payload("")
            return NodeAttestation(
                node_id=self.signer.identity.node_id,
                agreement_hash="",
                status=status,
                signature=proof.signature,
                public_key=self.signer.identity.public_key,
            )

        # 2. Execute blindly through RuntimeCore
        result = self.runtime.execute(contract)
        agreement_hash = result.runtime_hash

        if "HALT" in result.ack:
            status = f"EXECUTION_HALT:{result.ack}"
        else:
            status = "OK"

        # 3. Node signs its agreement hash
        proof = self.signer.sign_payload(agreement_hash)

        return NodeAttestation(
            node_id=self.signer.identity.node_id,
            agreement_hash=agreement_hash,
            status=status,
            signature=proof.signature,
            public_key=self.signer.identity.public_key,
        )


# ---------------------------------------------------------------------------
# Consensus Engine (Enhanced)
# ---------------------------------------------------------------------------

class ConsensusEngine:
    """Simulates the network consensus phase with attestation verification."""
    def __init__(self, nodes: list[DistributedConsensusNode]):
        self.nodes = nodes
        self.threshold = config.CONSENSUS_QUORUM_THRESHOLD

    def run_consensus(
        self,
        contract: ComputationExecutionContract,
        producer_pub_key: str,
        simulate_faulty: str = None,
        simulate_missing: str = None,
        consensus_round: int = 1,
    ) -> ConsensusProof:
        attestations: dict[str, NodeAttestation] = {}
        disagreements = {}
        participating = []
        quorum_size = math.ceil(len(self.nodes) * self.threshold)

        for node in self.nodes:
            nid = node.signer.identity.node_id

            if nid == simulate_missing:
                disagreements[nid] = "MISSING_PARTICIPANT"
                continue

            participating.append(nid)
            attestation = node.process(contract, producer_pub_key)

            # Fault injection: replace hash after honest processing
            if nid == simulate_faulty:
                faulty_hash = hashlib.sha256(b"faulty_data").hexdigest()
                faulty_proof = node.signer.sign_payload(faulty_hash)
                attestation = NodeAttestation(
                    node_id=nid,
                    agreement_hash=faulty_hash,
                    status=attestation.status,
                    signature=faulty_proof.signature,
                    public_key=attestation.public_key,
                )

            attestations[nid] = attestation

        if not participating:
            return ConsensusProof(
                participating_nodes=[],
                final_hash="",
                agreement_percentage=0.0,
                consensus_reached=False,
                disagreements=disagreements,
                consensus_round=consensus_round,
                quorum_size=quorum_size,
            )

        # Verify each attestation's signature
        verified_attestations: dict[str, NodeAttestation] = {}
        for nid, att in attestations.items():
            proof = NodeProof(
                node_id=nid,
                signature=att.signature,
                signed_hash=hashlib.sha256(att.agreement_hash.encode()).hexdigest(),
                timestamp="",
            )
            if verify_node_proof(proof, att.public_key, att.agreement_hash):
                verified_attestations[nid] = att
            else:
                disagreements[nid] = "ATTESTATION_SIGNATURE_INVALID"

        # Find majority hash from verified attestations
        hash_counts: dict[str, int] = {}
        for nid, att in verified_attestations.items():
            h = att.agreement_hash
            if h and "PROVENANCE_FAILURE" not in att.status:
                hash_counts[h] = hash_counts.get(h, 0) + 1

        if not hash_counts:
            for nid, att in verified_attestations.items():
                disagreements[nid] = att.status
            return ConsensusProof(
                participating_nodes=participating,
                final_hash="NO_CONSENSUS",
                agreement_percentage=0.0,
                consensus_reached=False,
                disagreements=disagreements,
                consensus_round=consensus_round,
                quorum_size=quorum_size,
                node_attestations={k: v.to_dict() for k, v in attestations.items()},
            )

        majority_hash = max(hash_counts, key=hash_counts.get)
        majority_count = hash_counts[majority_hash]
        agreement_percentage = majority_count / len(self.nodes)

        for nid, att in verified_attestations.items():
            if att.agreement_hash != majority_hash:
                reason = att.status if att.status != "OK" else f"DIVERGENT_HASH:{att.agreement_hash[:8]}"
                disagreements[nid] = reason

        consensus_reached = agreement_percentage >= self.threshold

        return ConsensusProof(
            participating_nodes=participating,
            final_hash=majority_hash if consensus_reached else "NO_CONSENSUS",
            agreement_percentage=agreement_percentage,
            consensus_reached=consensus_reached,
            disagreements=disagreements,
            consensus_round=consensus_round,
            quorum_size=quorum_size,
            node_attestations={k: v.to_dict() for k, v in attestations.items()},
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from provenance import sign_contract

    print("=== DISTRIBUTED CONSENSUS SIMULATION (ENHANCED) ===\n")

    producer = NodeSigner("PRODUCER_1", "QUANTUM_PRODUCER")
    nodes = [
        DistributedConsensusNode("NODE_A"),
        DistributedConsensusNode("NODE_B"),
        DistributedConsensusNode("NODE_C"),
    ]
    engine = ConsensusEngine(nodes)

    contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        payload={"data": "entangled_pair"},
        confidence=0.98,
        trace_id="tr-consensus-enh-001",
        contract_version="2.0.0",
    )
    signed_contract = sign_contract(contract, producer)

    # A. Full Agreement
    print("[Scenario A: Full Agreement]")
    proof_a = engine.run_consensus(signed_contract, producer.identity.public_key)
    print(f"  Consensus: {proof_a.consensus_reached}  Agreement: {proof_a.agreement_percentage:.0%}")
    print(f"  Quorum: {proof_a.quorum_size}  Round: {proof_a.consensus_round}")
    print(f"  Attestations: {len(proof_a.node_attestations)}")
    print()

    # B. One Faulty Node
    print("[Scenario B: One Faulty Node]")
    proof_b = engine.run_consensus(
        signed_contract, producer.identity.public_key,
        simulate_faulty="NODE_B",
    )
    print(f"  Consensus: {proof_b.consensus_reached}  Agreement: {proof_b.agreement_percentage:.0%}")
    print(f"  Disagreements: {proof_b.disagreements}")
    print()

    # C. Tampered Contract
    print("[Scenario C: Tampered Contract]")
    td = signed_contract.to_dict()
    td["payload"] = {"data": "malicious_data"}
    tampered_contract = ComputationExecutionContract(**td)
    proof_c = engine.run_consensus(tampered_contract, producer.identity.public_key)
    print(f"  Consensus: {proof_c.consensus_reached}  Final: {proof_c.final_hash}")
    print()

    # D. Missing Participant
    print("[Scenario D: Missing Participant]")
    proof_d = engine.run_consensus(
        signed_contract, producer.identity.public_key,
        simulate_missing="NODE_C",
    )
    print(f"  Consensus: {proof_d.consensus_reached}  Agreement: {proof_d.agreement_percentage:.0%}")
    print(f"  Disagreements: {proof_d.disagreements}")
    print()
