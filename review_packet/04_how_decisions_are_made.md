# How the System Makes Decisions

## Two Layers of Decision

The system makes decisions at two separate layers. This separation is intentional and mandatory.

---

## Layer 1 — Uncertainty Classification (before any contract)

Before a contract is formed, the raw quantum output is classified into one of five uncertainty classes:

| Class | Condition | What It Means |
|-------|-----------|---------------|
| HIGH_CONFIDENCE | confidence ≥ 0.70 | Signal is strong. Safe to proceed. |
| LOW_CONFIDENCE | confidence in [0.40, 0.70) | Signal is weak but readable. Proceed with caution. |
| DEGRADED | noise > 0.50 AND confidence < 0.70 | Channel is too noisy. Hold until conditions improve. |
| UNTRANSLATABLE | confidence < 0.30 | Signal is too scattered to decode. Hold. |
| REJECTED | confidence < 0.40 | Below the rejection floor. Discard. |

**Key rule:** Quantum uncertainty is not the same as operational failure. UNTRANSLATABLE means "we cannot read this" — it does not mean the system failed. The system recognised the situation and responded safely.

---

## Layer 2 — Operational Outcomes (after translation)

Once a contract is formed, it is evaluated against operational context:

| Outcome | Condition | Is action permitted? |
|---------|-----------|---------------------|
| **OK** | confidence ≥ 0.70, message matches | ✅ Yes |
| **DEGRADED** | confidence in [0.40, 0.70), message matches | ✅ Yes — but warning lineage is attached |
| **HOLD** | noise > 0.50 AND status is not OK | ❌ No — suppress action |
| **REJECT** | confidence < 0.40 OR bit mismatch | ❌ No — contract is invalid |
| **HALT** | replay detected OR rate limit exceeded | ❌ No — system safety stop |

---

## The Anti-Authority Rule

The system produces a **recommendation** (OperationalPosture). It does not produce a **command**.

Even at maximum confidence:
```
Quantum confidence : 0.9326
System output      : OK:NODE_READY  ← recommendation
Authority holder   : CALLER         ← always the caller
```

The caller reads the posture and decides whether to act. The system never acts on its own behalf.

This is proven at runtime by `authority_boundary_test.py`. The proof does not just describe this rule — it runs it and verifies `authority_transferred = False`.

---

## All Response Strings

### Success responses
| Response | Meaning |
|----------|---------|
| `ACK:OK:NODE_READY` | OK — high confidence, message verified |
| `ACK:DEGRADED:NODE_READY:confidence=0.58` | DEGRADED — lower confidence, proceed with caution |

### Halt responses
| Response | Cause |
|----------|-------|
| `HALT:TRANSLATION_FAILURE` | Signal too noisy, confidence too low, or bits do not match |
| `HALT:REPLAY_DETECTED` | Same trace_id received twice — possible replay attack |
| `HALT:RATE_LIMIT_EXCEEDED` | Too many requests per minute |
| `HALT:INVALID_INPUT` | Empty, oversized, or structurally invalid message |
| `HALT:CONTRACT_DOWNGRADE` | Contract version below minimum allowed |
| `HALT:UNAUTHORIZED_PRODUCER` | Producer type not in allowed set |
| `HALT:UNEXPECTED` | Unhandled internal error — always logged with full details |

The system **never crashes**. Every path returns one of these strings.

---

## The Confidence Score — Explained Simply

Imagine flipping a coin 1,024 times. If it lands heads 955 times, you are very confident it is biased toward heads.

The system runs the quantum simulation 1,024 times and counts outcomes. If one outcome dominates, confidence is high. If results are scattered evenly, confidence is low.

```
High noise  →  scattered results  →  low confidence  →  REJECTED
Low noise   →  dominant result    →  high confidence  →  OK
```

Actual live example:
```
noise=0.02  →  { "11": 955, "10": 39, "01": 14, "00": 16 }  →  confidence=0.9326  →  OK
noise=0.60  →  { "10": 257, "00": 233, "11": 297, "01": 237 }  →  confidence=0.2900  →  HALT
```

---

## The Trace ID — Explained Simply

Every contract gets a `trace_id` generated from the message content + seed + dominant bitstring. The same transmission always produces the same ID.

This is how replay attacks are detected: if the same `trace_id` appears twice, the second submission is blocked immediately with `HALT:REPLAY_DETECTED`.
