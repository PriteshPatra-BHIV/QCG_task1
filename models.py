"""
models.py - Typed, validated data models for the QCG pipeline.
"""

from dataclasses import dataclass, asdict
import config


@dataclass(frozen=True)
class TransmissionRequest:
    message: str
    noise: float
    mode: str

    def __post_init__(self):
        if not self.message or not self.message.strip():
            raise ValueError("message must be a non-empty string.")
        if not (0.0 <= self.noise <= 1.0):
            raise ValueError(f"noise must be in [0.0, 1.0], got {self.noise}.")
        if self.mode not in config.SUPPORTED_MODES:
            raise ValueError(
                f"mode '{self.mode}' is not supported. Choose from {config.SUPPORTED_MODES}."
            )


@dataclass(frozen=True)
class QuantumDistribution:
    encoded_bits: str
    transmission_mode: str
    noise_factor: float
    shots: int
    counts: dict
    seed: int

    def __post_init__(self):
        if not self.counts:
            raise ValueError("counts must not be empty.")
        if self.shots <= 0:
            raise ValueError("shots must be a positive integer.")


@dataclass
class ClassicalContract:
    trace_id: str
    confidence: float
    decoded_message: str
    transmission_status: str   # OK | DEGRADED | REJECTED
    uncertainty_score: float
    contract_version: str

    def to_dict(self) -> dict:
        return asdict(self)
