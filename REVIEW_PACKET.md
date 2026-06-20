# Quantum Optimization Framework Review Packet

This document contains the validation evidence for the BHIV Quantum Optimization Compiler framework.

## 1. Compiler Execution & QUBO Generation Evidence
The `test_compiler.py` script was executed to validate the end-to-end flow from problem definition to QUBO matrix generation for a simplified Emergency Response Allocation problem.

### Problem Setup
*   **Variables:** 4 binary variables (Team A/B assigned to Zone 1/2)
*   **Constraints:** 2 equality constraints (Each team must be in exactly one zone)
*   **Objective:** Minimize distance/cost based on linear weights.

### Execution Output
```text
--- Starting Quantum Optimization Compiler Test ---

Compiled Problem Summary:
Problem: Emergency_Response_Allocation
Variables: 4
Constraints: 2
Objective Sense: minimize

--- Generated QUBO Matrix ---
Global Offset (Constant): 200.0
('teamA_zone1', 'teamA_zone1'): -90.0
('teamA_zone2', 'teamA_zone2'): -50.0
('teamB_zone1', 'teamB_zone1'): -60.0
('teamB_zone2', 'teamB_zone2'): -85.0
('teamA_zone1', 'teamA_zone2'): 200.0
('teamB_zone1', 'teamB_zone2'): 200.0
```

### Analysis of Output
*   **Linear Penalties (Diagonal):** The individual linear terms (e.g., `teamA_zone1`) reflect both the objective function weights and the negative penalty derived from expanding the constraint $(x_1 + x_2 - 1)^2$.
*   **Quadratic Penalties (Off-Diagonal):** The highly positive cross-terms (`200.0`) between variables representing the same team in different zones strongly penalize the solver if it attempts to assign a single team to multiple zones simultaneously (violating the exclusivity constraint).

## 2. Solver Comparison & Runtime Integration Reference
All required diagrams and comparative outputs are available in the generated markdown documents:
*   [QUANTUM_SOLVER_EVALUATION.md](file:///c:/QCG/QCG_task1/QUANTUM_SOLVER_EVALUATION.md) (Solver matrices and maturity)
*   [QUANTUM_RUNTIME_INTEGRATION.md](file:///c:/QCG/QCG_task1/QUANTUM_RUNTIME_INTEGRATION.md) (Architecture diagrams for deterministic isolation)
*   [BHIV_OPERATIONAL_INTELLIGENCE_CASE_STUDY.md](file:///c:/QCG/QCG_task1/BHIV_OPERATIONAL_INTELLIGENCE_CASE_STUDY.md) (Applied hybrid scaling)
