from quantum_problem_compiler import ProblemCompiler
from qubo_translation import QUBOTranslator

def run_test():
    print("--- Starting Quantum Optimization Compiler Test ---\n")

    # 1. Initialize Compiler
    compiler = ProblemCompiler("Emergency_Response_Allocation")

    # 2. Add Variables (Binary assignment of Teams to Zones)
    # Team A and Team B, Zone 1 and Zone 2
    x_a1 = compiler.add_variable("teamA_zone1")
    x_a2 = compiler.add_variable("teamA_zone2")
    x_b1 = compiler.add_variable("teamB_zone1")
    x_b2 = compiler.add_variable("teamB_zone2")

    # 3. Add Constraints
    # Constraint 1: Team A can only be in one zone (x_a1 + x_a2 == 1)
    compiler.add_constraint("TeamA_Exclusivity", {"teamA_zone1": 1.0, "teamA_zone2": 1.0}, "==", 1.0)
    
    # Constraint 2: Team B can only be in one zone (x_b1 + x_b2 == 1)
    compiler.add_constraint("TeamB_Exclusivity", {"teamB_zone1": 1.0, "teamB_zone2": 1.0}, "==", 1.0)

    # 4. Set Objective (Minimize distance/cost)
    # Let's say Zone 1 is critical and Team A is closer to Zone 1.
    objective_linear = {
        "teamA_zone1": 10.0,
        "teamA_zone2": 50.0,
        "teamB_zone1": 40.0,
        "teamB_zone2": 15.0
    }
    compiler.set_objective(linear_terms=objective_linear, sense="minimize")

    # 5. Compile Problem
    problem = compiler.compile()
    print("Compiled Problem Summary:")
    print(problem.export_summary())

    # 6. Translate to QUBO
    translator = QUBOTranslator(problem)
    qubo_matrix = translator.translate(constraint_weight=100.0)

    print("\n--- Generated QUBO Matrix ---")
    print(f"Global Offset (Constant): {translator.offset}")
    for term, coeff in qubo_matrix.items():
        print(f"{term}: {coeff}")

if __name__ == "__main__":
    run_test() 
