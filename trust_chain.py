"""
trust_chain.py -- Node Registry & Chain-of-Custody

Provides:
1. NodeRegistry  — centralized identity lookup (node_id -> NodeIdentity)
2. TrustChainLink — a single custody handoff between two nodes
3. TrustChain     — ordered list of handoffs with full verification

Together these prove *who held the contract at every stage* and that
each handoff was authorized by the sending node's cryptographic identity.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

from node_identity import NodeIdentity, NodeSigner, NodeProof, verify_node_proof


# ---------------------------------------------------------------------------
# Node Registry
# ---------------------------------------------------------------------------

class NodeRegistry:
    """
    In-memory registry mapping node_id -> NodeIdentity.

    Every node that participates in the ecosystem must register here
    before its signatures can be verified.  An unregistered node's
    proofs are rejected during trust-chain verification.
    """

    def __init__(self):
        self._nodes: dict[str, NodeIdentity] = {}

    def register(self, identity: NodeIdentity) -> None:
        """Register a node identity.  Overwrites if node_id already exists."""
        self._nodes[identity.node_id] = identity

    def lookup(self, node_id: str) -> NodeIdentity | None:
        """Look up a node by ID.  Returns None if not registered."""
        return self._nodes.get(node_id)

    def is_registered(self, node_id: str) -> bool:
        return node_id in self._nodes

    def all_nodes(self) -> list[NodeIdentity]:
        return list(self._nodes.values())

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes


# ---------------------------------------------------------------------------
# Trust Chain Link
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrustChainLink:
    """A single custody handoff between two nodes."""
    from_node: str          # node_id of the sender
    to_node: str            # node_id of the receiver
    action: str             # e.g. "PRODUCE", "GATEWAY_FORWARD", "EXECUTE", "CONSENSUS_VOTE"
    signature: str          # sender's signature over the handoff payload
    payload_hash: str       # hash of the artifact being handed off
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def handoff_hash(self) -> str:
        """Deterministic hash of this handoff for chaining."""
        canonical = json.dumps({
            "from_node": self.from_node,
            "to_node": self.to_node,
            "action": self.action,
            "payload_hash": self.payload_hash,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Trust Chain
# ---------------------------------------------------------------------------

class TrustChain:
    """
    Ordered list of TrustChainLink entries representing contract custody.

    Verification walks the entire chain and confirms:
    1. Each sender is registered in the registry.
    2. Each sender's signature is valid for the handoff data.
    3. The chain is contiguous (link N's to_node == link N+1's from_node).
    """

    def __init__(self):
        self._links: list[TrustChainLink] = []

    def add_handoff(
        self,
        from_signer: NodeSigner,
        to_identity: NodeIdentity,
        action: str,
        payload_hash: str,
    ) -> TrustChainLink:
        """Record a custody handoff.  The sender signs the handoff."""
        handoff_data = {
            "from_node": from_signer.identity.node_id,
            "to_node": to_identity.node_id,
            "action": action,
            "payload_hash": payload_hash,
        }
        proof = from_signer.sign_payload(handoff_data)

        link = TrustChainLink(
            from_node=from_signer.identity.node_id,
            to_node=to_identity.node_id,
            action=action,
            signature=proof.signature,
            payload_hash=payload_hash,
        )
        self._links.append(link)
        return link

    def verify_chain(self, registry: NodeRegistry) -> tuple[bool, list[str]]:
        """
        Walk the full chain and verify every link.

        Returns (passed, list_of_errors).
        """
        errors = []

        if not self._links:
            return True, []

        for i, link in enumerate(self._links):
            # 1. Check sender is registered
            sender = registry.lookup(link.from_node)
            if sender is None:
                errors.append(f"Link {i}: sender '{link.from_node}' is not registered")
                continue

            # 2. Verify signature
            handoff_data = {
                "from_node": link.from_node,
                "to_node": link.to_node,
                "action": link.action,
                "payload_hash": link.payload_hash,
            }
            proof = NodeProof(
                node_id=link.from_node,
                signature=link.signature,
                signed_hash=hashlib.sha256(
                    json.dumps(handoff_data, sort_keys=True, default=str).encode()
                ).hexdigest(),
                timestamp="",
            )
            if not verify_node_proof(proof, sender.public_key, handoff_data):
                errors.append(f"Link {i}: signature verification FAILED for '{link.from_node}'")

            # 3. Chain continuity (link N's to_node == link N+1's from_node)
            if i > 0:
                prev = self._links[i - 1]
                if prev.to_node != link.from_node:
                    errors.append(
                        f"Link {i}: chain break — previous to_node='{prev.to_node}' "
                        f"!= current from_node='{link.from_node}'"
                    )

        return len(errors) == 0, errors

    @property
    def links(self) -> list[TrustChainLink]:
        return list(self._links)

    def to_dict_list(self) -> list[dict]:
        return [l.to_dict() for l in self._links]

    def __len__(self) -> int:
        return len(self._links)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== NODE REGISTRY & TRUST CHAIN DEMO ===\n")

    # --- Setup nodes ---
    producer = NodeSigner("PRODUCER_Q1", "QUANTUM_PRODUCER")
    gateway = NodeSigner("GATEWAY_01", "GATEWAY")
    exec_node = NodeSigner("EXEC_NODE_01", "EXECUTION_NODE")
    consensus_node = NodeSigner("CONSENSUS_01", "CONSENSUS_NODE")

    # --- Registry ---
    registry = NodeRegistry()
    for signer in [producer, gateway, exec_node, consensus_node]:
        registry.register(signer.identity)

    print(f"[1] Registered {len(registry)} nodes")
    for n in registry.all_nodes():
        print(f"    {n.node_id:20s} role={n.node_role}")

    # --- Build trust chain: Producer -> Gateway -> ExecNode -> Consensus ---
    chain = TrustChain()
    payload_hash = hashlib.sha256(b'{"task":"demo"}').hexdigest()

    chain.add_handoff(producer, gateway.identity, "PRODUCE", payload_hash)
    chain.add_handoff(gateway, exec_node.identity, "GATEWAY_FORWARD", payload_hash)
    chain.add_handoff(exec_node, consensus_node.identity, "EXECUTE", payload_hash)

    print(f"\n[2] Trust chain has {len(chain)} links")
    for link in chain.links:
        print(f"    {link.from_node} --[{link.action}]--> {link.to_node}")

    # --- Verify ---
    print(f"\n[3] Verifying trust chain...")
    passed, errs = chain.verify_chain(registry)
    print(f"    Passed: {passed}")

    # --- Spoofing test ---
    print(f"\n[4] Spoofing test: unregistered node tries to add a link...")
    spoofer = NodeSigner("SPOOFER_X", "ATTACKER")
    chain.add_handoff(spoofer, consensus_node.identity, "SPOOF_HANDOFF", payload_hash)
    passed2, errs2 = chain.verify_chain(registry)
    print(f"    Passed: {passed2}")
    for e in errs2:
        print(f"    Error: {e}")

    print("\n[DONE] Trust Chain demo complete.")
