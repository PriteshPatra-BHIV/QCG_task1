# Execution Ledger Specification

## Overview

The Deterministic Evidence Ledger provides an immutable and cryptographically sound mechanism to chain `ExecutionRecord`s.

> **IMPORTANT:** This is an execution evidence ledger. It is **NOT** a blockchain. It does not perform consensus or distributed block formation.

## Deterministic Chain

Every execution must follow the rigorous evidence chain:

1. **Execution**: The computation completes.
2. **Evidence Hash**: An execution hash is derived from the `ExecutionRecord`.
3. **Previous Hash**: The previous evidence hash is retrieved from the chain head.
4. **Execution Chain**: A new hash is produced `H(Previous Hash + Evidence Hash)`.
5. **Merkle Root**: A Merkle tree root is generated for all execution chain hashes.
6. **Ledger Snapshot**: A snapshot of the ledger sequence, root, and timestamp is returned.

## Ledger Snapshot

The ledger issues snapshots upon append, defined as follows:

- `sequence_length`: Total number of records.
- `merkle_root`: Root of the Merkle Tree of all evidence hashes.
- `latest_evidence_hash`: The hash of the head of the chain.
- `timestamp`: ISO-8601 UTC timestamp.
