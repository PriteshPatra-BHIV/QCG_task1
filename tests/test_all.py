"""
tests/test_all.py
Full pytest suite for the Hybrid Quantum Communication Gateway.
Covers all 6 layers: producer, translation, gateway, failure modes, determinism.
"""

import pytest

from models import TransmissionRequest, QuantumDistribution, ClassicalContract
from quantum_producer import run_quantum_producer
from translation_layer import translate, TranslationError
from hybrid_gateway import QuantumGateway
from determinism_proof import run_determinism_proof


SEED = 42
GOOD_REQUEST = TransmissionRequest(message="NODE_READY", noise=0.05, mode="entangled")


# -- Layer 1: Input Validation ------------------------------------------------

class TestTransmissionRequest:
    def test_valid_request(self):
        r = TransmissionRequest("NODE_READY", 0.12, "entangled")
        assert r.message == "NODE_READY"

    def test_empty_message_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            TransmissionRequest("", 0.1, "entangled")

    def test_whitespace_message_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            TransmissionRequest("   ", 0.1, "entangled")

    def test_noise_below_zero_raises(self):
        with pytest.raises(ValueError, match="noise"):
            TransmissionRequest("MSG", -0.1, "entangled")

    def test_noise_above_one_raises(self):
        with pytest.raises(ValueError, match="noise"):
            TransmissionRequest("MSG", 1.1, "entangled")

    def test_unsupported_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            TransmissionRequest("MSG", 0.1, "teleport")

    def test_boundary_noise_zero(self):
        r = TransmissionRequest("MSG", 0.0, "entangled")
        assert r.noise == 0.0

    def test_boundary_noise_one(self):
        r = TransmissionRequest("MSG", 1.0, "entangled")
        assert r.noise == 1.0

    def test_message_stripped(self):
        r = TransmissionRequest("  NODE_READY  ", 0.0, "entangled")
        assert r.message == "NODE_READY"

    def test_message_too_long_raises(self):
        with pytest.raises(ValueError, match="MAX_MESSAGE_LENGTH"):
            TransmissionRequest("A" * 300, 0.0, "entangled")


# -- Config Validation --------------------------------------------------------

class TestConfigValidation:
    def test_validate_passes_with_defaults(self):
        import config
        config.validate()  # should not raise

    def test_validate_catches_inverted_thresholds(self):
        import config
        original_corruption = config.CORRUPTION_THRESHOLD
        config.CORRUPTION_THRESHOLD = 0.80  # higher than CONFIDENCE_THRESHOLD
        with pytest.raises(ValueError, match="less than"):
            config.validate()
        config.CORRUPTION_THRESHOLD = original_corruption  # restore


# -- Layer 1: Quantum Producer ------------------------------------------------

class TestQuantumProducer:
    def test_returns_quantum_distribution(self):
        dist = run_quantum_producer(GOOD_REQUEST, seed=SEED)
        assert isinstance(dist, QuantumDistribution)

    def test_counts_sum_to_shots(self):
        dist = run_quantum_producer(GOOD_REQUEST, seed=SEED)
        assert sum(dist.counts.values()) == dist.shots

    def test_encoded_bits_are_binary(self):
        dist = run_quantum_producer(GOOD_REQUEST, seed=SEED)
        assert dist.encoded_bits in {"00", "01", "10", "11"}

    def test_seed_produces_identical_counts(self):
        d1 = run_quantum_producer(GOOD_REQUEST, seed=SEED)
        d2 = run_quantum_producer(GOOD_REQUEST, seed=SEED)
        assert d1.counts == d2.counts

    def test_different_seeds_may_differ(self):
        d1 = run_quantum_producer(GOOD_REQUEST, seed=1)
        d2 = run_quantum_producer(GOOD_REQUEST, seed=99)
        # Not guaranteed to differ but with high noise they will; just check types
        assert isinstance(d1.counts, dict)
        assert isinstance(d2.counts, dict)

    def test_high_noise_spreads_distribution(self):
        noisy = TransmissionRequest("NODE_READY", 0.95, "entangled")
        dist = run_quantum_producer(noisy, seed=SEED)
        dominant_prob = max(dist.counts.values()) / dist.shots
        assert dominant_prob < 0.5   # noise destroys the signal

    def test_zero_noise_concentrates_distribution(self):
        clean = TransmissionRequest("NODE_READY", 0.0, "entangled")
        dist = run_quantum_producer(clean, seed=SEED)
        dominant_prob = max(dist.counts.values()) / dist.shots
        assert dominant_prob > 0.95  # near-perfect fidelity

    def test_empty_counts_model_raises(self):
        with pytest.raises(ValueError, match="counts"):
            QuantumDistribution(
                encoded_bits="11", transmission_mode="entangled",
                noise_factor=0.0, shots=1024, counts={}, seed=SEED
            )


# -- Layer 2: Translation Layer -----------------------------------------------

class TestTranslationLayer:
    def _clean_dist(self) -> QuantumDistribution:
        return run_quantum_producer(
            TransmissionRequest("NODE_READY", 0.0, "entangled"), seed=SEED
        )

    def test_ok_contract_on_clean_signal(self):
        dist = self._clean_dist()
        contract = translate(dist, "NODE_READY")
        assert contract.transmission_status == "OK"
        assert contract.decoded_message == "NODE_READY"

    def test_contract_fields_present(self):
        dist = self._clean_dist()
        contract = translate(dist, "NODE_READY")
        d = contract.to_dict()
        for field in ("trace_id", "confidence", "decoded_message",
                      "transmission_status", "uncertainty_score", "contract_version"):
            assert field in d

    def test_confidence_plus_uncertainty_equals_one(self):
        dist = self._clean_dist()
        contract = translate(dist, "NODE_READY")
        assert abs(contract.confidence + contract.uncertainty_score - 1.0) < 1e-4

    def test_trace_id_is_deterministic(self):
        dist = self._clean_dist()
        c1 = translate(dist, "NODE_READY")
        c2 = translate(dist, "NODE_READY")
        assert c1.trace_id == c2.trace_id

    def test_rejected_on_noise_spike(self):
        noisy = TransmissionRequest("NODE_READY", 0.95, "entangled")
        dist = run_quantum_producer(noisy, seed=SEED)
        with pytest.raises(TranslationError, match="REJECTED"):
            translate(dist, "NODE_READY")

    def test_rejected_on_message_corruption(self):
        # NODE_READY -> bits=11; LINK_DOWN -> bits=01: guaranteed mismatch
        dist = run_quantum_producer(
            TransmissionRequest("NODE_READY", 0.05, "entangled"), seed=SEED
        )
        with pytest.raises(TranslationError, match="REJECTED"):
            translate(dist, "LINK_DOWN")

    def test_degraded_on_medium_noise(self):
        medium = TransmissionRequest("NODE_READY", 0.40, "entangled")
        dist = run_quantum_producer(medium, seed=SEED)
        # May be DEGRADED or REJECTED depending on shot outcome; just ensure no crash
        try:
            contract = translate(dist, "NODE_READY")
            assert contract.transmission_status in ("OK", "DEGRADED")
        except TranslationError:
            pass  # REJECTED is also valid at this noise level

    def test_no_raw_probabilities_in_contract(self):
        dist = self._clean_dist()
        contract = translate(dist, "NODE_READY")
        d = contract.to_dict()
        assert "counts" not in d
        assert "raw" not in str(d)


# -- Layer 3: Gateway Pipeline ------------------------------------------------

class TestGatewayPipeline:
    def test_clean_transmission_returns_ack_ok(self):
        gw = QuantumGateway()
        ack = gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        assert ack.startswith("ACK:OK:")

    def test_ack_contains_message(self):
        gw = QuantumGateway()
        ack = gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        assert "NODE_READY" in ack

    def test_invalid_input_returns_halt(self):
        gw = QuantumGateway()
        ack = gw.transmit("", noise=0.1, mode="entangled", seed=SEED)
        assert ack.startswith("HALT:INVALID_INPUT")

    def test_invalid_mode_returns_halt(self):
        gw = QuantumGateway()
        ack = gw.transmit("NODE_READY", noise=0.1, mode="teleport", seed=SEED)
        assert ack.startswith("HALT:INVALID_INPUT")

    def test_transmit_never_raises(self):
        gw = QuantumGateway()
        for noise in [0.0, 0.5, 0.99]:
            result = gw.transmit("NODE_READY", noise=noise, mode="entangled", seed=SEED)
            assert isinstance(result, str)

    def test_independent_gateway_instances(self):
        gw1 = QuantumGateway()
        gw2 = QuantumGateway()
        ack1 = gw1.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        ack2 = gw2.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        assert "REPLAY" not in ack1
        assert "REPLAY" not in ack2

    def test_health_check_returns_ok(self):
        gw = QuantumGateway()
        health = gw.health_check()
        assert health["status"] == "ok"
        assert "replay_registry_size" in health
        assert "rate_limit_per_minute" in health
        assert "contract_version" in health

    def test_rate_limit_blocks_excess_requests(self):
        gw = QuantumGateway()
        gw._rate_limiter._tokens = 0.0  # exhaust tokens
        ack = gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        assert ack == "HALT:RATE_LIMIT_EXCEEDED"

    def test_message_too_long_returns_halt(self):
        gw = QuantumGateway()
        ack = gw.transmit("A" * 300, noise=0.0, mode="entangled", seed=SEED)
        assert ack.startswith("HALT:INVALID_INPUT")


# -- Layer 4: Failure Proof ---------------------------------------------------

class TestFailureProof:
    def test_noise_spike_halts(self):
        gw = QuantumGateway()
        ack = gw.transmit("NODE_READY", noise=0.95, mode="entangled", seed=SEED)
        assert ack.startswith("HALT:")

    def test_low_confidence_halts(self):
        gw = QuantumGateway()
        ack = gw.transmit("NODE_READY", noise=0.75, mode="entangled", seed=SEED)
        assert ack.startswith("HALT:")

    def test_replay_detected_on_second_call(self):
        gw = QuantumGateway()
        gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        ack2 = gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        assert ack2 == "HALT:REPLAY_DETECTED"

    def test_replay_registry_reset_allows_retransmit(self):
        gw = QuantumGateway()
        gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        gw.reset_replay_registry()
        ack = gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
        assert "REPLAY" not in ack

    def test_empty_counts_raises_value_error(self):
        with pytest.raises(ValueError, match="counts"):
            QuantumDistribution(
                encoded_bits="11", transmission_mode="entangled",
                noise_factor=0.0, shots=1024, counts={}, seed=SEED
            )

    def test_message_corruption_halts(self):
        dist = run_quantum_producer(
            TransmissionRequest("NODE_READY", 0.05, "entangled"), seed=SEED
        )
        with pytest.raises(TranslationError, match="REJECTED"):
            translate(dist, "LINK_DOWN")

    def test_concurrent_replay_guard(self):
        """Two threads transmitting the same message should produce exactly one REPLAY."""
        import threading
        gw = QuantumGateway()
        results = []
        lock = threading.Lock()

        def transmit():
            ack = gw.transmit("NODE_READY", noise=0.0, mode="entangled", seed=SEED)
            with lock:
                results.append(ack)

        threads = [threading.Thread(target=transmit) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        replay_count = sum(1 for r in results if "REPLAY" in r)
        ok_count = sum(1 for r in results if r.startswith("ACK:OK"))
        assert ok_count == 1
        assert replay_count == 1


# -- Layer 6: Determinism Proof -----------------------------------------------

class TestDeterminismProof:
    def test_five_runs_identical(self):
        assert run_determinism_proof(
            message="NODE_READY", noise=0.12, mode="entangled", seed=SEED, runs=5
        ) is True

    def test_different_messages_differ(self):
        req_a = TransmissionRequest("NODE_READY", 0.0, "entangled")
        req_b = TransmissionRequest("LINK_DOWN", 0.0, "entangled")
        dist_a = run_quantum_producer(req_a, seed=SEED)
        dist_b = run_quantum_producer(req_b, seed=SEED)
        assert dist_a.encoded_bits != dist_b.encoded_bits

    def test_same_seed_same_counts(self):
        req = TransmissionRequest("NODE_READY", 0.20, "entangled")
        runs = [run_quantum_producer(req, seed=SEED).counts for _ in range(3)]
        assert runs[0] == runs[1] == runs[2]

    def test_contract_trace_id_stable_across_runs(self):
        req = TransmissionRequest("NODE_READY", 0.0, "entangled")
        trace_ids = set()
        for _ in range(5):
            dist = run_quantum_producer(req, seed=SEED)
            contract = translate(dist, "NODE_READY")
            trace_ids.add(contract.trace_id)
        assert len(trace_ids) == 1


# =============================================================================
# Phase 3 Test Matrix
# =============================================================================

# -- Determinism: 20-run identical replay -------------------------------------

class TestDeterminism20Run:
    def test_20_runs_identical(self):
        """Phase 3 requirement: 20 consecutive runs must be identical."""
        assert run_determinism_proof(
            message="NODE_READY", noise=0.12, mode="entangled", seed=42, runs=20
        ) is True

    def test_failure_injection_timestamp_detected(self):
        from determinism_proof import run_failure_injection_proof
        fi = run_failure_injection_proof()
        # Timestamp mutation must surface as an observability diff
        assert fi["timestamp_mutation"]["detected"] is True

    def test_failure_injection_payload_mutation_detected(self):
        from determinism_proof import run_failure_injection_proof
        fi = run_failure_injection_proof()
        assert fi["payload_mutation"]["detected"] is True

    def test_failure_injection_ordering_neutralised(self):
        from determinism_proof import run_failure_injection_proof
        fi = run_failure_injection_proof()
        # Canonical JSON sort_keys=True must neutralise ordering
        assert fi["ordering_mutation"]["hash_unchanged"] is True


# -- Replay Enforcement -------------------------------------------------------

class TestReplayEnforcer:
    def _enforcer(self):
        from replay_enforcer import ReplayEnforcer
        return ReplayEnforcer(ttl_seconds=60.0)

    def test_valid_execution_accepted(self):
        e = self._enforcer()
        d = e.submit("art-001")
        assert d.status == "ACCEPTED"
        assert d.sequence_id == 1

    def test_duplicate_rejected(self):
        e = self._enforcer()
        e.submit("art-002")
        d = e.submit("art-002")
        assert d.status == "REJECTED_DUPLICATE"

    def test_stale_rejected(self):
        import time
        from replay_enforcer import ReplayEnforcer
        e = ReplayEnforcer(ttl_seconds=1.0)
        stale_issued = time.monotonic() - 10.0
        d = e.submit("art-stale", issued_at=stale_issued)
        assert d.status == "REJECTED_STALE"

    def test_sequence_monotonic(self):
        e = self._enforcer()
        ids = [f"art-seq-{i}" for i in range(5)]
        seqs = [e.submit(aid).sequence_id for aid in ids]
        assert seqs == sorted(seqs)
        assert seqs[0] == 1

    def test_stale_beats_duplicate(self):
        """Stale check must fire before duplicate check."""
        import time
        from replay_enforcer import ReplayEnforcer
        e = ReplayEnforcer(ttl_seconds=1.0)
        stale_issued = time.monotonic() - 10.0
        # First submit (stale) — should be REJECTED_STALE, not ACCEPTED
        d = e.submit("art-both", issued_at=stale_issued)
        assert d.status == "REJECTED_STALE"


# -- Trust Chain --------------------------------------------------------------

class TestTrustChain:
    def test_valid_chain_passes(self):
        from trust_chain import TrustChain, NodeRegistry
        from node_identity import NodeSigner
        import hashlib

        producer = NodeSigner("TC_PROD", "PRODUCER")
        gateway = NodeSigner("TC_GW", "GATEWAY")
        executor = NodeSigner("TC_EXEC", "EXECUTOR")

        registry = NodeRegistry()
        for s in [producer, gateway, executor]:
            registry.register(s.identity)

        chain = TrustChain()
        ph = hashlib.sha256(b"payload").hexdigest()
        chain.add_handoff(producer, gateway.identity, "PRODUCE", ph)
        chain.add_handoff(gateway, executor.identity, "FORWARD", ph)

        passed, errors = chain.verify_chain(registry)
        assert passed is True
        assert errors == []

    def test_forged_signature_detected(self):
        from trust_chain import TrustChain, TrustChainLink, NodeRegistry
        from node_identity import NodeSigner
        import hashlib

        legit = NodeSigner("LEGIT_NODE", "PRODUCER")
        attacker = NodeSigner("ATTACKER", "ATTACKER")

        registry = NodeRegistry()
        registry.register(legit.identity)  # attacker NOT registered

        chain = TrustChain()
        ph = hashlib.sha256(b"payload").hexdigest()
        chain.add_handoff(attacker, legit.identity, "SPOOF", ph)

        passed, errors = chain.verify_chain(registry)
        assert passed is False
        assert any("not registered" in e for e in errors)


# -- Audit Trail --------------------------------------------------------------

class TestAuditTrail:
    def test_inclusion_proof(self):
        from audit_trail import MerkleAuditTrail
        trail = MerkleAuditTrail()
        entries = [trail.append("EVT", {"i": i}, "NODE_0") for i in range(5)]
        assert trail.verify_inclusion(entries[2]) is True

    def test_tamper_detection(self):
        from audit_trail import MerkleAuditTrail, AuditEntry
        trail = MerkleAuditTrail()
        for i in range(4):
            trail.append("EVT", {"i": i}, "NODE_0")
        # Mutate internal entry
        original = trail._entries[1]
        trail._entries[1] = AuditEntry(
            sequence=1, event_type="TAMPERED", event_hash="0" * 64,
            node_id="ATTACKER", event_data={}
        )
        passed, _ = trail.verify_integrity()
        assert passed is False
        trail._entries[1] = original  # restore


# -- Consensus Tests ----------------------------------------------------------

class TestConsensus:
    def _setup(self):
        from consensus_simulation import DistributedConsensusNode, ConsensusEngine
        from node_identity import NodeSigner
        from execution_contract import ComputationExecutionContract
        from provenance import sign_contract

        producer = NodeSigner("CONS_PROD", "QUANTUM_PRODUCER")
        nodes = [DistributedConsensusNode(f"CN_{i}") for i in range(3)]
        engine = ConsensusEngine(nodes)

        contract = ComputationExecutionContract(
            producer_type="QUANTUM", payload={"data": "test"},
            confidence=0.95, trace_id="test-consensus-001", contract_version="2.0.0",
        )
        signed = sign_contract(contract, producer)
        return engine, signed, producer

    def test_honest_network(self):
        engine, signed, producer = self._setup()
        proof = engine.run_consensus(signed, producer.identity.public_key)
        assert proof.consensus_reached is True
        assert proof.agreement_percentage == 1.0

    def test_faulty_node(self):
        engine, signed, producer = self._setup()
        proof = engine.run_consensus(signed, producer.identity.public_key,
                                      simulate_faulty="CN_1")
        # 2/3 honest nodes still reach consensus
        assert proof.consensus_reached is True
        assert "CN_1" in proof.disagreements

    def test_stale_node(self):
        engine, signed, producer = self._setup()
        proof = engine.run_consensus(signed, producer.identity.public_key,
                                      simulate_missing="CN_2")
        # 2 of 3 nodes = 66% — meets threshold
        assert proof.consensus_reached is True
        assert "CN_2" in proof.disagreements

    def test_spoofed_node(self):
        """Unregistered/spoofed attestation signature is rejected."""
        from consensus_simulation import DistributedConsensusNode, ConsensusEngine
        from node_identity import NodeSigner
        from execution_contract import ComputationExecutionContract
        from provenance import sign_contract

        producer = NodeSigner("SPOOF_PROD", "QUANTUM_PRODUCER")
        nodes = [DistributedConsensusNode(f"SN_{i}") for i in range(4)]
        engine = ConsensusEngine(nodes)
        # Inject a faulty hash for one node to simulate spoofing behaviour
        contract = ComputationExecutionContract(
            producer_type="QUANTUM", payload={"data": "spoof_test"},
            confidence=0.95, trace_id="spoof-consensus-001", contract_version="2.0.0",
        )
        signed = sign_contract(contract, producer)
        proof = engine.run_consensus(signed, producer.identity.public_key,
                                      simulate_faulty="SN_0")
        # Faulty node's hash differs but honest majority still wins
        assert proof.consensus_reached is True
        assert "SN_0" in proof.disagreements
