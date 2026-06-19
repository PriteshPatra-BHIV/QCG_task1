# REVIEW_PACKET.md

> Capability Registry Foundation — Phase 6
> BHIV Systems — Capability Inventory
> Owner: Kanishk
> Status: PRODUCTION READY

---

## 1. What Changed
The objective of this work was to establish a foundational, reusable Capability Registry specification for BHIV systems. Previously, capabilities were tied inextricably to product logic and team authority. This update cleanly decouples "Capability" as an independent, discoverable, scope-bounded function.

The following foundational artifacts were created:
* `CAPABILITY_MODEL.md` (Formal definition, lifecycle, distinction from product/team/authority)
* `capability_registry_schema.json` (JSON Schema governing the registry entries)
* `ATTACHMENT_MODEL.md` (Definition of how consumers attach to capabilities: embedded, api_linked, sidecar, bounded_participant, optional_extension)
* `sample_capabilities.json` (5 valid capability records populated to demonstrate the schema)

*(Note: The previous QCG REVIEW_PACKET was renamed to `REVIEW_PACKET_QCG.md` to prevent data loss while fulfilling this mandatory delivery).*

---

## 2. Core Files
- **Entry Point:** `capability_registry_schema.json`
- **Conceptual Grounding:** `CAPABILITY_MODEL.md`, `ATTACHMENT_MODEL.md`
- **Sample Population:** `sample_capabilities.json`

---

## 3. Execution Flow (Discovery & Attachment)

When a BHIV product wishes to adopt a capability, the flow is:

1. **Discovery:** The consumer queries the capability registry (e.g., searching for `SCENARIO_SIMULATION` with `ACTIVE` status).
2. **Evaluation:** The consumer reviews `authority_limits` (owns / does_not_own) to ensure it meets their needs without exceeding their own governance boundary.
3. **Attachment:** The consumer reads `attachment_rules`. If it is `api_linked`, they configure their product to invoke the capability via the specified `protocol` (e.g., `http_rest`) and `endpoint`.
4. **Invocation:** The consumer formats its request according to the `inputs` schema and expects the response defined in `outputs`.

---

## 4. JSON Samples

The 5 capability examples created in `sample_capabilities.json` include:
1. `REPLAY_ENFORCEMENT` (Replay Module - embedded)
2. `SCENARIO_SIMULATION` (Testing Module - api_linked)
3. `TELEMETRY_VISUALIZATION` (Dashboard Module - optional_extension)
4. `AUTONOMOUS_EXECUTION` (Agent Module - sidecar)
5. `STATE_ORCHESTRATION` (Workflow Module - bounded_participant)

Example configuration snippet for `REPLAY_ENFORCEMENT`:
```json
{
  "capability_id": "a1b2c3d4-e5f6-5a7b-8c9d-0e1f2a3b4c5d",
  "capability_name": "REPLAY_ENFORCEMENT",
  "status": "ACTIVE",
  "attachment_rules": {
    "attachment_type": "embedded",
    "protocol": "in_process"
  }
}
```

---

## 5. Failure Cases

The schema ensures strict structure, rejecting non-compliant capability submissions. Expected failure cases during validation include:

| Failure Mode | Reason | Rejection Signal |
|--------------|--------|------------------|
| `MISSING_OWNER` | Team or contact is missing from the record | JSON Schema Validation Error |
| `INVALID_ATTACHMENT` | `attachment_type` is not one of the 5 allowed enums | JSON Schema Validation Error |
| `AUTHORITY_BREACH` | Capability attempts to declare product logic as an input | Rejected by Governance / Registry Admin |
| `ID_FORMAT_ERROR` | `capability_id` is not a valid UUID-5 | JSON Schema Validation Error |

---

## 6. Proof
The foundational schema has been verified by validating the `sample_capabilities.json` structure against the `$schema` standard. All 5 sample modules successfully map to the schema definition, including inputs, outputs, attachment rules, and explicit authority boundaries.
