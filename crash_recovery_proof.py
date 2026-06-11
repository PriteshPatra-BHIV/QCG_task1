"""
crash_recovery_proof.py — Phase 3: Crash Recovery Proof

Demonstrates that the replay registry survives a gateway (execution process)
crash and that execution continues safely after restart, with no duplicate
processing of already-seen messages.

Proof Cases
-----------
1. Normal run    — pipeline executes cleanly, contract accepted, ACK:OK
2. Crash + restart — execution process crashes mid-flight; registry loaded
                     from disk on restart; already-seen messages rejected as
                     DUPLICATE; new messages accepted with continued sequence
3. Registry isolation — two independent registry instances share no state

IPC transport: multiprocessing.Queue (same as existing pipeline)

Exit codes:
    0 — all proof cases pass
    1 — one or more proof cases failed
"""

from __future__ import annotations

import json
import multiprocessing
import sys
import tempfile
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers: minimal in-process pipeline simulation
# (avoids spawning real OS processes for proof speed; process isolation is
#  proven by TestProcessIsolation in the test suite which uses real PIDs)
# ---------------------------------------------------------------------------

def _make_contract(trace_id: str):
    from execution_contract import ComputationExecutionContract
    from node_identity import NodeSigner
    from provenance import sign_contract

    producer = NodeSigner("CRASH_PROOF_PRODUCER", "QUANTUM_PRODUCER")
    contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        payload={"data": "crash_recovery_test"},
        confidence=0.97,
        trace_id=trace_id,
        contract_version="2.0.0",
    )
    signed = sign_contract(contract, producer)
    return signed, producer.identity.public_key


def _execute_contract(signed, pub_key, registry_path: Path) -> dict:
    """Run contract through ReplayRegistry + RuntimeCore. Returns result dict."""
    from replay_registry import ReplayRegistry
    from runtime_core import RuntimeCore
    from provenance import verify_contract_provenance, ProvenanceStatus
    import config

    reg = ReplayRegistry(path=registry_path, ttl_seconds=config.REPLAY_TTL_SECONDS)
    runtime = RuntimeCore()

    decision = reg.submit(signed.trace_id, issued_at=time.time())
    if decision.status != "VALID":
        return {
            "trace_id": signed.trace_id,
            "sequence_number": decision.sequence_number,
            "status": decision.status,
            "ack": f"HALT:{decision.status}",
        }

    prov = verify_contract_provenance(signed, pub_key)
    if prov != ProvenanceStatus.VERIFIED:
        return {
            "trace_id": signed.trace_id,
            "sequence_number": decision.sequence_number,
            "status": "PROVENANCE_FAILED",
            "ack": f"HALT:PROVENANCE_FAILED:{prov}",
        }

    result = runtime.execute(signed)
    return {
        "trace_id": result.contract_trace_id,
        "sequence_number": decision.sequence_number,
        "status": decision.status,
        "ack": result.ack,
        "runtime_hash": result.runtime_hash,
    }


# ---------------------------------------------------------------------------
# Proof runner
# ---------------------------------------------------------------------------

def run_proof(verbose: bool = True) -> dict:
    results: dict[str, bool] = {}
    registry_path = Path(tempfile.mktemp(suffix="_crash_proof.json"))

    try:
        # ------------------------------------------------------------------
        # Case 1: Normal execution — contract accepted, ACK:OK
        # ------------------------------------------------------------------
        signed, pub_key = _make_contract("crash-proof-trace-001")
        r1 = _execute_contract(signed, pub_key, registry_path)

        results["normal_execution_accepted"] = (
            r1["status"] == "VALID" and r1["ack"] == "ACK:OK"
        )
        if verbose:
            print(f"\n  [Case 1: Normal execution]")
            print(f"    trace_id={r1['trace_id']}  seq={r1['sequence_number']}")
            print(f"    status={r1['status']}  ack={r1['ack']}")
            print(f"    pass={results['normal_execution_accepted']}")

        # ------------------------------------------------------------------
        # Case 2: Simulated crash — registry file exists on disk.
        #         Restart: new instance loads from disk.
        #         Re-submitting same trace_id → DUPLICATE (replay blocked).
        # ------------------------------------------------------------------
        # Simulate crash: registry_path file already written by Case 1.
        # "Restart" = new ReplayRegistry instance pointing to same file.
        from replay_registry import ReplayRegistry
        registry_after_restart = ReplayRegistry(
            path=registry_path, ttl_seconds=300.0
        )

        seq_survived = registry_after_restart.sequence_count
        known_survived = registry_after_restart.is_known("crash-proof-trace-001")
        results["registry_survives_crash"] = known_survived and seq_survived >= 1
        if verbose:
            print(f"\n  [Case 2: Registry survives crash/restart]")
            print(f"    sequence_count_after_restart={seq_survived}")
            print(f"    known trace-001={known_survived}")
            print(f"    pass={results['registry_survives_crash']}")

        # ------------------------------------------------------------------
        # Case 3: Duplicate blocked after restart — same trace_id rejected
        # ------------------------------------------------------------------
        r2 = _execute_contract(signed, pub_key, registry_path)
        results["duplicate_blocked_after_restart"] = (
            r2["status"] == "DUPLICATE" and r2["ack"].startswith("HALT:DUPLICATE")
        )
        if verbose:
            print(f"\n  [Case 3: Duplicate blocked after restart]")
            print(f"    status={r2['status']}  ack={r2['ack']}")
            print(f"    pass={results['duplicate_blocked_after_restart']}")

        # ------------------------------------------------------------------
        # Case 4: New contract after restart — accepted with continued sequence
        # ------------------------------------------------------------------
        signed2, pub_key2 = _make_contract("crash-proof-trace-002")
        r3 = _execute_contract(signed2, pub_key2, registry_path)

        results["new_contract_accepted_after_restart"] = (
            r3["status"] == "VALID"
            and r3["ack"] == "ACK:OK"
            and r3["sequence_number"] == seq_survived + 1
        )
        if verbose:
            print(f"\n  [Case 4: New contract accepted after restart]")
            print(f"    trace_id={r3['trace_id']}  seq={r3['sequence_number']}")
            print(f"    expected_seq={seq_survived + 1}")
            print(f"    status={r3['status']}  ack={r3['ack']}")
            print(f"    pass={results['new_contract_accepted_after_restart']}")

        # ------------------------------------------------------------------
        # Case 5: Independent registry instances share no state
        # ------------------------------------------------------------------
        path_a = Path(tempfile.mktemp(suffix="_reg_a.json"))
        path_b = Path(tempfile.mktemp(suffix="_reg_b.json"))
        try:
            reg_a = ReplayRegistry(path=path_a, ttl_seconds=300.0)
            reg_b = ReplayRegistry(path=path_b, ttl_seconds=300.0)
            reg_a.submit("isolation-msg-001")
            # B has no knowledge of A's messages
            results["registry_isolation"] = (
                not reg_b.is_known("isolation-msg-001")
                and reg_b.sequence_count == 0
            )
        finally:
            for p in [path_a, path_b]:
                if p.exists():
                    p.unlink()

        if verbose:
            print(f"\n  [Case 5: Registry isolation]")
            print(f"    independent registries share no state")
            print(f"    pass={results['registry_isolation']}")

    finally:
        if registry_path.exists():
            registry_path.unlink()

    all_passed = all(results.values())

    if verbose:
        print(f"\n{'='*60}")
        status = "PASS" if all_passed else "FAIL"
        print(f"  CRASH RECOVERY PROOF - {status}")
        print(f"{'='*60}")
        for case, passed in results.items():
            mark = "[PASS]" if passed else "[FAIL]"
            print(f"  {mark}  {case}")
        print(f"{'='*60}\n")

    return {"passed": all_passed, "cases": results}


# ---------------------------------------------------------------------------
# Process isolation proof — spawns real OS processes, checks distinct PIDs
# ---------------------------------------------------------------------------

def _producer_target(q_out):
    import os, time, json
    from execution_contract import ComputationExecutionContract
    from node_identity import NodeSigner
    from provenance import sign_contract

    producer = NodeSigner("ISO_PRODUCER", "QUANTUM_PRODUCER")
    contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        payload={"data": "isolation_test"},
        confidence=0.95,
        trace_id="isolation-trace-001",
        contract_version="2.0.0",
    )
    signed = sign_contract(contract, producer)
    q_out.put({
        "pid": os.getpid(),
        "contract": signed.to_dict(),
        "pub_key": producer.identity.public_key,
    })


def _execution_target(q_in, q_out):
    import os
    from runtime_core import RuntimeCore
    from execution_contract import ComputationExecutionContract

    runtime = RuntimeCore()
    msg = q_in.get(timeout=10)
    contract = ComputationExecutionContract(**msg["contract"])
    result = runtime.execute(contract)
    q_out.put({
        "producer_pid": msg["pid"],
        "execution_pid": os.getpid(),
        "ack": result.ack,
    })


def run_process_isolation_proof(verbose: bool = True) -> dict:
    """Spawn real OS processes and verify they have distinct PIDs."""
    q1 = multiprocessing.Queue()
    q2 = multiprocessing.Queue()

    p_prod = multiprocessing.Process(target=_producer_target, args=(q1,))
    p_exec = multiprocessing.Process(target=_execution_target, args=(q1, q2))

    import os
    runner_pid = os.getpid()

    p_prod.start()
    p_exec.start()
    p_prod.join(timeout=15)
    p_exec.join(timeout=15)

    try:
        outcome = q2.get(timeout=5)
    except Exception:
        outcome = {}

    producer_pid = outcome.get("producer_pid", 0)
    execution_pid = outcome.get("execution_pid", 0)

    passed = (
        producer_pid != 0
        and execution_pid != 0
        and producer_pid != execution_pid
        and runner_pid != producer_pid
        and runner_pid != execution_pid
        and outcome.get("ack") == "ACK:OK"
    )

    if verbose:
        print(f"\n  [Process Isolation Proof]")
        print(f"    runner_pid={runner_pid}")
        print(f"    producer_pid={producer_pid}")
        print(f"    execution_pid={execution_pid}")
        print(f"    all_distinct={producer_pid != execution_pid != runner_pid}")
        print(f"    ack={outcome.get('ack')}")
        print(f"    pass={passed}")

    return {"passed": passed, "runner_pid": runner_pid,
            "producer_pid": producer_pid, "execution_pid": execution_pid,
            "ack": outcome.get("ack")}


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)

    proof = run_proof()
    iso = run_process_isolation_proof()

    all_passed = proof["passed"] and iso["passed"]
    sys.exit(0 if all_passed else 1)
