# What Each File Does

A plain-English guide to every file in the project.

---

## Core Files

### `config.py` — The Settings Panel
All the dials and switches for the system in one place.
- How many times to run the quantum simulation (shots)
- How confident we need to be before saying "OK"
- How noisy a channel can be before we reject it
- Maximum message length, rate limits, log format

You can change any of these without touching the code — just edit the `.env` file.

---

### `models.py` — The Data Shapes
Defines exactly what a valid message looks like, what a quantum result looks like, and what a final contract looks like.

Think of it as the **forms** the system uses — every piece of data must fill out the right form before it can move to the next step.

---

### `logger.py` — The Black Box Recorder
Every action the system takes gets written to a log — like a flight recorder.

In production mode it writes clean JSON lines (easy for monitoring tools to read).
In development mode it writes human-readable text.

---

### `quantum_producer.py` — The Quantum Sender (Layer 1)
Takes your message and simulates sending it through a quantum channel.

Uses a real quantum computing library (Qiskit) to build and run the simulation.
Adds realistic noise based on the noise level you provide.
Returns a probability distribution — the raw quantum output.

---

### `translation_layer.py` — The Translator (Layer 2)
The most important file.

Takes the fuzzy quantum output and converts it into a clean, structured contract.
Makes the confidence/rejection decision.
Ensures no raw probabilities ever leak to the outside world.

---

### `hybrid_gateway.py` — The Orchestrator (Layers 3, 4, 5)
The main controller. It:
- Runs the full pipeline from message → ACK
- Enforces rate limiting (no more than N requests per minute)
- Guards against replay attacks (same message sent twice)
- Never crashes — always returns a safe response string
- Exposes a health check so monitoring tools can verify it's alive

---

### `determinism_proof.py` — The Consistency Checker (Layer 6)
Runs the same message with the same settings 5 times and proves every output is identical.

This is the guarantee that the system is reliable and predictable — not random.

---

### `tests/test_all.py` — The Test Suite
35+ automated tests that verify every part of the system works correctly — including all failure scenarios, thread safety, and the determinism proof.

Run with: `pytest tests/ -v`

---

## Configuration Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Production dependencies (what the system needs to run) |
| `requirements-dev.txt` | Development dependencies (adds testing tools) |
| `.env.example` | Template showing all available settings |

---

## Summary Table

| File | Layer | One Job |
|------|-------|---------|
| `quantum_producer.py` | 1 | Send message through quantum channel |
| `translation_layer.py` | 2 | Convert quantum output to clean contract |
| `hybrid_gateway.py` | 3, 4, 5 | Orchestrate, protect, observe |
| `determinism_proof.py` | 6 | Prove consistency |
| `config.py` | — | All settings in one place |
| `models.py` | — | Define data shapes |
| `logger.py` | — | Record everything |
| `tests/test_all.py` | — | Verify everything works |
