# PROCESS_MODEL.md

> Phase 2: Multi-Process Execution — Architecture and Evidence

---

## Objective

Replace single-process execution assumptions with three independent OS processes
that communicate via IPC queues.

---

## Process Inventory

| Process File | Role | Log File |
|--------------|------|----------|
| `producer_process.py` | Produces signed `ComputationExecutionContract` | `logs/process_1.log` |
| `execution_process.py` | Validates provenance, enforces replay, executes contract | `logs/process_2.log` |
| `consensus_process.py` | Runs 3-node consensus, emits `ConsensusProof` | `logs/process_3.log` |
| `process_runner.py` | Spawns all three, routes IPC, detects crashes | stdout + all log files |

---

## IPC Architecture

```
producer_process
      |
      |  multiprocessing.Queue  (q_prod_exec)
      |  Message: { "type": "CONTRACT", "contract": {...}, "producer_public_key": "...", "issued_at": float }
      v
execution_process
      |
      |  multiprocessing.Queue  (q_exec_cons)
      |  Message: { "type": "EXECUTION_RESULT",
      |             "result": { ...ExecutionResult... },
      |             "contract": { ...original signed contract... },
      |             "producer_public_key": "<hex DER>",
      |             "issued_at": float }
      v
consensus_process
      |
      |  multiprocessing.Queue  (q_cons_out)
      |  Message: { "type": "CONSENSUS_PROOF", "proof": {...} }
      v
process_runner (collector)
```

Termination signal: `{ "type": "DONE" }` propagates through all queues.

---

## Crash Handling

Each process runs inside a `_wrap()` function in `process_runner.py`.
A crash is simulated by passing `crash=True` to the process target, which
calls `sys.exit(1)`.

`multiprocessing.Process.join(timeout=30)` is used; after join, `exitcode != 0`
signals a crash.

| Injected Crash | `crashes` dict | Pipeline Status |
|----------------|---------------|-----------------|
| None | `{}` | `pipeline_ok=True` |
| `producer` | `{"producer": 1}` | `pipeline_ok=False` |
| `execution` | `{"execution": 1}` | `pipeline_ok=False` |
| `consensus` | `{"consensus": 1}` | `pipeline_ok=False` |

---

## Log Evidence

Each log file contains JSON lines with fields:

```json
{"pid": 12345, "role": "PRODUCER", "event": "started", "ts": "2026-06-07T10:00:00Z"}
{"pid": 12345, "role": "PRODUCER", "event": "contract sent", "trace_id": "proc-trace-001", "ts": "..."}
{"pid": 12346, "role": "EXECUTION", "event": "replay_check", "trace_id": "proc-trace-001", "status": "ACCEPTED", "seq": 1, "ts": "..."}
{"pid": 12347, "role": "CONSENSUS", "event": "consensus_complete", "reached": true, "agreement": "100%", "ts": "..."}
```

Log files prove: independent PIDs, message flow order, and execution timestamps.

---

## Replay Reconstruction from Logs

To reconstruct execution sequence from logs alone:

```bash
# Sort all three logs by timestamp and merge
sort logs/process_1.log logs/process_2.log logs/process_3.log | python -c "
import sys, json
lines = [json.loads(l) for l in sys.stdin if l.strip()]
lines.sort(key=lambda x: (x['ts'], x['pid']))
for l in lines:
    print(f\"{l['ts']}  [{l['role']:10s}]  {l['event']}\")
"
```

The reconstructed sequence will show:
1. PRODUCER started → contract sent
2. EXECUTION started → replay_check ACCEPTED → executed
3. CONSENSUS started → consensus_complete

---

## Known Limitations

- IPC uses `multiprocessing.Queue` (shared memory), not a network socket.
  Real deployment would use Unix sockets, ZeroMQ, or gRPC.
- `multiprocessing.set_start_method("spawn")` is required on Windows.
- Crash detection is exit-code based. Real deployment needs health-check heartbeats.
- Consensus nodes within `consensus_process.py` share the same OS process; true
  network-separated consensus requires real transport between separate processes.
