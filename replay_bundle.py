"""
replay_bundle.py -- Phase 4: Replay Proof Package (Enhanced)

A ReplayBundle contains the complete lineage of an execution through
every layer of the QCG pipeline.  It is an artifact that reconstructs
the entire execution history.

Enhancements over v1:
- audit_trail_root: Merkle root anchoring the event sequence
- trust_chain: ordered chain-of-custody handoff records
- verification_details: per-check pass/fail breakdown
- verification_report(): structured report method
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict, field
from typing import Any

from node_identity import NodeProof, verify_node_proof
from consensus_simulation import ConsensusProof


# ---------------------------------------------------------------------------
# Lineage Sub-Components
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProducerLineage:
    producer_id: str
    producer_type: str
    payload_hash: str
    producer_signature: str

    def to_dict(self) -> dict: return asdict(self)


@dataclass(frozen=True)
class AdapterLineage:
    translation_version: str
    contract_version: str

    def to_dict(self) -> dict: return asdict(self)


@dataclass(frozen=True)
class GovernanceLineage:
    strict_mode: bool
    violations: list[dict]

    def to_dict(self) -> dict: return asdict(self)


@dataclass(frozen=True)
class ExecutionLineage:
    trace_id: str
    runtime_hash: str
    ack: str
    execution_timestamp: str

    def to_dict(self) -> dict: return asdict(self)


# ---------------------------------------------------------------------------
# Replay Bundle (Enhanced)
# ---------------------------------------------------------------------------

@dataclass
class ReplayBundle:
    """The master artifact for reconstructable execution history."""
    bundle_id: str
    producer_lineage: ProducerLineage
    adapter_lineage: AdapterLineage
    governance_lineage: GovernanceLineage
    execution_lineage: ExecutionLineage
    consensus_lineage: ConsensusProof
    bundle_signature: str = ""
    verification_status: str = "UNVERIFIED"
    # --- Enhanced fields ---
    audit_trail_root: str = ""                          # Merkle root from audit trail
    trust_chain: list[dict] = field(default_factory=list)  # chain-of-custody links
    verification_details: dict = field(default_factory=dict)  # per-check results

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "producer_lineage": self.producer_lineage.to_dict(),
            "adapter_lineage": self.adapter_lineage.to_dict(),
            "governance_lineage": self.governance_lineage.to_dict(),
            "execution_lineage": self.execution_lineage.to_dict(),
            "consensus_lineage": self.consensus_lineage.to_dict(),
            "bundle_signature": self.bundle_signature,
            "verification_status": self.verification_status,
            "audit_trail_root": self.audit_trail_root,
            "trust_chain": self.trust_chain,
            "verification_details": self.verification_details,
        }

    def sign(self, gateway_signer) -> None:
        """Sign the bundle using the gateway's identity."""
        state = self._signable_state()
        proof = gateway_signer.sign_payload(state)
        self.bundle_signature = proof.signature

    def verify(self, gateway_public_key: str, producer_public_key: str) -> str:
        """
        Verify the full integrity of the execution history.

        Checks:
        1. Bundle signature (gateway signed the whole bundle)
        2. Producer signature (producer signed the payload)
        3. Consensus was reached
        4. Audit trail root consistency (if present)
        5. Trust chain internal consistency (if present)

        Returns: PASS or FAIL
        """
        details = {}

        # 1. Verify bundle signature
        state = self._signable_state()
        bundle_proof = NodeProof(
            node_id="GATEWAY",
            signature=self.bundle_signature,
            signed_hash=hashlib.sha256(
                json.dumps(state, sort_keys=True, default=str).encode()
            ).hexdigest(),
            timestamp="",
        )
        bundle_sig_ok = verify_node_proof(bundle_proof, gateway_public_key, state)
        details["bundle_signature"] = "PASS" if bundle_sig_ok else "FAIL"
        if not bundle_sig_ok:
            self.verification_details = details
            self.verification_status = "FAIL"
            return "FAIL"

        # 2. Verify Producer signature on payload_hash string
        # producer.sign_payload(payload_hash) was called with a str,
        # so verify must also receive the same str.
        prod_sig_ok = verify_node_proof(
            NodeProof(
                node_id=self.producer_lineage.producer_id,
                signature=self.producer_lineage.producer_signature,
                signed_hash=hashlib.sha256(
                    self.producer_lineage.payload_hash.encode()
                ).hexdigest(),
                timestamp="",
            ),
            producer_public_key,
            self.producer_lineage.payload_hash,   # str — matches sign_payload(str)
        )
        details["producer_signature"] = "PASS" if prod_sig_ok else "FAIL"
        if not prod_sig_ok:
            self.verification_details = details
            self.verification_status = "FAIL"
            return "FAIL"

        # 3. Verify Consensus Reached
        consensus_ok = self.consensus_lineage.consensus_reached
        details["consensus_reached"] = "PASS" if consensus_ok else "FAIL"
        if not consensus_ok:
            self.verification_details = details
            self.verification_status = "FAIL"
            return "FAIL"

        # 4. Audit trail root consistency (if present)
        if self.audit_trail_root:
            # The audit trail root should be non-empty and well-formed (64 hex chars)
            root_ok = len(self.audit_trail_root) == 64
            details["audit_trail_root"] = "PASS" if root_ok else "FAIL"
            if not root_ok:
                self.verification_details = details
                self.verification_status = "FAIL"
                return "FAIL"
        else:
            details["audit_trail_root"] = "SKIPPED"

        # 5. Trust chain consistency (if present)
        if self.trust_chain:
            chain_ok = True
            for i in range(1, len(self.trust_chain)):
                prev_to = self.trust_chain[i - 1].get("to_node", "")
                curr_from = self.trust_chain[i].get("from_node", "")
                if prev_to != curr_from:
                    chain_ok = False
                    break
            details["trust_chain_continuity"] = "PASS" if chain_ok else "FAIL"
            if not chain_ok:
                self.verification_details = details
                self.verification_status = "FAIL"
                return "FAIL"
        else:
            details["trust_chain_continuity"] = "SKIPPED"

        self.verification_details = details
        self.verification_status = "PASS"
        return "PASS"

    def verification_report(self) -> dict:
        """Return a structured verification report."""
        return {
            "bundle_id": self.bundle_id,
            "status": self.verification_status,
            "checks": self.verification_details,
            "has_audit_trail": bool(self.audit_trail_root),
            "has_trust_chain": len(self.trust_chain) > 0,
            "consensus_agreement": self.consensus_lineage.agreement_percentage,
            "consensus_round": self.consensus_lineage.consensus_round,
        }

    # -- internal -----------------------------------------------------------

    def _signable_state(self) -> dict:
        """The subset of state that the gateway signs."""
        state = self.to_dict()
        state.pop("bundle_signature")
        state.pop("verification_status")
        state.pop("verification_details")
        return state


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from node_identity import NodeSigner
    from datetime import datetime, timezone

    print("=== REPLAY BUNDLE PROOF DEMO (ENHANCED) ===\n")

    producer = NodeSigner("PRODUCER_Q1", "QUANTUM_PRODUCER")
    gateway = NodeSigner("GATEWAY_NODE", "GATEWAY")

    payload_hash = hashlib.sha256(b'{"data": "q_state"}').hexdigest()
    prod_proof = producer.sign_payload(payload_hash)

    producer_lin = ProducerLineage(
        producer_id=producer.identity.node_id,
        producer_type="QUANTUM",
        payload_hash=payload_hash,
        producer_signature=prod_proof.signature,
    )
    adapter_lin = AdapterLineage("1.0.0", "2.0.0")
    gov_lin = GovernanceLineage(True, [])
    exec_lin = ExecutionLineage("tr-replay-enh-1", "deadbeef" * 8, "ACK:OK",
                                 datetime.now(timezone.utc).isoformat())

    consensus_lin = ConsensusProof(
        participating_nodes=["NODE_A", "NODE_B", "NODE_C"],
        final_hash="deadbeef" * 8,
        agreement_percentage=1.0,
        consensus_reached=True,
        disagreements={},
        consensus_round=1,
        quorum_size=2,
    )

    # Trust chain data
    trust_chain_data = [
        {"from_node": "PRODUCER_Q1", "to_node": "GATEWAY_NODE", "action": "PRODUCE"},
        {"from_node": "GATEWAY_NODE", "to_node": "EXEC_01", "action": "FORWARD"},
        {"from_node": "EXEC_01", "to_node": "CONSENSUS", "action": "EXECUTE"},
    ]

    bundle = ReplayBundle(
        bundle_id="RB-ENH-001",
        producer_lineage=producer_lin,
        adapter_lineage=adapter_lin,
        governance_lineage=gov_lin,
        execution_lineage=exec_lin,
        consensus_lineage=consensus_lin,
        audit_trail_root="a" * 64,  # simulated Merkle root
        trust_chain=trust_chain_data,
    )

    print("[+] Signing Replay Bundle...")
    bundle.sign(gateway)

    print("[+] Verifying Replay Bundle (Valid)...")
    res = bundle.verify(gateway.identity.public_key, producer.identity.public_key)
    print(f"Result: {res}")
    print(f"Report: {json.dumps(bundle.verification_report(), indent=2)}")

    print("\n[+] Verifying with broken trust chain...")
    bundle2 = ReplayBundle(
        bundle_id="RB-ENH-002",
        producer_lineage=producer_lin,
        adapter_lineage=adapter_lin,
        governance_lineage=gov_lin,
        execution_lineage=exec_lin,
        consensus_lineage=consensus_lin,
        trust_chain=[
            {"from_node": "A", "to_node": "B", "action": "X"},
            {"from_node": "C", "to_node": "D", "action": "Y"},  # break: B != C
        ],
    )
    bundle2.sign(gateway)
    res2 = bundle2.verify(gateway.identity.public_key, producer.identity.public_key)
    print(f"Result: {res2}")
    print(f"Report: {json.dumps(bundle2.verification_report(), indent=2)}")
