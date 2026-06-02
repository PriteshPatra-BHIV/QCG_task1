"""
config.py - All tuneable constants in one place.
Override any value via environment variable or a .env file.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _str(key: str, default: str) -> str:
    return os.environ.get(key, default)


# -- Quantum Producer ---------------------------------------------------------
SHOTS: int                  = _int("QCG_SHOTS", 1024)
DEFAULT_SEED: int           = _int("QCG_SEED", 42)
SUPPORTED_MODES: set        = set(_str("QCG_SUPPORTED_MODES", "entangled,direct,superdense").split(","))
MAX_MESSAGE_LENGTH: int     = _int("QCG_MAX_MESSAGE_LENGTH", 256)

# -- Translation Layer --------------------------------------------------------
CONTRACT_VERSION: str       = _str("QCG_CONTRACT_VERSION", "1.0.0")
CONFIDENCE_THRESHOLD: float = _float("QCG_CONFIDENCE_THRESHOLD", 0.70)
CORRUPTION_THRESHOLD: float = _float("QCG_CORRUPTION_THRESHOLD", 0.40)

# -- Gateway ------------------------------------------------------------------
RATE_LIMIT_PER_MINUTE: int  = _int("QCG_RATE_LIMIT_PER_MINUTE", 60)

# -- Logging ------------------------------------------------------------------
LOG_LEVEL: str              = _str("QCG_LOG_LEVEL", "INFO")   # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT: str             = _str("QCG_LOG_FORMAT", "json")  # json | text

# -- Adapter Layer ------------------------------------------------------------
EXECUTION_CONTRACT_VERSION: str = _str("QCG_EXEC_CONTRACT_VERSION", "2.0.0")
MINIMUM_CONTRACT_VERSION: str   = _str("QCG_MIN_CONTRACT_VERSION", "2.0.0")
ALLOWED_PRODUCER_TYPES: set     = set(_str("QCG_ALLOWED_PRODUCERS", "CLASSICAL,QUANTUM,HYBRID").split(","))
GOVERNANCE_STRICT_MODE: bool    = _str("QCG_GOVERNANCE_STRICT", "true").lower() == "true"

# -- Distributed Simulation ---------------------------------------------------
SIMULATION_NODE_COUNT: int      = _int("QCG_SIM_NODE_COUNT", 3)
SIMULATION_PRODUCER_COUNT: int  = _int("QCG_SIM_PRODUCER_COUNT", 2)


def validate():
    """Validate config at startup. Raises ValueError on bad values."""
    if not (0.0 < CONFIDENCE_THRESHOLD <= 1.0):
        raise ValueError(f"QCG_CONFIDENCE_THRESHOLD must be in (0, 1], got {CONFIDENCE_THRESHOLD}")
    if not (0.0 < CORRUPTION_THRESHOLD <= 1.0):
        raise ValueError(f"QCG_CORRUPTION_THRESHOLD must be in (0, 1], got {CORRUPTION_THRESHOLD}")
    if CORRUPTION_THRESHOLD >= CONFIDENCE_THRESHOLD:
        raise ValueError(
            f"QCG_CORRUPTION_THRESHOLD ({CORRUPTION_THRESHOLD}) must be "
            f"less than QCG_CONFIDENCE_THRESHOLD ({CONFIDENCE_THRESHOLD})"
        )
    if SHOTS <= 0:
        raise ValueError(f"QCG_SHOTS must be positive, got {SHOTS}")
    if MAX_MESSAGE_LENGTH <= 0:
        raise ValueError(f"QCG_MAX_MESSAGE_LENGTH must be positive, got {MAX_MESSAGE_LENGTH}")
    if RATE_LIMIT_PER_MINUTE <= 0:
        raise ValueError(f"QCG_RATE_LIMIT_PER_MINUTE must be positive, got {RATE_LIMIT_PER_MINUTE}")
    if SIMULATION_NODE_COUNT <= 0:
        raise ValueError(f"QCG_SIM_NODE_COUNT must be positive, got {SIMULATION_NODE_COUNT}")
    if SIMULATION_PRODUCER_COUNT <= 0:
        raise ValueError(f"QCG_SIM_PRODUCER_COUNT must be positive, got {SIMULATION_PRODUCER_COUNT}")


validate()
