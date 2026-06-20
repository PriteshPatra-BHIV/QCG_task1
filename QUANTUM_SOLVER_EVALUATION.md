# Quantum Solver Evaluation Study

This document evaluates the landscape of quantum and classical solvers for operational intelligence workloads, categorizing them by architecture, strengths, weaknesses, and operational suitability.

---

## 1. Quantum Hardware & Vendors

### D-Wave (Quantum Annealing)
*   **Strengths:** Natively solves QUBO and Ising models. Boasts the highest physical qubit counts available today (e.g., Advantage system with 5,000+ qubits). Excellent for highly constrained combinatorial optimization.
*   **Weaknesses:** Not universal (gate-based); restricted to optimization and sampling. Connectivity graphs (Pegasus/Zephyr) require complex embedding, reducing effective logical variable count. Coherence times and analog noise limit precision.
*   **Ideal Use Cases:** Routing, task assignment, workforce scheduling, partition problems.
*   **Maturity Level:** High (commercially accessible, established hybrid solvers).
*   **Operational Suitability:** Currently the most practical for pure optimization workloads in enterprise settings due to its hybrid solver suite.

### IBM Quantum (Superconducting Gate-Based)
*   **Strengths:** Universal quantum computer. Highly active community (Qiskit). Strong roadmap for logical qubits and error mitigation. Can run QAOA (Quantum Approximate Optimization Algorithm).
*   **Weaknesses:** Currently in the NISQ (Noisy Intermediate-Scale Quantum) era; gate depths are severely limited by noise. Qubit counts are lower than annealers.
*   **Ideal Use Cases:** Chemistry simulation, cryptography, highly structured optimization problems where shallow circuits suffice.
*   **Maturity Level:** Medium (rapidly evolving, deep integration).
*   **Operational Suitability:** Low for immediate large-scale optimization, but critical for long-term algorithmic development.

### IonQ & Quantinuum (Trapped Ion Gate-Based)
*   **Strengths:** All-to-all connectivity allows for denser embeddings without chain penalties. Very high fidelity and long coherence times compared to superconducting circuits.
*   **Weaknesses:** Slower gate operation times. Lower overall qubit counts.
*   **Ideal Use Cases:** High-precision QAOA, quantum machine learning, complex but small-scale combinatorial problems.
*   **Maturity Level:** Medium.
*   **Operational Suitability:** Suitable for high-value, small-to-medium optimization kernels where precision outweighs scale.

### Google Quantum AI (Superconducting Gate-Based)
*   **Strengths:** Pioneers in quantum supremacy. Excellent research into quantum error correction (surface codes) and physics simulation.
*   **Weaknesses:** Less commercial/enterprise focus on direct optimization APIs compared to IBM or D-Wave.
*   **Ideal Use Cases:** Materials science, fundamental physics, exploratory QAOA.
*   **Maturity Level:** Medium (research-heavy).
*   **Operational Suitability:** Low for near-term operational integration.

---

## 2. Classical Optimization Approaches

### Mixed Integer Programming (MIP) / OR-Tools / Gurobi
*   **Strengths:** Guarantees global optimality for linear problems. Extremely mature, robust, and highly scalable. Capable of handling continuous and integer variables natively without penalty functions.
*   **Weaknesses:** Struggles with highly non-linear, rugged fitness landscapes. Computation time scales exponentially for worst-case NP-hard problems.
*   **Ideal Use Cases:** Supply chain planning, resource allocation, blending problems.
*   **Maturity Level:** Extremely High.
*   **Operational Suitability:** The gold standard. Must be the baseline against which any quantum system is judged.

### Constraint Programming (CP)
*   **Strengths:** Excellent at navigating logical constraints ("if X then Y") and scheduling constraints.
*   **Weaknesses:** Less focused on objective maximization; more focused on feasibility. Can get stuck proving optimality.
*   **Ideal Use Cases:** Workforce scheduling, timetabling.
*   **Maturity Level:** High.
*   **Operational Suitability:** High for operational intelligence requiring strict compliance.

### Simulated Annealing & Genetic Algorithms (Heuristics)
*   **Strengths:** Excellent at finding "good enough" solutions quickly in massive, non-linear search spaces. Highly parallelizable.
*   **Weaknesses:** No guarantee of global optimality. Parameter tuning (mutation rates, cooling schedules) is an art. Can get trapped in local minima (though SA is designed to mitigate this).
*   **Ideal Use Cases:** Complex routing (VRP), multi-agent coordination.
*   **Maturity Level:** High.
*   **Operational Suitability:** Often used in tandem with MIP or as a fallback when exact solvers time out.
