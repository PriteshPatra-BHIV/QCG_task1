from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutionRecord:
    """
    Immutable representation of an Execution Record.
    Every computation is recorded here to be independently reconstructed, 
    verified, audited, and cryptographically proven.
    """
    execution_id: str
    trace_id: str
    replay_reference: str
    execution_sequence: int
    producer_identity: str
    runtime_identity: str
    governance_identity: str
    execution_status: str
    runtime_hash: str
    execution_hash: str
    previous_execution_hash: str
    execution_root_hash: str
    schema_version: str
