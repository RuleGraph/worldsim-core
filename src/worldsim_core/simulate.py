from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from .models import World, LawCard
from .invariants import audit_invariants, rel_drift
from .solvers import VerletNBodySolver

@dataclass
class RunResult:
    steps: int
    dt_seconds: float
    final_state: dict
    initial_invariants: dict
    final_invariants: dict
    drifts: Dict[str, float]

class SolverRegistry:
    def __init__(self):
        self._by_law: Dict[str, object] = {}

    def register(self, law_id: str, solver: object):
        self._by_law[law_id] = solver

    def get(self, law_id: str) -> object:
        if law_id not in self._by_law:
            raise KeyError(f"No solver registered for law '{law_id}'")
        return self._by_law[law_id]

DEFAULT_REGISTRY = SolverRegistry()
DEFAULT_REGISTRY.register("rg:law/gravity.newton.v1", VerletNBodySolver())

def _world_to_arrays(world: World):
    m = np.array([e.mass.value for e in world.entities], dtype=float)
    r = np.array([e.state.position.value for e in world.entities], dtype=float)
    v = np.array([e.state.velocity.value for e in world.entities], dtype=float)
    return m, r, v

def _arrays_to_world(world: World, r: np.ndarray, v: np.ndarray):
    for i, e in enumerate(world.entities):
        e.state.position.value = r[i].tolist()
        e.state.velocity.value = v[i].tolist()

def _config_dt(world: World) -> float:
    cfg = world.config or {}
    if "dtSeconds" in cfg:
        return float(cfg["dtSeconds"])
    return 60.0

def _config_steps(world: World) -> int:
    cfg = world.config or {}
    if "steps" in cfg:
        return int(cfg["steps"])
    return 0

def simulate(world: World, cards: Dict[str, LawCard], registry: Optional[SolverRegistry] = None) -> RunResult:
    registry = registry or DEFAULT_REGISTRY

    law_ref = world.dynamics[0]["ref"]
    law = cards.get(law_ref) or next((c for c in cards.values() if c.id == law_ref), None)
    if law is None:
        raise ValueError(f"LawCard '{law_ref}' not available")

    solver = registry.get(law.id)

    dt = _config_dt(world)
    steps = _config_steps(world)
    if steps <= 0:
        raise ValueError("world.config.steps must be > 0")

    m, r, v = _world_to_arrays(world)
    state = {"t": 0.0, "r": r, "v": v, "m": m}

    G = law.parameters["G"].value
    inv0 = audit_invariants(G, m, r, v)

    budgets = (law.invariants or {}).get("driftBudget", {})
    budget_energy = float(budgets.get("Energy", {}).get("rel", 1.0))
    budget_linmom = float(budgets.get("LinearMomentum", {}).get("rel", 1.0))
    budget_angmom = float(budgets.get("AngularMomentum", {}).get("rel", 1.0))

    gross_factor = 10.0

    for i in range(steps):
        state = solver.step(state, law, dt)
        if (i + 1) % 100 == 0 or i + 1 == steps:
            inv = audit_invariants(G, m, state["r"], state["v"])
            dE = rel_drift(inv["Energy"], inv0["Energy"]) if budget_energy < 1.0 else 0.0
            dP = rel_drift(inv["LinearMomentum"], inv0["LinearMomentum"]) if budget_linmom < 1.0 else 0.0
            dL = rel_drift(inv["AngularMomentum"], inv0["AngularMomentum"]) if budget_angmom < 1.0 else 0.0
            if (
                (budget_energy < 1.0 and dE > gross_factor * budget_energy) or
                (budget_linmom < 1.0 and dP > gross_factor * budget_linmom) or
                (budget_angmom < 1.0 and dL > gross_factor * budget_angmom)
            ):
                break

    invN = audit_invariants(G, m, state["r"], state["v"])
    drifts = {
        "Energy": rel_drift(invN["Energy"], inv0["Energy"]),
        "LinearMomentum": rel_drift(invN["LinearMomentum"], inv0["LinearMomentum"]),
        "AngularMomentum": rel_drift(invN["AngularMomentum"], inv0["AngularMomentum"]),
    }

    _arrays_to_world(world, state["r"], state["v"])

    return RunResult(
        steps=i + 1,
        dt_seconds=dt,
        final_state=state,
        initial_invariants=inv0,
        final_invariants=invN,
        drifts=drifts,
    )