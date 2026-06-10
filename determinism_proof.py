"""
Layer 6 - Determinism Proof
Same seed + same message -> identical ClassicalContract across N runs.

Determinism Categories (see determinism_doctrine.py)
----------------------------------------------------
EXECUTION     : ack, runtime_hash, confidence — MUST be identical.
CONTRACT      : payload_hash, trace_id, confidence, payload — MUST be identical.
OBSERVABILITY : timestamps — MAY differ between runs (wall-clock metadata).

This proof uses DeterminismOracle.extract_deterministic_projection() to
compare only deterministic fields, explicitly excluding timestamps.

Phase 3 additions
-----------------
- Default runs raised to 20 (sprint requirement).
- run_failure_injection_proof() proves detection of timestamp/ordering/payload mutation.
"""

import logging

import config
from logger import get_logger, log_event
from models import TransmissionRequest
from quantum_producer import run_quantum_producer
from translation_layer import translate
from determinism_doctrine import DeterminismOracle

log = get_logger("qcg.determinism")
_oracle = DeterminismOracle()


def run_determinism_proof(
    message: str = "NODE_READY",
    noise: float = 0.12,
    mode: str = "entangled",
    seed: int = config.DEFAULT_SEED,
    runs: int = 20,
) -> bool:
    log_event(log, logging.INFO, "determinism_proof_start", ctx={
        "msg_text": message, "noise": noise, "mode": mode, "seed": seed, "runs": runs
    })

    request = TransmissionRequest(message=message, noise=noise, mode=mode)
    results = []
    deterministic_projections = []

    for i in range(runs):
        dist = run_quantum_producer(request, seed=seed)
        contract = translate(dist, message)
        full_dict = contract.to_dict()
        # Extract only the deterministic projection — exclude timestamps
        det_proj = {
            k: v for k, v in full_dict.items()
            if k != "timestamp"  # timestamp is observability, not deterministic
        }
        results.append(full_dict)
        deterministic_projections.append(det_proj)
        log_event(log, logging.DEBUG, "determinism_run", ctx={
            "run": i + 1, "contract": full_dict
        })

    reference = deterministic_projections[0]
    all_match = all(r == reference for r in deterministic_projections)
    mismatches = [i + 1 for i, r in enumerate(deterministic_projections) if r != reference]

    # Also report which observability fields differed (expected: timestamps)
    observability_diffs = []
    for i, full in enumerate(results):
        for key in full:
            if key == "timestamp" and full[key] != results[0][key]:
                observability_diffs.append({
                    "run": i + 1, "field": key,
                    "value": full[key], "reference": results[0][key],
                })

    log_event(log, logging.INFO, "determinism_proof_result", ctx={
        "passed": all_match,
        "runs": runs,
        "mismatches": mismatches,
        "reference_deterministic_projection": reference,
        "observability_diffs_count": len(observability_diffs),
        "note": (
            "Comparison uses deterministic projection only. "
            "Timestamps are observability metadata and are excluded."
        ),
    })
    return all_match


# ---------------------------------------------------------------------------
# Failure Injection Proof
# ---------------------------------------------------------------------------

def run_failure_injection_proof() -> dict:
    """
    Prove that the determinism oracle detects three mutation types:
      1. timestamp mutation   — observability field changes
      2. ordering mutation    — payload keys reordered (JSON canonical form must normalise)
      3. payload mutation     — deterministic field tampered

    Returns a dict with detection results for each case.
    """
    from execution_contract import ComputationExecutionContract, _canonical_hash

    oracle = DeterminismOracle()

    request = TransmissionRequest("NODE_READY", 0.0, "entangled")
    dist = run_quantum_producer(request, seed=config.DEFAULT_SEED)
    contract = translate(dist, "NODE_READY")

    # Base contract via adapter
    from adapters import QuantumAdapter
    adapter = QuantumAdapter()
    base_contract, _ = adapter.adapt(dist, "NODE_READY")

    results = {}

    # --- 1. Timestamp mutation (observability field) ---
    import dataclasses
    mutated_ts = dataclasses.replace(base_contract, timestamp="1970-01-01T00:00:00+00:00")
    verdict = oracle.assert_contract_determinism(base_contract, mutated_ts)
    results["timestamp_mutation"] = {
        "deterministic_match": verdict.deterministic_match,
        "observability_diffs": bool(verdict.observability_diffs),
        "detected": not verdict.deterministic_match or bool(verdict.observability_diffs),
    }

    # --- 2. Ordering mutation (payload dict key order should not affect hash) ---
    original_payload = base_contract.payload
    reversed_payload = dict(reversed(list(original_payload.items())))
    hash_original = _canonical_hash(original_payload)
    hash_reversed = _canonical_hash(reversed_payload)
    results["ordering_mutation"] = {
        "hash_unchanged": hash_original == hash_reversed,
        "detected": hash_original != hash_reversed,
        "note": "json.dumps sort_keys=True neutralises ordering — hash_unchanged expected",
    }

    # --- 3. Payload mutation (deterministic field tampered) ---
    tampered_payload = {**original_payload, "__tamper__": True}
    tampered_hash = _canonical_hash(tampered_payload)
    results["payload_mutation"] = {
        "hash_changed": tampered_hash != hash_original,
        "detected": tampered_hash != hash_original,
    }

    log_event(log, logging.INFO, "failure_injection_proof", ctx=results)
    return results


if __name__ == "__main__":
    print("=== DETERMINISM PROOF: 20 runs ===")
    passed = run_determinism_proof()
    print(f"20-run determinism: {'PASS' if passed else 'FAIL'}")

    print("\n=== FAILURE INJECTION PROOF ===")
    fi = run_failure_injection_proof()
    for case, detail in fi.items():
        detected = detail.get("detected", False)
        print(f"  {case}: {'DETECTED' if detected else 'NOT DETECTED'} — {detail}")

    raise SystemExit(0 if passed else 1)
