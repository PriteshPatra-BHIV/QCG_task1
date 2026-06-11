"""
replay_enforcement_proof.py — Phase 2: Durable Replay Enforcement Proof

Demonstrates:
  1. Duplicate rejection
  2. Stale message rejection
  3. Sequence ordering validation
  4. Registry persistence across simulated restarts

Exit codes:
    0 — all proof cases pass
    1 — one or more proof cases failed
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from replay_registry import ReplayRegistry

PROOF_REGISTRY_PATH = Path("replay_registry_proof.json")


def _section(title: str) -> None:
    print(f"\n  [{title}]")


def run_proof(verbose: bool = True) -> dict:
    results: dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Case 1: Valid first submission → VALID
    # ------------------------------------------------------------------
    reg = ReplayRegistry(path=PROOF_REGISTRY_PATH, ttl_seconds=60.0)
    reg.reset()

    d = reg.submit("msg-001")
    results["valid_first_submission"] = d.status == "VALID" and d.sequence_number == 1
    if verbose:
        _section("Case 1: First submission")
        print(f"    status={d.status}  seq={d.sequence_number}  "
              f"pass={results['valid_first_submission']}")

    # ------------------------------------------------------------------
    # Case 2: Duplicate rejection → DUPLICATE
    # ------------------------------------------------------------------
    d2 = reg.submit("msg-001")
    results["duplicate_rejected"] = d2.status == "DUPLICATE"
    if verbose:
        _section("Case 2: Duplicate rejection")
        print(f"    status={d2.status}  seq={d2.sequence_number}  "
              f"pass={results['duplicate_rejected']}")

    # ------------------------------------------------------------------
    # Case 3: Stale message rejection → STALE
    # ------------------------------------------------------------------
    stale_registry = ReplayRegistry(path=PROOF_REGISTRY_PATH, ttl_seconds=5.0)
    stale_registry.reset()
    stale_issued = time.time() - 60.0   # 60s old, TTL=5s
    d3 = stale_registry.submit("msg-stale", issued_at=stale_issued)
    results["stale_rejected"] = d3.status == "STALE"
    if verbose:
        _section("Case 3: Stale rejection")
        print(f"    status={d3.status}  reason='{d3.reason}'  "
              f"pass={results['stale_rejected']}")

    # ------------------------------------------------------------------
    # Case 4: Sequence ordering — monotonically increasing
    # ------------------------------------------------------------------
    seq_reg = ReplayRegistry(path=PROOF_REGISTRY_PATH, ttl_seconds=60.0)
    seq_reg.reset()
    seqs = [seq_reg.submit(f"seq-msg-{i}").sequence_number for i in range(5)]
    results["sequence_monotonic"] = seqs == list(range(1, 6))
    if verbose:
        _section("Case 4: Sequence ordering")
        print(f"    sequences={seqs}  pass={results['sequence_monotonic']}")

    # ------------------------------------------------------------------
    # Case 5: Sequence validation helper
    # ------------------------------------------------------------------
    v_valid  = seq_reg.validate_sequence_order(3)
    v_stale  = seq_reg.validate_sequence_order(0)
    v_future = seq_reg.validate_sequence_order(9999)
    results["sequence_validation"] = (
        v_valid == "VALID" and v_stale == "STALE" and v_future == "FUTURE"
    )
    if verbose:
        _section("Case 5: Sequence validation")
        print(f"    seq=3->{v_valid}  seq=0->{v_stale}  seq=9999->{v_future}  "
              f"pass={results['sequence_validation']}")

    # ------------------------------------------------------------------
    # Case 6: Persistence across restart
    # ------------------------------------------------------------------
    persist_path = Path("replay_registry_persist_proof.json")
    reg_before = ReplayRegistry(path=persist_path, ttl_seconds=60.0)
    reg_before.reset()
    reg_before.submit("persist-001")
    reg_before.submit("persist-002")
    seq_before = reg_before.sequence_count
    count_before = reg_before.entry_count

    # Simulate restart: create new instance pointing to the same file
    reg_after = ReplayRegistry(path=persist_path, ttl_seconds=60.0)
    seq_after = reg_after.sequence_count
    count_after = reg_after.entry_count

    # The first post-restart submission must continue from where we left off
    d_after = reg_after.submit("persist-003")
    results["persistence_survives_restart"] = (
        seq_before == seq_after
        and count_before == count_after
        and reg_after.is_known("persist-001")
        and reg_after.is_known("persist-002")
        and d_after.sequence_number == seq_before + 1
    )
    if verbose:
        _section("Case 6: Restart persistence")
        print(f"    seq_before={seq_before}  seq_after_reload={seq_after}")
        print(f"    known persist-001={reg_after.is_known('persist-001')}")
        print(f"    post-restart seq={d_after.sequence_number}  "
              f"pass={results['persistence_survives_restart']}")

    # Cleanup proof files
    for p in [PROOF_REGISTRY_PATH, persist_path]:
        if p.exists():
            p.unlink()

    all_passed = all(results.values())

    if verbose:
        print(f"\n{'='*60}")
        status = "PASS" if all_passed else "FAIL"
        print(f"  REPLAY ENFORCEMENT PROOF - {status}")
        print(f"{'='*60}")
        for case, passed in results.items():
            mark = "[PASS]" if passed else "[FAIL]"
            print(f"  {mark}  {case}")
        print(f"{'='*60}\n")

    return {"passed": all_passed, "cases": results}


if __name__ == "__main__":
    proof = run_proof()
    sys.exit(0 if proof["passed"] else 1)
