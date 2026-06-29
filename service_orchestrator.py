"""
service_orchestrator.py - Production-Grade Orchestrator for QCG Distributed Runtime.
Spawns and coordinates independent services over network interfaces.
"""

import os
import sys
import json
import time
import urllib.request
import multiprocessing
from typing import Dict, List, Any

import config
import runtime_services
from capability_registry import CapabilityRegistryServer

def _run_service_process(service_name: str, crash: bool = False):
    """Wrapper function to execute a service inside a child process."""
    if crash:
        print(f"[Orchestrator] Simulated crash injected for '{service_name}'", flush=True)
        sys.exit(1)

    # Invoke service runners based on name
    try:
        if service_name == "registry":
            runtime_services.start_health_server(config.REGISTRY_PORT + 100)
            server = CapabilityRegistryServer("127.0.0.1", config.REGISTRY_PORT)
            server.start()
            while True:
                time.sleep(1)
        elif service_name == "replay":
            runtime_services.run_replay_service()
        elif service_name == "trust":
            runtime_services.run_trust_service()
        elif service_name == "producer":
            runtime_services.run_producer_service()
        elif service_name == "execution":
            runtime_services.run_execution_service()
        elif service_name == "consensus":
            runtime_services.run_consensus_service()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[Orchestrator] Service '{service_name}' exited with error: {e}", flush=True)
        sys.exit(1)

def check_http_health(port: int, timeout: float = 1.0) -> bool:
    """Check health status of a service via its HTTP health endpoint."""
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
            return data.get("status") == "UP"
    except Exception:
        return False

def run_distributed_pipeline(crash_stage: str | None = None) -> dict:
    """Spawn and manage the full 6-service distributed runtime."""
    print("[Orchestrator] Preparing distributed pipeline...", flush=True)
    os.makedirs("logs", exist_ok=True)
    
    # Clean consensus output log
    consensus_log = "logs/consensus_output.log"
    if os.path.exists(consensus_log):
        try: os.unlink(consensus_log)
        except OSError: pass

    processes = {}
    
    # 1. Start Capability Registry
    p_registry = multiprocessing.Process(
        target=_run_service_process,
        args=("registry", crash_stage == "registry"),
        name="RegistryService"
    )
    p_registry.start()
    processes["registry"] = (p_registry, config.REGISTRY_PORT + 100)

    # Wait for registry to become healthy
    print("[Orchestrator] Waiting for Capability Registry...", flush=True)
    registry_healthy = False
    for _ in range(50):
        if check_http_health(config.REGISTRY_PORT + 100):
            registry_healthy = True
            break
        time.sleep(0.1)

    if not registry_healthy:
        print("[Orchestrator] Error: Registry failed to boot. Aborting.", flush=True)
        p_registry.terminate()
        return {"pipeline_ok": False, "crashes": {"registry": -1}}

    print("[Orchestrator] Registry online. Launching dependencies...", flush=True)

    # 2. Launch Replay, Trust, and Consensus services
    for name, port in [("replay", config.REPLAY_PORT), ("trust", config.TRUST_PORT), ("consensus", config.CONSENSUS_PORT)]:
        p = multiprocessing.Process(
            target=_run_service_process,
            args=(name, crash_stage == name),
            name=f"{name.capitalize()}Service"
        )
        p.start()
        processes[name] = (p, port + 100)

    # Wait for dependencies to start up
    time.sleep(1.0)

    # 3. Launch Execution Service
    p_exec = multiprocessing.Process(
        target=_run_service_process,
        args=("execution", crash_stage == "execution"),
        name="ExecutionService"
    )
    p_exec.start()
    processes["execution"] = (p_exec, config.EXECUTION_PORT + 100)

    # Wait for execution to start up
    time.sleep(1.0)

    # 4. Launch Producer Service (triggers contract emission)
    p_prod = multiprocessing.Process(
        target=_run_service_process,
        args=("producer", crash_stage == "producer"),
        name="ProducerService"
    )
    p_prod.start()
    processes["producer"] = (p_prod, config.PRODUCER_PORT + 100)

    # Monitor loop
    start_time = time.time()
    pipeline_ok = True
    crashes = {}

    print("[Orchestrator] Distributed pipeline started. Monitoring health...", flush=True)

    while True:
        # Check if producer is finished
        if not p_prod.is_alive() and p_prod.exitcode == 0:
            # Check if consensus has written the outcome
            if os.path.exists(consensus_log) and os.path.getsize(consensus_log) > 0:
                print("[Orchestrator] Consensus output received. Terminating pipeline gracefully.", flush=True)
                break

        # Check for timeouts
        if time.time() - start_time > 30:
            print("[Orchestrator] Timeout (30s) reached.", flush=True)
            pipeline_ok = False
            break

        # Check health endpoints and process status
        for name, (p, h_port) in list(processes.items()):
            # If process exited with non-zero
            if not p.is_alive() and p.exitcode not in (0, None):
                print(f"[Orchestrator] Process '{name}' crashed with code {p.exitcode}", flush=True)
                crashes[name] = p.exitcode
                pipeline_ok = False
            
            # If service is alive but HTTP health query fails
            if p.is_alive() and name != "producer":
                if not check_http_health(h_port):
                    print(f"[Orchestrator] Service '{name}' failed health check", flush=True)
                    p.terminate()
                    crashes[name] = -1
                    pipeline_ok = False

        if not pipeline_ok:
            break

        time.sleep(0.5)

    # Terminate remaining processes gracefully
    print("[Orchestrator] Shutting down services...", flush=True)
    for name, (p, _) in processes.items():
        if p.is_alive():
            p.terminate()
            p.join(timeout=2)
            if p.is_alive():
                os.system(f"taskkill /F /PID {p.pid}" if sys.platform == "win32" else f"kill -9 {p.pid}")

    # Read consensus proof results
    consensus_result = None
    if os.path.exists(consensus_log) and os.path.getsize(consensus_log) > 0:
        try:
            with open(consensus_log, "r") as f:
                lines = f.readlines()
                if lines:
                    consensus_result = json.loads(lines[-1])
        except Exception as e:
            print(f"[Orchestrator] Error parsing consensus log: {e}", flush=True)

    summary = {
        "crashes": crashes,
        "consensus_result": consensus_result,
        "crash_stage_injected": crash_stage,
        "pipeline_ok": pipeline_ok and len(crashes) == 0,
    }

    print(f"[Orchestrator] Summary: {summary}", flush=True)
    return summary

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    crash_stage = None
    if "--crash" in sys.argv:
        idx = sys.argv.index("--crash")
        if idx + 1 < len(sys.argv):
            crash_stage = sys.argv[idx + 1]

    run_distributed_pipeline(crash_stage=crash_stage)
