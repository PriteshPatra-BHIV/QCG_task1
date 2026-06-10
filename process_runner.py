"""
process_runner.py — Phase 2: Multi-Process Orchestrator

Spawns three independent OS processes:
  Process 1 (Producer)   — producer_process.py
  Process 2 (Execution)  — execution_process.py
  Process 3 (Consensus)  — consensus_process.py

IPC topology:
  producer --> [q_prod_exec] --> execution --> [q_exec_cons] --> consensus --> [q_cons_out]

Crash handling:
  Each process target wraps its logic; if it exits non-zero the runner
  logs the failure and reports which stage failed.

Run:
  python process_runner.py           # normal run
  python process_runner.py --crash producer
  python process_runner.py --crash execution
  python process_runner.py --crash consensus
"""

from __future__ import annotations

import json
import multiprocessing
import os
import sys
import time

import producer_process
import execution_process
import consensus_process


def _wrap(target_fn, queue_args: tuple, crash: bool, log_path: str):
    """Wrapper that logs the crash signal before calling the target."""
    try:
        target_fn(*queue_args, crash=crash)
    except SystemExit as e:
        _file_log(log_path, os.getpid(), target_fn.__module__, "process_exit", code=e.code)
        raise


def run_pipeline(crash_stage: str | None = None) -> dict:
    """
    Execute the full three-process pipeline.

    Returns a summary dict with process ids, acks, and consensus outcome.
    """
    # Ensure log directory exists
    os.makedirs("logs", exist_ok=True)
    # Clear old logs
    for p in ["logs/process_1.log", "logs/process_2.log", "logs/process_3.log"]:
        with open(p, "w") as f:
            pass

    q_prod_exec: multiprocessing.Queue = multiprocessing.Queue()
    q_exec_cons: multiprocessing.Queue = multiprocessing.Queue()
    q_cons_out:  multiprocessing.Queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(
        target=_wrap,
        args=(producer_process.run, (q_prod_exec,), crash_stage == "producer",
              "logs/process_1.log"),
        name="ProducerProcess",
    )
    p2 = multiprocessing.Process(
        target=_wrap,
        args=(execution_process.run, (q_prod_exec, q_exec_cons), crash_stage == "execution",
              "logs/process_2.log"),
        name="ExecutionProcess",
    )
    p3 = multiprocessing.Process(
        target=_wrap,
        args=(consensus_process.run, (q_exec_cons, q_cons_out), crash_stage == "consensus",
              "logs/process_3.log"),
        name="ConsensusProcess",
    )

    for p in (p1, p2, p3):
        p.start()

    pids = {
        "producer":   p1.pid,
        "execution":  p2.pid,
        "consensus":  p3.pid,
    }
    print(json.dumps({"event": "processes_started", "pids": pids,
                      "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))

    for p in (p1, p2, p3):
        p.join(timeout=30)

    crashes = {
        name: proc.exitcode
        for name, proc in [("producer", p1), ("execution", p2), ("consensus", p3)]
        if proc.exitcode != 0
    }

    consensus_result = None
    try:
        consensus_result = q_cons_out.get(timeout=5)
    except Exception:
        pass

    summary = {
        "pids": pids,
        "crashes": crashes,
        "consensus_result": consensus_result,
        "crash_stage_injected": crash_stage,
        "pipeline_ok": len(crashes) == 0,
    }

    print(json.dumps({"event": "pipeline_complete", **summary,
                      "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
    return summary


def _file_log(path: str, pid: int, role: str, event: str, **kwargs) -> None:
    entry = {"pid": pid, "role": role, "event": event, **kwargs,
             "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)

    crash_stage = None
    if "--crash" in sys.argv:
        idx = sys.argv.index("--crash")
        if idx + 1 < len(sys.argv):
            crash_stage = sys.argv[idx + 1]

    print(f"\n=== PROCESS RUNNER: crash_stage={crash_stage} ===\n")
    summary = run_pipeline(crash_stage=crash_stage)

    if crash_stage:
        crashed = list(summary["crashes"].keys())
        print(f"\n[Crash Handling] Stage '{crash_stage}' crashed as expected: {crashed}")
    else:
        status = "OK" if summary["pipeline_ok"] else "FAILED"
        print(f"\n[Pipeline] Status: {status}")
