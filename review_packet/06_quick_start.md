# Quick Start — Run It in 5 Minutes

## What You Need
- Python 3.10 or higher
- pip
- A terminal (Command Prompt, PowerShell, or any shell)

---

## Step 1 — Install Dependencies

```bash
# Production only
pip install -r requirements.txt

# Production + tests
pip install -r requirements-dev.txt
```

No C++ compiler required. Pre-built wheels for Python 3.10–3.13 on Windows, macOS, and Linux are available on PyPI.

---

## Step 2 — (Optional) Configure Settings

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and adjust any values. The defaults work fine out of the box. See `.env.example` for every available setting.

---

## Step 3 — Run the Doctrine Proof (Phase 6 — recommended first run)

```bash
python run_semantics_runtime.py
```

Runs all 5 runtime cases (A–E). Expected:
```
OVERALL: ALL CASES PASSED
```
Exit code 0 = pass. This is the primary proof entry point.

---

## Step 4 — Run the Anti-Authority Proof (Phase 5)

```bash
python authority_boundary_test.py
```

Expected:
```
authority_transferred : False  <- must be False
authority_holder      : CALLER <- always CALLER
VERDICT: PASS
```

---

## Step 5 — Run the Determinism Proof

```bash
python determinism_proof.py
```

Runs the same transmission 5 times with the same seed, verifies zero mismatches.
- Exit code `0` = PASSED ✅
- Exit code `1` = FAILED ❌

---

## Step 6 — Run All Tests

```bash
pytest tests/ -v
```

Expected: **122 tests passing**.

---

## Step 7 — Run the Full Gateway Demo

```bash
python hybrid_gateway.py
```

Full pipeline demo + all failure scenarios. Expected last log event:
```json
{"event": "gateway_demo_result", "ctx": {"ack": "ACK:OK:NODE_READY"}}
```

---

## All Proof Entry Points at a Glance

| Command | What It Proves |
|---------|---------------|
| `python run_semantics_runtime.py` | All 5 runtime cases pass, no silent states |
| `python authority_boundary_test.py` | System never becomes execution authority |
| `python contract_semantics.py` | Determinism + convergence |
| `python degraded_runtime.py` | All 5 outcome boundaries observable |
| `python lineage.py` | Full lineage reconstruction, no hidden state |
| `python determinism_proof.py` | 5-run seed-locked determinism |
| `pytest tests/ -q` | 122 automated tests pass |

---

## Understanding the Log Output

Each line is a JSON object:

| Field | Meaning |
|-------|---------|
| `ts` | Timestamp (UTC, ISO-8601) |
| `level` | INFO / WARNING / ERROR |
| `logger` | Which module emitted this |
| `event` | What just happened |
| `ctx` | Structured details |

Example:
```json
{
  "ts": "2026-06-03T10:46:01.984804+00:00",
  "level": "INFO",
  "logger": "qcg.translation",
  "event": "translation_complete",
  "ctx": {
    "trace_id": "c987207f-a809-54e9-b64b-e7940c28f291",
    "confidence": 0.6807,
    "status": "DEGRADED",
    "decoded_msg": "NODE_READY"
  }
}
```

Rejection events log at WARNING level so monitoring tools catch them.

---

## Check System Health

```python
from hybrid_gateway import QuantumGateway
gw = QuantumGateway()
print(gw.health_check())
```

```json
{
  "status": "ok",
  "replay_registry_size": 0,
  "rate_limit_per_minute": 60,
  "contract_version": "1.0.0"
}
```
