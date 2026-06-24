# Provenance Verification APIs

## Overview

The `provenance_api.py` module defines deterministic functions to verify execution certificates, lineage, and runtime semantics.

## Core APIs

All functions must remain completely deterministic and not rely on side-effects or asynchronous states.

### `verify_execution(record: ExecutionRecord) -> bool`
Verifies that the `execution_hash` is correctly derived from the record's base attributes.

### `verify_provenance(record: ExecutionRecord, trusted_identities: set) -> bool`
Validates that the producer, runtime, and governance identities are within the allowed trusted sets.

### `verify_lineage(record: ExecutionRecord, ledger: EvidenceLedger) -> bool`
Checks that the `previous_execution_hash` perfectly matches the `EvidenceLedger`'s sequence history.

### `verify_runtime(record: ExecutionRecord, expected_runtime_hash: str) -> bool`
Verifies that the `runtime_hash` matches the independently recalculated path hash.

### `execution_history(ledger: EvidenceLedger, trace_id: str) -> List[ExecutionRecord]`
Extracts the sequence of records corresponding to a single computational `trace_id`.

### `execution_graph(ledger: EvidenceLedger) -> List[Tuple[str, str]]`
Returns a directed graph of `(parent_execution_id, child_execution_id)` for the deterministic lineage of all executions.

### `execution_certificate(record: ExecutionRecord, ledger: EvidenceLedger) -> Dict[str, Any]`
Generates a portable, verifiable certificate mapping a record to its Merkle proof and ledger chain hash.
