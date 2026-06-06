"""
node_identity.py — Phase 1: Node Identity Layer

Defines the cryptographically verifiable identity of a participant in the network.
Provides signing and verification primitives.

Note on Cryptography:
As per the approved plan, since external asymmetric crypto libraries (e.g. cryptography, ecdsa)
are not in the environment, we use a secure HMAC simulation where the 'public_key' acts
as the verification key. In a production environment, this would be replaced with ECDSA or RSA.
"""

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Node Identity Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NodeIdentity:
    """Represents a verified participant in the QCG ecosystem."""
    node_id: str
    public_key: str
    node_role: str
    version: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NodeProof:
    """Cryptographic proof of a node's participation."""
    node_id: str
    signature: str
    signed_hash: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Signing & Verification Engine (Simulation)
# ---------------------------------------------------------------------------

class NodeSigner:
    """
    Simulation of an asymmetric signer.
    Generates a private key and a public key (verification key).
    """
    def __init__(self, node_id: str, node_role: str = "EXECUTION_NODE", version: str = "1.0.0"):
        # SIMULATION: Use a strong random hex as the private secret.
        self._private_key = secrets.token_hex(32)
        # SIMULATION: The public key is derived (in this mock, it's just a derived string).
        # To allow verification without the private key, we use the public_key as the HMAC secret
        # in this mock. In production, signature would be ECDSA.
        self._public_key = hashlib.sha256(self._private_key.encode()).hexdigest()
        
        self.identity = NodeIdentity(
            node_id=node_id,
            public_key=self._public_key,
            node_role=node_role,
            version=version
        )

    def sign_payload(self, payload: dict | str) -> NodeProof:
        """Sign a payload and return a cryptographic proof of participation."""
        if isinstance(payload, dict):
            # Canonicalize dict
            payload_str = json.dumps(payload, sort_keys=True, default=str)
        else:
            payload_str = str(payload)
            
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        
        # SIMULATION: HMAC using the public key as the shared secret for easy local verification.
        signature = hmac.new(
            self._public_key.encode(),
            payload_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return NodeProof(
            node_id=self.identity.node_id,
            signature=signature,
            signed_hash=payload_hash
        )


def verify_node_proof(proof: NodeProof, public_key: str, payload: dict | str | None = None) -> bool:
    """
    Verify a node's cryptographic proof.
    If payload is provided, also verifies the signed_hash matches the payload.
    """
    if payload is not None:
        if isinstance(payload, dict):
            payload_str = json.dumps(payload, sort_keys=True, default=str)
        else:
            payload_str = str(payload)
        expected_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        if expected_hash != proof.signed_hash:
            return False
            
    # SIMULATION: Verify HMAC using the public_key as the mock secret.
    expected_signature = hmac.new(
        public_key.encode(),
        proof.signed_hash.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Use hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_signature, proof.signature)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== NODE IDENTITY & SIGNING DEMO ===")
    
    # 1. Create a node
    signer = NodeSigner(node_id="NODE_ALPHA_001", node_role="QUANTUM_GATEWAY")
    print(f"Node Created: {signer.identity.node_id}")
    print(f"Public Key  : {signer.identity.public_key}")
    
    # 2. Sign some participation data
    participation_event = {
        "action": "contract_received",
        "contract_trace_id": "abc-123-def",
        "decision": "approve"
    }
    
    print("\n[+] Signing Participation Event...")
    proof = signer.sign_payload(participation_event)
    print(f"Signature   : {proof.signature}")
    print(f"Signed Hash : {proof.signed_hash}")
    
    # 3. Verify the proof
    print("\n[+] Verifying Proof (Valid)...")
    is_valid = verify_node_proof(proof, signer.identity.public_key, participation_event)
    print(f"Verification Result: {'PASS' if is_valid else 'FAIL'}")
    
    # 4. Tamper with the payload and verify
    tampered_event = dict(participation_event)
    tampered_event["decision"] = "reject"
    print("\n[+] Verifying Proof against Tampered Payload...")
    is_tampered_valid = verify_node_proof(proof, signer.identity.public_key, tampered_event)
    print(f"Verification Result: {'PASS' if is_tampered_valid else 'FAIL'}")
    
    # 5. Tamper with signature
    tampered_proof = NodeProof(
        node_id=proof.node_id,
        signature="deadbeef" * 8,
        signed_hash=proof.signed_hash,
        timestamp=proof.timestamp
    )
    print("\n[+] Verifying Forged Signature...")
    is_forged_valid = verify_node_proof(tampered_proof, signer.identity.public_key, participation_event)
    print(f"Verification Result: {'PASS' if is_forged_valid else 'FAIL'}")
