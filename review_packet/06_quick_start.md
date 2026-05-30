# Quick Start — Run It in 5 Minutes

## What You Need
- Python 3.10 or higher installed
- A terminal (Command Prompt, PowerShell, or any shell)

---

## Step 1 — Install Dependencies

For running the system:
```bash
pip install -r requirements.txt
```

For running tests too:
```bash
pip install -r requirements-dev.txt
```

---

## Step 2 — (Optional) Configure Settings

Copy the example config file:
```bash
cp .env.example .env
```

Open `.env` and adjust any values you want. The defaults work fine out of the box.

---

## Step 3 — Run the Gateway Demo

```bash
python hybrid_gateway.py
```

This runs a full transmission of `NODE_READY` through the system and then runs all 5 failure scenarios. You'll see structured JSON logs in your terminal.

**Expected output (last line):**
```
{"event": "gateway_demo_result", "ctx": {"ack": "ACK:OK:NODE_READY"}}
```

---

## Step 4 — Run the Determinism Proof

```bash
python determinism_proof.py
```

Runs the same message 5 times with the same seed and verifies all outputs are identical.

- Exits with code `0` = PASSED ✅
- Exits with code `1` = FAILED ❌

---

## Step 5 — Run All Tests

```bash
pytest tests/ -v
```

Runs 35+ tests covering all 6 layers. All should pass.

---

## What You'll See in the Logs

Each log line is a JSON object. Key fields:

| Field | Meaning |
|-------|---------|
| `ts` | Timestamp (UTC) |
| `level` | INFO / WARNING / ERROR |
| `event` | What just happened |
| `ctx` | Details about that event |

Example:
```json
{
  "ts": "2025-01-15T10:23:41.123456+00:00",
  "level": "INFO",
  "logger": "qcg.gateway",
  "event": "industrial_endpoint_ack",
  "ctx": {
    "trace_id": "a3f9c2d1-...",
    "confidence": 0.9287,
    "status": "OK",
    "ack": "ACK:OK:NODE_READY"
  }
}
```

---

## Check System Health

From code:
```python
from hybrid_gateway import QuantumGateway
gw = QuantumGateway()
print(gw.health_check())
```

Output:
```json
{
  "status": "ok",
  "replay_registry_size": 0,
  "rate_limit_per_minute": 60,
  "contract_version": "1.0.0"
}
```
