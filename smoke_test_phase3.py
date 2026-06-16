"""Smoke test for Phase 3 and Phase 4 changes."""
import os, sys, time, tempfile

# ── Phase 3: CanonicalReplayAuthority ────────────────────────────────────────
from canonical_replay_authority import CanonicalReplayAuthority
from replay_registry import ReplayRegistry

tmp = tempfile.mktemp(suffix=".json")
auth = CanonicalReplayAuthority(ReplayRegistry(path=tmp))

v1 = auth.submit("msg-001")
assert v1.status == "VALID",     f"expected VALID got {v1.status}"
assert v1.sequence_number == 1,  f"expected seq 1 got {v1.sequence_number}"
assert v1.lineage_record.verification_hash != ""
print("submit() VALID                  OK")

v2 = auth.submit("msg-001")
assert v2.status == "DUPLICATE", f"expected DUPLICATE got {v2.status}"
print("submit() DUPLICATE              OK")

v3 = auth.submit("msg-stale", issued_at=time.time() - 9999)
assert v3.status == "STALE",     f"expected STALE got {v3.status}"
print("submit() STALE                  OK")

lk = auth.lookup("msg-001")
assert lk is not None and lk.status == "DUPLICATE"
assert auth.lookup("never-seen") is None
print("lookup()                        OK")

ss = auth.sequence_status()
assert ss["sequence_counter"] == 1
assert ss["last_message_id"] == "msg-001"
print("sequence_status()               OK")

lin = auth.lineage()
assert len(lin) == 1 and lin[0].message_id == "msg-001"
print("lineage()                       OK")

rpt = auth.verification_report()
assert rpt["valid_count"] == 1
assert rpt["total_submitted"] == 2  # msg-001 (deduped key) + msg-stale
print("verification_report()           OK")

os.unlink(tmp)

# ── Phase 4: RuntimeCore has no _replay_registry ─────────────────────────────
from runtime_core import RuntimeCore
rc = RuntimeCore()
assert not hasattr(rc, "_replay_registry"), "RuntimeCore must not own _replay_registry"
assert not hasattr(rc, "_registry_lock"),   "RuntimeCore must not own _registry_lock"
print("RuntimeCore no replay state     OK")

# ── Phase 4: Receiver uses authority, not _seen dict ─────────────────────────
import inspect
with open("gateway.py") as f:
    src = f.read()
assert "self._seen" not in src,         "Receiver must not own _seen dict"
assert "CanonicalReplayAuthority" in src or "_authority" in src
print("Receiver no _seen dict          OK")

# ── Phase 4: QuantumGateway uses authority, not _replay_registry ─────────────
with open("hybrid_gateway.py") as f:
    src_gw = f.read()
assert "self._replay_registry" not in src_gw, "QuantumGateway must not own _replay_registry"
assert "CanonicalReplayAuthority" in src_gw or "replay_authority" in src_gw
print("QuantumGateway no _replay_registry OK")

# ── Phase 4: execution_process uses CanonicalReplayAuthority ─────────────────
with open("execution_process.py") as f:
    ep_src = f.read()
assert "ReplayEnforcer" not in ep_src,        "execution_process must not use ReplayEnforcer"
assert "CanonicalReplayAuthority" in ep_src
print("execution_process no ReplayEnforcer OK")

print("\n=== PHASE 3 + PHASE 4 SMOKE TEST PASS ===")
