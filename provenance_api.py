"""
provenance_api.py — Phase 5: Provenance Verification APIs

Provides deterministic functions to verify execution certificates and lineage.
All APIs must be deterministic.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple

from execution_record import ExecutionRecord
from evidence_ledger import EvidenceLedger, _hash_pair

# ---------------------------------------------------------------------------
# Verification APIs
# ---------------------------------------------------------------------------

def verify_execution(record: ExecutionRecord) -> bool:
    """
    Verify the execution_hash of a given ExecutionRecord.
    The execution_hash should be deterministically derived from its fields.
    """
    # Exclude execution_hash, previous_execution_hash, execution_root_hash 
    # to form the base deterministic record payload that was hashed.
    base_dict = {
        "execution_id": record.execution_id,
        "trace_id": record.trace_id,
        "replay_reference": record.replay_reference,
        "execution_sequence": record.execution_sequence,
        "producer_identity": record.producer_identity,
        "runtime_identity": record.runtime_identity,
        "governance_identity": record.governance_identity,
        "execution_status": record.execution_status,
        "runtime_hash": record.runtime_hash,
        "schema_version": record.schema_version,
    }
    expected_hash = hashlib.sha256(json.dumps(base_dict, sort_keys=True).encode()).hexdigest()
    return record.execution_hash == expected_hash


def verify_provenance(record: ExecutionRecord, trusted_identities: set) -> bool:
    """
    Verify the provenance of the record by checking if the producer, runtime,
    and governance identities are within the trusted set.
    """
    # A true implementation would verify cryptographic signatures.
    # Here we simulate by checking against known trusted identities.
    if record.producer_identity not in trusted_identities:
        return False
    if record.runtime_identity not in trusted_identities:
        return False
    if record.governance_identity not in trusted_identities:
        return False
    return True


def verify_lineage(record: ExecutionRecord, ledger: EvidenceLedger) -> bool:
    """
    Verify that the record's previous_execution_hash matches the evidence ledger's chain
    up to that record's position.
    """
    # Find the record in the ledger
    for i, r in enumerate(ledger._records):
        if r.execution_id == record.execution_id:
            # Check the hash chain up to this record
            if i == 0:
                expected_prev = hashlib.sha256(b"GENESIS").hexdigest()
            else:
                expected_prev = ledger._evidence_hashes[i-1]
            return record.previous_execution_hash == expected_prev
            
    return False # Record not found in ledger


def verify_runtime(record: ExecutionRecord, expected_runtime_hash: str) -> bool:
    """
    Verify that the runtime_hash in the record matches the expected deterministically
    re-computed runtime hash.
    """
    return record.runtime_hash == expected_runtime_hash


def execution_history(ledger: EvidenceLedger, trace_id: str) -> List[ExecutionRecord]:
    """
    Return all execution records matching the given trace_id.
    """
    return [r for r in ledger._records if r.trace_id == trace_id]


def execution_graph(ledger: EvidenceLedger) -> List[Tuple[str, str]]:
    """
    Return a list of edges (parent_execution_id, child_execution_id) representing
    the deterministic lineage of executions.
    """
    edges = []
    for r in ledger._records:
        parent_id = "GENESIS"
        # Find the parent record based on previous_execution_hash
        for parent in ledger._records:
            if parent.execution_hash == r.previous_execution_hash:
                parent_id = parent.execution_id
                break
        edges.append((parent_id, r.execution_id))
    return edges


def execution_certificate(record: ExecutionRecord, ledger: EvidenceLedger) -> Dict[str, Any]:
    """
    Generate a verifiable execution certificate containing the record and its Merkle proof.
    """
    # 1. Find record index
    index = -1
    for i, r in enumerate(ledger._records):
        if r.execution_id == record.execution_id:
            index = i
            break
            
    if index == -1:
        raise ValueError("Record not found in ledger")
        
    # 2. Re-calculate evidence hash
    evidence_base_hash = record.execution_hash
    # The chain hash includes the previous head
    if index == 0:
        prev_head = hashlib.sha256(b"GENESIS").hexdigest()
    else:
        prev_head = ledger._evidence_hashes[index-1]
    
    expected_chain_hash = _hash_pair(prev_head, evidence_base_hash)
    
    # 3. Get merkle path (simplified, just providing the root and sequence for now
    # in a real merkle tree we would provide the sibling hashes up the tree).
    merkle_root = ledger.get_merkle_root()
    
    return {
        "execution_record": record.__dict__,
        "certificate_type": "DeterministicExecutionCertificate",
        "chain_hash": expected_chain_hash,
        "merkle_root": merkle_root,
        "ledger_sequence": index + 1,
        "schema_version": "1.0.0"
    }

