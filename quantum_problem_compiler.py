from typing import Dict, List, Any, Optional

class Variable:
    def __init__(self, name: str, var_type: str = "binary", lower_bound: float = 0.0, upper_bound: float = 1.0):
        self.name = name
        self.var_type = var_type
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def __repr__(self):
        return f"Variable({self.name}, {self.var_type})"

class Objective:
    def __init__(self, sense: str = "minimize"):
        self.sense = sense  # "minimize" or "maximize"
        self.linear_terms: Dict[str, float] = {}
        self.quadratic_terms: Dict[tuple, float] = {}

    def add_linear_term(self, var_name: str, coefficient: float):
        if var_name in self.linear_terms:
            self.linear_terms[var_name] += coefficient
        else:
            self.linear_terms[var_name] = coefficient

    def add_quadratic_term(self, var_name1: str, var_name2: str, coefficient: float):
        # Canonicalize order
        term = tuple(sorted([var_name1, var_name2]))
        if term in self.quadratic_terms:
            self.quadratic_terms[term] += coefficient
        else:
            self.quadratic_terms[term] = coefficient

class Constraint:
    def __init__(self, name: str, sense: str, rhs: float):
        self.name = name
        self.sense = sense  # "==", "<=", ">="
        self.rhs = rhs
        self.linear_terms: Dict[str, float] = {}

    def add_term(self, var_name: str, coefficient: float):
        if var_name in self.linear_terms:
            self.linear_terms[var_name] += coefficient
        else:
            self.linear_terms[var_name] = coefficient

class PenaltyFunction:
    """Represents a constraint transformed into a penalty for QUBO formulation."""
    def __init__(self, name: str, weight: float, terms: Dict[str, Any]):
        self.name = name
        self.weight = weight
        self.terms = terms

class CompiledOptimizationProblem:
    """A solver-agnostic representation of an optimization problem."""
    def __init__(self, name: str):
        self.name = name
        self.variables: Dict[str, Variable] = {}
        self.constraints: Dict[str, Constraint] = {}
        self.objective: Objective = Objective()
        self.penalties: List[PenaltyFunction] = []

    def export_summary(self) -> str:
        summary = f"Problem: {self.name}\n"
        summary += f"Variables: {len(self.variables)}\n"
        summary += f"Constraints: {len(self.constraints)}\n"
        summary += f"Objective Sense: {self.objective.sense}\n"
        return summary

class ProblemCompiler:
    """Compiles operational variables, constraints, and objectives into a solver-agnostic representation."""
    def __init__(self, name: str):
        self.problem = CompiledOptimizationProblem(name)

    def add_variable(self, name: str, var_type: str = "binary") -> Variable:
        var = Variable(name, var_type)
        self.problem.variables[name] = var
        return var

    def add_constraint(self, name: str, terms: Dict[str, float], sense: str, rhs: float):
        constraint = Constraint(name, sense, rhs)
        for var_name, coeff in terms.items():
            if var_name not in self.problem.variables:
                raise ValueError(f"Variable {var_name} not found in problem.")
            constraint.add_term(var_name, coeff)
        self.problem.constraints[name] = constraint

    def set_objective(self, linear_terms: Dict[str, float], quadratic_terms: Dict[tuple, float] = None, sense: str = "minimize"):
        self.problem.objective.sense = sense
        for var_name, coeff in linear_terms.items():
             self.problem.objective.add_linear_term(var_name, coeff)
        
        if quadratic_terms:
            for (v1, v2), coeff in quadratic_terms.items():
                self.problem.objective.add_quadratic_term(v1, v2, coeff)

    def add_penalty(self, name: str, weight: float, terms: Dict[str, Any]):
        penalty = PenaltyFunction(name, weight, terms)
        self.problem.penalties.append(penalty)

    def compile(self) -> CompiledOptimizationProblem:
        # Optimization pass or validation could happen here.
        # Currently just returns the built problem.
        return self.problem
