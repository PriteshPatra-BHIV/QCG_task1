"""
provenance.py — Phase 2: Contract Provenance Signing

Extends the trust boundary by ensuring every ComputationExecutionContract carries
cryptographic proof of its origins (producer_signature) and its current state
(contract_signature).

This layer verifies the integrity of the contract without inspecting its business logic.
"""

import json
import hashlib
from execution_contract import ComputationExecutionContract, _canonical_hash
from node_identity import NodeSigner, NodeProof, verify_node_proof

# ---------------------------------------------------------------------------
# Enums & Statuses
# ---------------------------------------------------------------------------

class ProvenanceStatus:
    VERIFIED = "VERIFIED"     # Signatures match and payload is intact
    UNVERIFIED = "UNVERIFIED" # Signatures are missing
    TAMPERED = "TAMPERED"     # Signatures exist but do not match the content

# ---------------------------------------------------------------------------
# Signing Helpers
# ---------------------------------------------------------------------------

def sign_contract(
    contract: ComputationExecutionContract,
    producer_signer: NodeSigner,
) -> ComputationExecutionContract:
    """
    Sign a contract, injecting provenance signatures.
    Returns a new contract instance (since contracts are frozen).
    """
    # 1. Producer signs the payload
    # We use payload_hash directly to represent the payload contents.
    producer_proof = producer_signer.sign_payload(contract.payload_hash)
    
    # We need to construct a new dictionary to create a new dataclass instance
    contract_dict = contract.to_dict()
    contract_dict["producer_id"] = producer_signer.identity.node_id
    contract_dict["producer_signature"] = producer_proof.signature
    
    # 2. To get a contract_signature, we hash the entire deterministic state of the contract.
    # Exclude timestamp and the contract_signature itself to ensure stable hashes.
    det_dict = {
        k: v for k, v in contract_dict.items()
        if k not in ["timestamp", "contract_signature"]
    }
    
    # The producer signer signs the whole contract state
    contract_proof = producer_signer.sign_payload(det_dict)
    contract_dict["contract_signature"] = contract_proof.signature
    
    return ComputationExecutionContract(**contract_dict)


# ---------------------------------------------------------------------------
# Verification API
# ---------------------------------------------------------------------------

def verify_contract_provenance(
    contract: ComputationExecutionContract,
    producer_public_key: str
) -> str:
    """
    Verify the provenance of a contract.
    
    Returns:
      VERIFIED, UNVERIFIED, or TAMPERED.
    """
    # 1. Check for missing signatures
    if not contract.producer_signature or not contract.contract_signature or not contract.producer_id:
        return ProvenanceStatus.UNVERIFIED
        
    # 2. Verify payload hash integrity (basic integrity)
    expected_hash = _canonical_hash(contract.payload)
    if contract.payload_hash != expected_hash:
        return ProvenanceStatus.TAMPERED
        
    # 3. Verify Producer Signature (Payload)
    producer_proof = NodeProof(
        node_id=contract.producer_id,
        signature=contract.producer_signature,
        signed_hash=hashlib.sha256(contract.payload_hash.encode()).hexdigest(),
        timestamp=""
    )
    is_producer_valid = verify_node_proof(producer_proof, producer_public_key, contract.payload_hash)
    if not is_producer_valid:
        return ProvenanceStatus.TAMPERED

    # 4. Verify Contract Signature (Full Deterministic State)
    contract_dict = contract.to_dict()
    det_dict = {
        k: v for k, v in contract_dict.items()
        if k not in ["timestamp", "contract_signature"]
    }
    contract_proof = NodeProof(
        node_id=contract.producer_id,
        signature=contract.contract_signature,
        signed_hash=hashlib.sha256(json.dumps(det_dict, sort_keys=True, default=str).encode()).hexdigest(),
        timestamp=""
    )
    is_contract_valid = verify_node_proof(contract_proof, producer_public_key, det_dict)
    if not is_contract_valid:
        return ProvenanceStatus.TAMPERED
        
    return ProvenanceStatus.VERIFIED


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== CONTRACT PROVENANCE SIGNING DEMO ===")
    
    # Setup
    signer = NodeSigner(node_id="PRODUCER_Q1", node_role="QUANTUM_PRODUCER")
    print(f"Producer Identity : {signer.identity.node_id}")
    
    base_contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        payload={"message": "HELLO_ECHO", "noise": 0.05},
        confidence=0.95,
        trace_id="tr-provenance-1",
        contract_version="2.0.0"
    )
    
    print("\n[Case 1] Missing Signatures (UNVERIFIED)")
    status = verify_contract_provenance(base_contract, signer.identity.public_key)
    print(f"Status: {status}")
    
    print("\n[Case 2] Valid Signed Contract (VERIFIED)")
    signed_contract = sign_contract(base_contract, signer)
    print(f"Producer Sig : {signed_contract.producer_signature[:32]}...")
    print(f"Contract Sig : {signed_contract.contract_signature[:32]}...")
    status = verify_contract_provenance(signed_contract, signer.identity.public_key)
    print(f"Status: {status}")
    
    print("\n[Case 3] Modified Contract Payload (TAMPERED)")
    # Modify payload
    tampered_dict = signed_contract.to_dict()
    tampered_dict["payload"] = {"message": "BYE_ECHO", "noise": 0.05}
    # Payload hash will be wrong compared to payload, causing TAMPERED,
    # or if they recalculate payload_hash, the signature will be wrong.
    tampered_contract = ComputationExecutionContract(**tampered_dict)
    status = verify_contract_provenance(tampered_contract, signer.identity.public_key)
    print(f"Status: {status}")
    
    print("\n[Case 4] Forged Signature (TAMPERED)")
    forged_dict = signed_contract.to_dict()
    forged_dict["contract_signature"] = "deadbeef1234567890abcdef"
    forged_contract = ComputationExecutionContract(**forged_dict)
    status = verify_contract_provenance(forged_contract, signer.identity.public_key)
    print(f"Status: {status}")
