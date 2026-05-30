# How a Message Travels Through the System

## The Journey of "NODE_READY"

---

### Step 1 — You Send a Message
You provide three things:
- The **message** you want to send (e.g. `NODE_READY`)
- How much **noise** is on the channel (e.g. `0.12` = 12% interference)
- The **mode** of transmission (e.g. `entangled`)

---

### Step 2 — Quantum Encoding (Layer 1)
The message gets converted into a quantum signal using a technique called **superdense coding** — a real quantum physics method that encodes 2 bits of information using just 1 qubit.

Think of it like compressing a letter into a secret code before sending it.

The signal is then sent through a simulated quantum channel — complete with realistic noise and interference.

**Output:** A probability distribution. Example:
```
{ "00": 12, "01": 8, "10": 950, "11": 54 }
```
This means: out of 1024 attempts, the signal landed on "10" most often.

---

### Step 3 — Translation (Layer 2)
This is the most important step.

The system looks at the probability distribution and asks:
- What was the most common result? → `"10"`
- How confident are we? → `92.8%`
- Does that match the original message? → Yes ✅
- What's the final verdict?

It produces a **Classical Contract** — a clean, structured decision:
```
{
  "trace_id":            "a3f9...",
  "confidence":          0.9287,
  "decoded_message":     "NODE_READY",
  "transmission_status": "OK",
  "uncertainty_score":   0.0713,
  "contract_version":    "1.0.0"
}
```

No raw probabilities. No quantum jargon. Just a clear answer.

---

### Step 4 — Classical Receiver (Layer 3)
A traditional computer receives the contract and responds:
```
ACK:OK:NODE_READY
```
Done. The message was received, verified, and acknowledged — just like any normal system would expect.

---

### Step 5 — Safety Checks (Layer 4)
Before accepting any message, the system checks:

| Situation | What Happens |
|-----------|-------------|
| Too much noise | `HALT:TRANSLATION_FAILURE` |
| Low confidence | `HALT:TRANSLATION_FAILURE` |
| Message was corrupted | `HALT:TRANSLATION_FAILURE` |
| Same message sent twice | `HALT:REPLAY_DETECTED` |
| Too many requests | `HALT:RATE_LIMIT_EXCEEDED` |

The system **never crashes** — it always returns a clear, safe response.

---

### The Full Picture

```
You
 │
 │  "NODE_READY", noise=0.12, mode=entangled
 ▼
[Quantum Sender]     → encodes message into quantum signal
 │
 ▼
[Quantum Channel]    → adds realistic noise/interference
 │
 ▼
[Translation Layer]  → converts fuzzy result into clean contract
 │
 ▼
[Classical Receiver] → reads contract, sends ACK
 │
 ▼
ACK:OK:NODE_READY
```
