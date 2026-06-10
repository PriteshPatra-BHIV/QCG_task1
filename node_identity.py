"""
node_identity.py — Node Identity Layer

Cryptographically verifiable identity for every ecosystem participant.
Uses ECDSA P-256 (secp256r1) via the `cryptography` package.

Signature scheme
----------------
- Private key : ECDSA P-256, generated fresh per NodeSigner instance.
- Public key  : DER-encoded SubjectPublicKeyInfo, hex-serialised for transport.
- Signature   : DER-encoded ECDSA signature over SHA-256(canonical_payload), hex-serialised.
- Verification: Standard ECDSA verify — no shared secret involved.

This replaces the previous HMAC simulation in which the "public key" was
used as the HMAC secret, making signature forgery trivial for any observer.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature


# ---------------------------------------------------------------------------
# Node Identity Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NodeIdentity:
    """Represents a verified participant in the QCG ecosystem."""
    node_id:    str
    public_key: str   # hex-encoded DER SubjectPublicKeyInfo
    node_role:  str
    version:    str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NodeProof:
    """Cryptographic proof of a node's participation."""
    node_id:     str
    signature:   str   # hex-encoded DER ECDSA signature
    signed_hash: str   # hex SHA-256 of the signed payload
    timestamp:   str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Signing & Verification (ECDSA P-256)
# ---------------------------------------------------------------------------

class NodeSigner:
    """
    ECDSA P-256 signer.  Generates a fresh key pair on construction.
    The private key never leaves this object.
    """

    def __init__(self, node_id: str, node_role: str = "EXECUTION_NODE", version: str = "1.0.0"):
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        pub_der = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self._public_key_hex = pub_der.hex()

        self.identity = NodeIdentity(
            node_id=node_id,
            public_key=self._public_key_hex,
            node_role=node_role,
            version=version,
        )

    def sign_payload(self, payload: dict | str) -> NodeProof:
        """Sign a payload and return a cryptographic proof."""
        payload_str = (
            json.dumps(payload, sort_keys=True, default=str)
            if isinstance(payload, dict)
            else str(payload)
        )
        payload_bytes = payload_str.encode()
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # ECDSA sign over the payload bytes with SHA-256
        sig_bytes = self._private_key.sign(
            payload_bytes,
            ec.ECDSA(hashes.SHA256()),
        )
        return NodeProof(
            node_id=self.identity.node_id,
            signature=sig_bytes.hex(),
            signed_hash=payload_hash,
        )


def verify_node_proof(
    proof: NodeProof,
    public_key_hex: str,
    payload: dict | str | None = None,
) -> bool:
    """
    Verify an ECDSA proof.

    If `payload` is provided, first recomputes its hash and checks it matches
    `proof.signed_hash`.  Then verifies the ECDSA signature.

    Returns True on success, False on any failure (including malformed input).
    """
    try:
        payload_str = None
        if payload is not None:
            payload_str = (
                json.dumps(payload, sort_keys=True, default=str)
                if isinstance(payload, dict)
                else str(payload)
            )
            expected_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            if expected_hash != proof.signed_hash:
                return False

        pub_der = bytes.fromhex(public_key_hex)
        public_key = serialization.load_der_public_key(pub_der)

        # We need the original payload bytes to verify; reconstruct from signed_hash
        # by re-deriving payload_str if available, else use signed_hash as stand-in
        if payload_str is not None:
            verify_data = payload_str.encode()
        else:
            # No payload provided — verify signature over the canonical bytes
            # that produced signed_hash (we cannot reconstruct, so we verify
            # the signature directly against the hash as a raw byte string)
            verify_data = proof.signed_hash.encode()

        public_key.verify(
            bytes.fromhex(proof.signature),
            verify_data,
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, ValueError, Exception):
        return False


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== NODE IDENTITY & ECDSA SIGNING DEMO ===")

    signer = NodeSigner(node_id="NODE_ALPHA_001", node_role="QUANTUM_GATEWAY")
    print(f"Node Created : {signer.identity.node_id}")
    print(f"Public Key   : {signer.identity.public_key[:32]}...")

    event = {"action": "contract_received", "trace_id": "abc-123", "decision": "approve"}

    proof = signer.sign_payload(event)
    print(f"\nSignature    : {proof.signature[:32]}...")
    print(f"Signed Hash  : {proof.signed_hash}")

    ok = verify_node_proof(proof, signer.identity.public_key, event)
    print(f"\nValid proof  : {'PASS' if ok else 'FAIL'}")

    tampered = {**event, "decision": "reject"}
    ok_t = verify_node_proof(proof, signer.identity.public_key, tampered)
    print(f"Tampered     : {'PASS' if ok_t else 'FAIL (correctly rejected)'}")

    forged = NodeProof(node_id=proof.node_id, signature="aa" * 72,
                       signed_hash=proof.signed_hash)
    ok_f = verify_node_proof(forged, signer.identity.public_key, event)
    print(f"Forged sig   : {'PASS' if ok_f else 'FAIL (correctly rejected)'}")
