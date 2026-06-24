# Execution Evidence Specification

## Overview

The Execution Evidence structure ensures that every computation is independently reconstructable, verifiable, and auditable. This specification defines the immutable `ExecutionRecord` schema.

## ExecutionRecord Schema

All execution records MUST be immutable and contain the following required fields:

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | string | Unique identifier for this execution evidence record. |
| `trace_id` | string | Reference to the original computation trace. |
| `replay_reference` | string | Hash binding to the replay registry lineage for duplicate detection. |
| `execution_sequence` | integer | Execution sequence number from the deterministic ledger. |
| `producer_identity` | string | Identity of the producer (Quantum/Classical). |
| `runtime_identity` | string | Identity of the RuntimeCore instance. |
| `governance_identity` | string | Identity of the governance layer providing the rules. |
| `execution_status` | string | Final state of the execution (e.g., ACK:OK, HALT:ERROR). |
| `runtime_hash` | string | Deterministic hash of the exact runtime path traversed. |
| `execution_hash` | string | Cryptographic hash of the current record. |
| `previous_execution_hash` | string | Hash of the preceding record in the evidence ledger. |
| `execution_root_hash` | string | Merkle root of the execution evidence tree up to this record. |
| `schema_version` | string | Schema version (e.g., "1.0.0"). |

## Mutability

Execution records MUST be strictly immutable. Modification of any field invalidates the cryptographic `execution_hash`.
