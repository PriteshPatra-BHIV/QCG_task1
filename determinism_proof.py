"""
Layer 6 - Determinism Proof
Same seed + same message -> identical ClassicalContract across N runs.
"""

import logging

import config
from logger import get_logger, log_event
from models import TransmissionRequest
from quantum_producer import run_quantum_producer
from translation_layer import translate

log = get_logger("qcg.determinism")


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
    for i in range(runs):
        dist = run_quantum_producer(request, seed=seed)
        contract = translate(dist, message)
        results.append(contract.to_dict())
        log_event(log, logging.DEBUG, "determinism_run", ctx={
            "run": i + 1, "contract": contract.to_dict()
        })

    reference = results[0]
    all_match = all(r == reference for r in results)
    mismatches = [i + 1 for i, r in enumerate(results) if r != reference]

    log_event(log, logging.INFO, "determinism_proof_result", ctx={
        "passed": all_match,
        "runs": runs,
        "mismatches": mismatches,
        "reference_contract": reference,
    })
    return all_match


if __name__ == "__main__":
    passed = run_determinism_proof()
    raise SystemExit(0 if passed else 1)
