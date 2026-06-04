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
    runs: int = 5,
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


if __name__ == "__main__":
    passed = run_determinism_proof()
    raise SystemExit(0 if passed else 1)
