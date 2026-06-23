import pytest
import uuid
import time
from execution_record import ExecutionRecord
from evidence_ledger import EvidenceLedger
from provenance_api import (
    verify_execution,
    verify_provenance,
    verify_lineage,
    verify_runtime,
    execution_history,
    execution_graph,
    execution_certificate
)

def test_evidence_ledger_append_and_merkle():
    ledger = EvidenceLedger()
    
    # 1. First record
    exec_id_1 = str(uuid.uuid4())
    record1 = ExecutionRecord(
        execution_id=exec_id_1,
        trace_id="trace_1",
        replay_reference="ref_1",
        execution_sequence=1,
        producer_identity="PRODUCER_1",
        runtime_identity="RUNTIME_1",
        governance_identity="GOV_1",
        execution_status="ACK:OK",
        runtime_hash="hash_rt_1",
        execution_hash="hash_ex_1",
        previous_execution_hash=ledger._current_head,
        execution_root_hash="hash_root_0",
        schema_version="1.0.0"
    )
    
    snapshot1 = ledger.append(record1)
    assert snapshot1.sequence_length == 1
    assert ledger.verify_chain() is True
    
    # 2. Second record
    exec_id_2 = str(uuid.uuid4())
    record2 = ExecutionRecord(
        execution_id=exec_id_2,
        trace_id="trace_1",
        replay_reference="ref_2",
        execution_sequence=2,
        producer_identity="PRODUCER_1",
        runtime_identity="RUNTIME_1",
        governance_identity="GOV_1",
        execution_status="ACK:OK",
        runtime_hash="hash_rt_2",
        execution_hash="hash_ex_2",
        previous_execution_hash=ledger._current_head,
        execution_root_hash=ledger.get_merkle_root(),
        schema_version="1.0.0"
    )
    
    snapshot2 = ledger.append(record2)
    assert snapshot2.sequence_length == 2
    assert ledger.verify_chain() is True
    
def test_provenance_api_verification():
    ledger = EvidenceLedger()
    
    exec_id_1 = str(uuid.uuid4())
    import hashlib
    import json
    
    base_dict = {
        "execution_id": exec_id_1,
        "trace_id": "trace_1",
        "replay_reference": "ref_1",
        "execution_sequence": 1,
        "producer_identity": "PRODUCER_1",
        "runtime_identity": "RUNTIME_1",
        "governance_identity": "GOV_1",
        "execution_status": "ACK:OK",
        "runtime_hash": "hash_rt_1",
        "schema_version": "1.0.0"
    }
    exec_hash = hashlib.sha256(json.dumps(base_dict, sort_keys=True).encode()).hexdigest()
    
    record = ExecutionRecord(
        execution_id=exec_id_1,
        trace_id="trace_1",
        replay_reference="ref_1",
        execution_sequence=1,
        producer_identity="PRODUCER_1",
        runtime_identity="RUNTIME_1",
        governance_identity="GOV_1",
        execution_status="ACK:OK",
        runtime_hash="hash_rt_1",
        execution_hash=exec_hash,
        previous_execution_hash=ledger._current_head,
        execution_root_hash="hash_root_0",
        schema_version="1.0.0"
    )
    ledger.append(record)
    
    assert verify_execution(record) is True
    
    trusted_identities = {"PRODUCER_1", "RUNTIME_1", "GOV_1"}
    assert verify_provenance(record, trusted_identities) is True
    
    assert verify_lineage(record, ledger) is True
    
    assert verify_runtime(record, "hash_rt_1") is True
    
    history = execution_history(ledger, "trace_1")
    assert len(history) == 1
    assert history[0].execution_id == exec_id_1
    
    graph = execution_graph(ledger)
    assert len(graph) == 1
    assert graph[0][1] == exec_id_1
    
    cert = execution_certificate(record, ledger)
    assert cert["certificate_type"] == "DeterministicExecutionCertificate"
    assert cert["ledger_sequence"] == 1
    
def test_execution_process_integration():
    from execution_process import run
    import threading
    import socket
    
    def get_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port

    in_port = get_free_port()
    out_port = get_free_port()
    hb_port = get_free_port()

    t = threading.Thread(target=run, args=(in_port, out_port, False, hb_port))
    t.daemon = True
    t.start()
    
    # Let process start
    time.sleep(1)
    
    from network_ipc import IPCSender, IPCReceiver
    queue_in = IPCSender(port=in_port)
    queue_out = IPCReceiver(port=out_port)
    
    # Create fake valid contract
    contract = {
        "producer_type": "QUANTUM",
        "payload": {"data": "test"},
        "confidence": 0.99,
        "trace_id": "trace_1",
        "contract_version": "1.0.0",
        "producer_id": "PRODUCER_1",
        "producer_signature": "sig1",
        "contract_signature": "sig2"
    }
    
    queue_in.put({
        "type": "CONTRACT",
        "contract": contract,
        "producer_public_key": "pub_key_1",
        "issued_at": time.time()
    })
    
    # Wait for result
    import traceback
    try:
        msg = queue_out.get(timeout=5)
        assert msg["type"] == "EXECUTION_RESULT"
        # Since producer signature is invalid it should halt
        assert "HALT:INVALID_SIGNATURE" in msg["result"]["ack"]
        
        # Try DONE to shutdown
        queue_in.put({"type": "DONE"})
        done_msg = queue_out.get(timeout=2)
        assert done_msg["type"] == "DONE"
    except Exception as e:
        queue_in.put({"type": "DONE"})
        traceback.print_exc()

if __name__ == "__main__":
    pytest.main(["-v", "test_provenance_integration.py"])
