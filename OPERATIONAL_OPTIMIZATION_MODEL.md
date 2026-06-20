# Operational Optimization Problem Framework

This document outlines seven key operational problem types, detailing how they can be transformed into optimization models suitable for future quantum and hybrid-quantum solvers.

---

## 1. Resource Allocation

### Problem Definition
Distributing limited resources (e.g., budget, compute power, human resources) across a set of tasks or departments to maximize overall utility or return on investment.

### Variables
*   $x_{ij} \in \{0, 1\}$: Binary variable indicating if resource $i$ is allocated to task $j$.

### Constraints
*   **Resource availability:** A resource can only be allocated once ($\sum_j x_{ij} \le 1$).
*   **Task requirements:** A task must receive exactly the required number of resources.

### Optimization Objective
Maximize total utility: $\max \sum_{i,j} U_{ij} x_{ij}$, where $U_{ij}$ is the utility of assigning resource $i$ to task $j$.

### Expected Outputs
A mapping matrix detailing exactly which resources are assigned to which tasks, ensuring all constraints are met while maximizing total utility.

### State Space Analysis
*   **Input Size:** $R$ resources, $T$ tasks.
*   **Constraint Count:** $R + T$
*   **Search Space Growth:** $O(2^{R \times T})$
*   **Classical Complexity:** NP-Hard (equivalent to Generalized Assignment Problem).
*   **Potential Quantum Advantage:** Quantum annealing and QAOA are well-suited for these discrete combinatorial landscapes, potentially offering polynomial speedups or better heuristics.
*   **Numerical Example:** 50 resources, 100 tasks $\rightarrow 2^{5000}$ possible states. Classically intractable for exact solutions; typically solved with heuristics.

---

## 2. Workforce Scheduling

### Problem Definition
Assigning shifts and tasks to employees over a specific time horizon while respecting labor laws, employee preferences, and operational coverage requirements.

### Variables
*   $s_{et} \in \{0, 1\}$: Binary variable indicating if employee $e$ works shift $t$.

### Constraints
*   **Coverage:** Minimum number of employees required per shift.
*   **Work rules:** Maximum consecutive shifts, minimum rest periods between shifts.
*   **Qualifications:** Employees must possess skills required for the assigned shift.

### Optimization Objective
Minimize scheduling costs (e.g., overtime) while maximizing employee preference satisfaction.

### Expected Outputs
A detailed roster assigning each employee to specific shifts over the planning horizon.

### State Space Analysis
*   **Input Size:** $E$ employees, $S$ shifts.
*   **Constraint Count:** $S + E \times (\text{rules})$
*   **Search Space Growth:** $O(2^{E \times S})$
*   **Classical Complexity:** NP-Hard.
*   **Potential Quantum Advantage:** Constraint satisfaction is a strong suit for QUBO models, allowing rapid evaluation of high-quality, valid rosters.
*   **Numerical Example:** 100 employees, 21 shifts/week $\rightarrow 2^{2100}$ states.

---

## 3. Asset Utilization

### Problem Definition
Maximizing the productive time and efficiency of physical assets (e.g., machinery, vehicles) by scheduling maintenance and operational cycles optimally.

### Variables
*   $a_{mt} \in \{0, 1\}$: Binary variable indicating if asset $m$ is active at time $t$.
*   $d_{mt} \in \{0, 1\}$: Binary variable indicating if asset $m$ is down for maintenance at time $t$.

### Constraints
*   **State Exclusivity:** An asset cannot be active and in maintenance simultaneously ($a_{mt} + d_{mt} \le 1$).
*   **Maintenance Windows:** Maintenance must occur within specified timeframes before failure probabilities become critical.

### Optimization Objective
Maximize total active asset time minus maintenance and failure penalties.

### Expected Outputs
A schedule for each asset indicating operational periods and planned maintenance downtime.

### State Space Analysis
*   **Input Size:** $A$ assets, $T$ time periods.
*   **Constraint Count:** $A \times T$
*   **Search Space Growth:** $O(3^{A \times T})$ (Active, Maintenance, Idle).
*   **Classical Complexity:** NP-Hard.
*   **Potential Quantum Advantage:** Efficiently exploring the trade-off landscape between immediate utilization and delayed maintenance risks.
*   **Numerical Example:** 20 assets, 100 time periods $\rightarrow 3^{2000}$ states.

---

## 4. Task Assignment

### Problem Definition
Matching a set of specialized tasks to a set of agents (human or machine) where agents have varying proficiencies, costs, and availability.

### Variables
*   $y_{kj} \in \{0, 1\}$: Binary variable indicating agent $k$ is assigned to task $j$.

### Constraints
*   **Exclusivity:** Each task is assigned to exactly one agent ($\sum_k y_{kj} = 1$).
*   **Capacity:** An agent cannot exceed their workload capacity.

### Optimization Objective
Minimize the total cost or time required to complete all tasks: $\min \sum_{k,j} C_{kj} y_{kj}$.

### Expected Outputs
A bipartite matching of tasks to agents.

### State Space Analysis
*   **Input Size:** $K$ agents, $J$ tasks.
*   **Constraint Count:** $J + K$
*   **Search Space Growth:** $O(K^J)$
*   **Classical Complexity:** P (if simple assignment), NP-Hard (if generalized with capacities/dependencies).
*   **Potential Quantum Advantage:** For complex, constrained versions with inter-task dependencies, quantum approaches may find global optima faster.
*   **Numerical Example:** 30 agents, 100 tasks $\rightarrow 30^{100}$ states.

---

## 5. Routing

### Problem Definition
Determining the optimal paths for a fleet of vehicles to visit a set of nodes (e.g., delivery locations) and return to the depot.

### Variables
*   $r_{uv}^v \in \{0, 1\}$: Binary variable indicating if vehicle $v$ travels directly from node $u$ to node $v$.

### Constraints
*   **Flow conservation:** If a vehicle enters a node, it must leave it.
*   **Visit requirement:** Every required node must be visited exactly once.
*   **Capacity:** The total load on a route cannot exceed vehicle capacity.

### Optimization Objective
Minimize total distance or travel time across all routes.

### Expected Outputs
A set of ordered sequences (routes) of nodes for each vehicle.

### State Space Analysis
*   **Input Size:** $V$ vehicles, $N$ nodes.
*   **Constraint Count:** $O(N + V)$
*   **Search Space Growth:** $O(N!)$
*   **Classical Complexity:** NP-Hard (Vehicle Routing Problem).
*   **Potential Quantum Advantage:** Quantum algorithms (like QAOA applied to TSP/VRP variants) offer potential speedups in escaping local minima in highly complex routing topologies.
*   **Numerical Example:** 50 nodes, 5 vehicles $\rightarrow \approx 50!$ routing combinations.

---

## 6. Supply Chain Planning

### Problem Definition
Optimizing the flow of goods from suppliers through manufacturing to distributors, balancing inventory costs, production costs, and transportation costs.

### Variables
*   $q_{fpt} \ge 0$: Continuous/Integer quantity of product $p$ flowing through facility $f$ at time $t$. (Often discretized for QUBO).

### Constraints
*   **Inventory balance:** Current inventory = Previous + Inflow - Outflow.
*   **Capacity:** Production and storage capacities cannot be exceeded.
*   **Demand satisfaction:** All customer demand must be met.

### Optimization Objective
Minimize the total cost of production, holding inventory, and transportation.

### Expected Outputs
A production and distribution plan specifying quantities to produce, store, and ship across the network over time.

### State Space Analysis
*   **Input Size:** $F$ facilities, $P$ products, $T$ time periods.
*   **Constraint Count:** $O(F \times P \times T)$
*   **Search Space Growth:** Exponential with respect to discretization levels.
*   **Classical Complexity:** NP-Hard (when including fixed costs and integer constraints).
*   **Potential Quantum Advantage:** Solving large-scale Mixed Integer Programs (MIPs) by converting discrete decisions into QUBOs.
*   **Numerical Example:** 10 facilities, 100 products, 12 time periods with binary selection variables $\rightarrow O(2^{12000})$.

---

## 7. Multi-Agent Coordination

### Problem Definition
Coordinating the actions of multiple autonomous agents to achieve a common goal without conflicting, such as drone swarm routing or automated guided vehicles (AGVs) on a warehouse floor.

### Variables
*   $p_{ait} \in \{0, 1\}$: Binary variable indicating if agent $a$ is at position $i$ at time $t$.

### Constraints
*   **Collision Avoidance:** Two agents cannot occupy the same position at the same time ($\sum_a p_{ait} \le 1$).
*   **Kinematics:** Agents can only move to adjacent valid positions between time $t$ and $t+1$.

### Optimization Objective
Minimize the total time (makespan) required for all agents to reach their destinations.

### Expected Outputs
A conflict-free path (sequence of positions over time) for every agent.

### State Space Analysis
*   **Input Size:** $A$ agents, $L$ locations, $T$ time steps.
*   **Constraint Count:** $L \times T + A \times T$
*   **Search Space Growth:** $O(L^{A \times T})$
*   **Classical Complexity:** NP-Hard (Multi-Agent Pathfinding).
*   **Potential Quantum Advantage:** Finding conflict-free schedules in dense environments where classical planners suffer from exponential back-tracking.
*   **Numerical Example:** 20 agents, 100 locations, 50 time steps $\rightarrow 100^{1000}$ possible state trajectories.
