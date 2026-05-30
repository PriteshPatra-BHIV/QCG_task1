# How the System Makes Decisions

## The Three Outcomes

Every transmission ends in one of three states:

---

### ✅ OK
**What it means:** The message arrived clearly and we're confident it's correct.

**When it happens:** Confidence is 70% or higher AND the decoded message matches what was sent.

**Response:** `ACK:OK:NODE_READY`

---

### ⚠️ DEGRADED
**What it means:** The message probably arrived correctly, but the signal was weak. We're less sure than we'd like to be.

**When it happens:** Confidence is between 40% and 70% AND the decoded message still matches.

**Response:** `ACK:DEGRADED:NODE_READY:confidence=0.58`

The system still delivers the message but flags it so the receiver knows to treat it with caution.

---

### ❌ REJECTED
**What it means:** We can't trust this transmission. Either the signal was too noisy, or the message doesn't match what was originally sent.

**When it happens:**
- Confidence drops below 40%, OR
- The decoded bits don't match the original message (corruption detected)

**Response:** `HALT:TRANSLATION_FAILURE`

The message is thrown away. Nothing unsafe passes through.

---

## The Other HALT Responses

| Response | Cause |
|----------|-------|
| `HALT:REPLAY_DETECTED` | The exact same message (same trace ID) was already received. Possible replay attack. |
| `HALT:RATE_LIMIT_EXCEEDED` | Too many requests in a short time. The system is protecting itself from overload. |
| `HALT:INVALID_INPUT` | The message was empty, too long, or the mode/noise values were invalid. |
| `HALT:UNEXPECTED` | Something unexpected went wrong internally. Always logged with full details. |

---

## The Confidence Score — Explained Simply

Imagine you flip a coin 1024 times. If it lands heads 950 times, you're very confident the coin is biased toward heads.

The system does the same thing — it runs the quantum simulation 1024 times and counts the results. If one outcome dominates, confidence is high. If results are scattered evenly, confidence is low (too much noise).

```
High noise  →  scattered results  →  low confidence  →  REJECTED
Low noise   →  dominant result    →  high confidence  →  OK
```

---

## The Trace ID — Explained Simply

Every contract gets a unique ID called a `trace_id`. It's generated from the message content + seed + result — so the same transmission always produces the same ID.

This is how the system detects replays: if it sees the same `trace_id` twice, it knows someone is re-sending an old message and blocks it.
