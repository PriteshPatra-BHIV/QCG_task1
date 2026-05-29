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
SHOTS: int               = _int("QCG_SHOTS", 1024)
DEFAULT_SEED: int        = _int("QCG_SEED", 42)
SUPPORTED_MODES: set     = {"entangled", "direct", "superdense"}

# -- Translation Layer --------------------------------------------------------
CONTRACT_VERSION: str    = _str("QCG_CONTRACT_VERSION", "1.0.0")
CONFIDENCE_THRESHOLD: float  = _float("QCG_CONFIDENCE_THRESHOLD", 0.70)
CORRUPTION_THRESHOLD: float  = _float("QCG_CORRUPTION_THRESHOLD", 0.40)

# -- Logging ------------------------------------------------------------------
LOG_LEVEL: str           = _str("QCG_LOG_LEVEL", "INFO")   # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT: str          = _str("QCG_LOG_FORMAT", "json")  # json | text
