# How a Message Travels Through the System

## The Journey of "NODE_READY"

---

### Step 1 — You Provide Three Things
- The **message**: `NODE_READY`
- Channel **noise level**: `0.12` (12% interference)
- **Transmission mode**: `entangled`

---

### Step 2 — Quantum Encoding
The message is converted to a 2-bit code using **superdense coding** — a real quantum physics technique that encodes 2 bits of information using 1 qubit.

The circuit runs 1,024 times through a simulated noisy channel.

**Output — a probability distribution (actual live values):**
```
{ "11": 697, "10": 162, "01": 86, "00": 79 }
```
"11" won 697 out of 1,024 shots. That is the dominant outcome.

---

### Step 3 — Uncertainty Classification

Before any contract is formed, the distribution is explicitly classified:

```
dominant outcome  : "11"
confidence        : 697 / 1024 = 0.6807
noise_factor      : 0.12
uncertainty class : LOW_CONFIDENCE
posture           : PROCEED_WITH_CAUTION
```

This is the hard boundary. Quantum probabilistic behaviour stops here. The downstream layers never see raw counts or probabilities — only the classified envelope.

---

### Step 4 — Translation
The dominant bitstring is verified against what was expected for "NODE_READY". If it matches and confidence is above the floor, a Classical Contract is formed:

```json
{
  "trace_id":            "c987207f-a809-54e9-b64b-e7940c28f291",
  "confidence":          0.6807,
  "decoded_message":     "NODE_READY",
  "transmission_status": "DEGRADED",
  "uncertainty_score":   0.3193,
  "contract_version":    "1.0.0"
}
```

No raw probabilities. No quantum counts. A deterministic, structured decision.

---

### Step 5 — Operational Posture
The contract is evaluated against current context (noise level, replay registry, rate limits):

```
outcome      : DEGRADED
emit_action  : True  (participation allowed, warning lineage attached)
justification: Confidence 0.6807 in [0.40, 0.70). Participation allowed with warning lineage.
```

This posture is **advisory**. It tells the caller what is safe. The caller decides whether to act. The system never acts autonomously.

---

### Step 6 — ACK
```
ACK:DEGRADED:NODE_READY:confidence=0.6807
```

The pipeline is complete. The quantum layer stayed probabilistic. The classical layer received a deterministic, auditable result.

---

### The Full Picture (Core Pipeline)

```
You
 │
 │  "NODE_READY", noise=0.12, mode=entangled
 ▼
[Quantum Producer]       → encodes message, runs 1024 shots
 │  { "11": 697, "10": 162, "01": 86, "00": 79 }
 ▼
[Uncertainty Classifier] → LOW_CONFIDENCE (confidence=0.6807)
 │  UncertaintyEnvelope  [BOUNDARY — quantum stops here]
 ▼
[Translation Layer]      → ClassicalContract (status=DEGRADED)
 │  no raw probabilities downstream
 ▼
[Degraded Runtime]       → OperationalPosture (DEGRADED, emit=True)
 │  advisory recommendation, not a command
 ▼
ACK:DEGRADED:NODE_READY:confidence=0.6807
```

---

## The Communication Layer Path (new)

The system also supports a producer-agnostic communication path. Any producer type — QUANTUM, CLASSICAL, or HYBRID — enters as a `CommunicationRequest` and exits as a `CommunicationResponse`. The gateway does not branch on source type.

```
QuantumProducer / ClassicalProducer / HybridProducer
 │
 │  CommunicationRequest
 │  { message_id, source_type, destination_type, payload, confidence }
 ▼
[CommunicationGateway.send()]
 │  rate limit check
 │  resolve_translation_status(confidence)  → OK / DEGRADED / REJECTED
 ▼
[TranslationContract]
 │  payload_hash (SHA-256), confidence, uncertainty, translation_status
 ▼
[Receiver.receive()]
 │  replay check (message_id registry, bounded at 100,000)
 ▼
[AcknowledgementContract]
 │  transport_status: ACK:OK / ACK:DEGRADED:confidence=X / HALT:*
 ▼
[CommunicationResponse]
 │  bundles TranslationContract + AcknowledgementContract
 ▼
Caller
```

All 4 cross-system paths use this identical flow:
- Quantum → Classical
- Classical → Quantum
- Hybrid → Classical
- Hybrid → Quantum

---

### What Happens When Things Go Wrong

| Situation | What Happens |
|-----------|-------------|
| Too much noise (confidence < 0.40) | `HALT:TRANSLATION_FAILURE` |
| Near-uniform distribution (confidence < 0.30) | `HALT:TRANSLATION_FAILURE` — classified as UNTRANSLATABLE first |
| Message bits don't match original | `HALT:TRANSLATION_FAILURE` — REJECT |
| Same trace_id sent twice | `HALT:REPLAY_DETECTED` |
| Same message_id sent twice (comm layer) | `HALT:REPLAY_DETECTED` |
| Too many requests per minute | `HALT:RATE_LIMIT_EXCEEDED` |
| Confidence below rejection floor (comm layer) | `HALT:TRANSLATION_REJECTED:confidence=X` |

The system **never crashes**. Every path returns a structured, observable string.
