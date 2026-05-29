# Hybrid Quantum Communication Gateway (QCG)

A deterministic hybrid quantum/classical communication gateway built with Qiskit.
Bridges probabilistic quantum output to deterministic classical contracts.

## Architecture

```
TransmissionRequest
      |
      v
[Layer 1] QuantumProducer       -- Qiskit superdense coding simulation
      |
      v  QuantumDistribution
      |
[Layer 2] TranslationLayer      -- Probabilistic -> deterministic contract
      |
      v  ClassicalContract
      |
[Layer 3] QuantumGateway        -- Orchestrates devices + replay guard
      |
      v
[IndustrialEndpoint]            -- Deterministic ACK
```

### ClassicalContract schema
```json
{
  "trace_id":           "<uuid5>",
  "confidence":         0.9287,
  "decoded_message":    "NODE_READY",
  "transmission_status":"OK",
  "uncertainty_score":  0.0713,
  "contract_version":   "1.0.0"
}
```

Transmission statuses:
- `OK`       -- confidence >= 0.70, bits match
- `DEGRADED` -- confidence in [0.40, 0.70), bits match
- `REJECTED` -- confidence < 0.40, or bit mismatch (raises TranslationError)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: tune thresholds / log format
```

## Run

```bash
# Full gateway demo + failure tests
python hybrid_gateway.py

# Determinism proof (exits 0 on pass, 1 on fail)
python determinism_proof.py
```

## Test

```bash
pytest tests/ -v
```

## Configuration

All constants are in `config.py` and overridable via environment variables.
See `.env.example` for the full list.

## File Structure

```
config.py            -- All constants, env-overridable
logger.py            -- Structured JSON logger
models.py            -- Typed, validated data models
quantum_producer.py  -- Layer 1: Qiskit quantum simulation
translation_layer.py -- Layer 2: QuantumDistribution -> ClassicalContract
hybrid_gateway.py    -- Layers 3+4+5: Gateway, devices, failure handling
determinism_proof.py -- Layer 6: Determinism verification
tests/test_all.py    -- Full pytest suite
.env.example         -- Config reference
requirements.txt     -- Dependencies
```
