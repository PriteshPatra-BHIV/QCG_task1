"""
Layer 1 - Quantum Producer
Simulates superdense coding to encode a classical message into a quantum channel.
"""

import hashlib
import logging

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

import config
from logger import get_logger, log_event
from models import TransmissionRequest, QuantumDistribution

log = get_logger("qcg.producer")

_SUPERDENSE_ENCODING: dict[str, list[str]] = {
    "00": [],
    "01": ["x"],
    "10": ["z"],
    "11": ["x", "z"],
}


def _message_to_bits(message: str) -> str:
    digest = hashlib.sha256(message.encode()).hexdigest()
    return f"{int(digest[:2], 16) % 4:02b}"


def _build_superdense_circuit(bits: str) -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    for gate in _SUPERDENSE_ENCODING[bits]:
        getattr(qc, gate)(0)
    qc.cx(0, 1)
    qc.h(0)
    qc.measure([0, 1], [0, 1])
    return qc


def _build_noise_model(noise_factor: float) -> NoiseModel | None:
    if noise_factor <= 0.0:
        return None
    noise_factor = min(noise_factor, 0.99)
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(noise_factor, 1), ["h", "x", "z"])
    nm.add_all_qubit_quantum_error(depolarizing_error(noise_factor / 2, 2), ["cx"])
    return nm


def run_quantum_producer(
    request: TransmissionRequest,
    shots: int = config.SHOTS,
    seed: int = config.DEFAULT_SEED,
) -> QuantumDistribution:
    """
    Encode request.message via superdense coding and simulate the quantum channel.
    Returns a QuantumDistribution. Raises ValueError on bad input.
    """
    bits = _message_to_bits(request.message)
    qc = _build_superdense_circuit(bits)
    noise_model = _build_noise_model(request.noise)

    job = AerSimulator(method="statevector").run(
        qc, shots=shots, noise_model=noise_model, seed_simulator=seed
    )
    counts = dict(job.result().get_counts())

    log_event(log, logging.INFO, "quantum_producer_complete", ctx={
        "msg_text": request.message,
        "encoded_bits": bits,
        "mode": request.mode,
        "noise": request.noise,
        "shots": shots,
        "seed": seed,
        "raw_counts": counts,
    })

    return QuantumDistribution(
        encoded_bits=bits,
        transmission_mode=request.mode,
        noise_factor=request.noise,
        shots=shots,
        counts=counts,
        seed=seed,
    )
