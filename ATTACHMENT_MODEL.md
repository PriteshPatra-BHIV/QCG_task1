# ATTACHMENT_MODEL.md

> Capability Registry Foundation — Phase 4
> Single source of truth for capability attachment patterns in BHIV systems.

---

## What is an Attachment Model?

Capabilities exist independently of the products that use them. An **attachment model** defines how a consumer integrates, invokes, and interacts with a given capability. 

The capability registry explicitly requires declaring the `attachment_type` in `attachment_rules`.

---

## 1. Embedded (`embedded`)

The capability is compiled or imported directly into the consumer's execution process. It shares memory space, runtime environment, and thread management with the consumer.

* **Typical Use:** High-performance, synchronous utilities (e.g., cryptographic hashing, pure deterministic validation).
* **Protocol:** `in_process`, `import`.
* **Pros:** Zero network latency, strict determinism.
* **Cons:** Must share the same programming language/environment; a crash in the capability crashes the consumer.

---

## 2. API-Linked (`api_linked`)

The capability is hosted as a remote service. The consumer invokes it over a network boundary using standard RPC or REST protocols.

* **Typical Use:** Shared central services (e.g., identity verification, global state lookup).
* **Protocol:** `http_rest`, `grpc`.
* **Pros:** Language-agnostic, independently scalable, no shared memory.
* **Cons:** Introduces network latency, requires failure-handling logic (retries, timeouts).

---

## 3. Sidecar (`sidecar`)

The capability runs as a separate but co-located process on the same host or pod as the consumer. Communication is local but strictly partitioned by OS boundaries.

* **Typical Use:** Local proxies, telemetry agents, local policy enforcers.
* **Protocol:** Local `socket`, loopback `http_rest`.
* **Pros:** Strong process isolation, very low latency, independent crash domains.
* **Cons:** Deployment complexity (requires orchestration of multiple containers/processes per node).

---

## 4. Bounded Participant (`bounded_participant`)

The capability operates entirely asynchronously via a message bus or event queue. The consumer emits events, and the capability reacts without direct synchronous invocation.

* **Typical Use:** Audit logging, asynchronous workflow triggers, reconciliation loops.
* **Protocol:** `queue` (e.g., Kafka, RabbitMQ, multiprocessing.Queue).
* **Pros:** Complete temporal decoupling, consumer is unaffected by capability downtime.
* **Cons:** No immediate synchronous return value; eventual consistency.

---

## 5. Optional Extension (`optional_extension`)

The capability is dynamically loaded or registered at runtime only if the consumer configuration requests it. It adheres to a strict plugin interface.

* **Typical Use:** Custom dashboard widgets, specialized data format adapters, experimental features.
* **Protocol:** Dynamic library load, WebAssembly modules, runtime hooks.
* **Pros:** Highly extensible, keeps base footprint small.
* **Cons:** Complex versioning, requires strict interface compliance to prevent runtime crashes.
