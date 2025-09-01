from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from .models import World, LawCard
from .invariants import audit_invariants, rel_drift
from .solvers import VerletNBodySolver
import math
from typing import Any

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
DEFAULT_REGISTRY.register("rg:law/physics.gravity.newton.v1", VerletNBodySolver())

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
    dyn = list(world.dynamics or [])
    # helpers to read Dynamic whether it's a pydantic object or a dict
    def _dyn_get(d: Any, key: str, default=None):
        return getattr(d, key, default) if not isinstance(d, dict) else d.get(key, default)
    def _dyn_ref(d: Any) -> str:
        return getattr(d, "ref") if not isinstance(d, dict) else d.get("ref")

    grav_ref = next((_dyn_ref(d) for d in dyn if _dyn_ref(d) == "rg:law/physics.gravity.newton.v1"), None)
    law_ref = grav_ref or _dyn_ref(dyn[0])
    law = cards.get(law_ref) or next((c for c in cards.values() if c.id == law_ref), None)
    solver = registry.get(law.id)

    m, r, v = _world_to_arrays(world)
    state = {"t": 0.0, "r": r, "v": v, "m": m}

    index_by_id = {e.id: i for i, e in enumerate(world.entities)}

    def _mask_from_selector(sel: Any, n: int) -> np.ndarray:
        """Return a boolean mask of bodies affected. Default = all bodies."""
        mask = np.zeros(n, dtype=bool)
        if not sel:
            mask[:] = True; return mask
        bodies = getattr(sel, "bodies", None) if not isinstance(sel, dict) else sel.get("bodies")
        if bodies:
            for bid in bodies:
                j = index_by_id.get(bid)
                if j is not None: mask[j] = True
        pairs = getattr(sel, "pairs", None) if not isinstance(sel, dict) else sel.get("pairs")
        if pairs:
            for a, b in pairs:
                ia = index_by_id.get(a); ib = index_by_id.get(b)
                if ia is not None: mask[ia] = True
                if ib is not None: mask[ib] = True
        if not mask.any(): mask[:] = True
        return mask

    def _param(d: Any, name: str, default: float) -> float:
        """Read parameter override or fall back to card value."""
        override = _dyn_get(d, "override", None) or {}
        ov = override.get(name) if isinstance(override, dict) else getattr(override, name, None)
        return float(ov) if ov is not None else float(default)

    def _external_accels(v_now: np.ndarray) -> np.ndarray:
        """Sum accelerations from non-gravity cards (drag, etc.)."""
        aext = np.zeros_like(r)
        for d in dyn:
            cref = _dyn_ref(d)
            if cref == law.id:
                continue  # gravity handled by solver
            card = cards.get(cref) or next((c for c in cards.values() if c.id == cref), None)
            if card is None:
                continue
            mask = _mask_from_selector(_dyn_get(d, "selector", None), r.shape[0])
            # Linear drag: F = -gamma * v  => a = F/m = -(gamma/m) * v
            if card.id == "rg:law/fluids.drag.linear.v1":
                gamma = _param(d, "gamma", card.parameters["gamma"].value)
                invm = (1.0 / m)[:, None]
                aext[mask] += (-(gamma) * invm[mask]) * v_now[mask]
            # Quadratic drag: F = -Cq * |v| * v  => a = -(Cq/m) * |v| * v
            elif card.id == "rg:law/fluids.drag.quadratic.v1":
                Cq = _param(d, "Cq", card.parameters["Cq"].value)
                invm = (1.0 / m)[:, None]
                speed = np.linalg.norm(v_now, axis=1)[:, None]
                aext[mask] += (-(Cq) * invm[mask]) * (speed[mask] * v_now[mask])
            # (future) other laws can be plugged here
        return aext

    def _card_by_ref(ref: str) -> LawCard | None:
        c = cards.get(ref)
        if c: return c
        return next((cc for cc in cards.values() if cc.id == ref), None)

    has_dissipative = any(
        bool((getattr(_card_by_ref(_dyn_ref(d)), "invariants", {}) or {}).get("dissipative", False))
        for d in dyn
    )

    G = law.parameters["G"].value if hasattr(law, "parameters") and "G" in law.parameters else 0.0
    inv0 = audit_invariants(G, m, r, v)

    budgets = (law.invariants or {}).get("driftBudget", {})
    budget_energy = float(budgets.get("Energy", {}).get("rel", 1.0))
    budget_linmom = float(budgets.get("LinearMomentum", {}).get("rel", 1.0))
    budget_angmom = float(budgets.get("AngularMomentum", {}).get("rel", 1.0))

    gross_factor = 10.0

    steps = _config_steps(world)
    dt = _config_dt(world)

    for i in range(steps):
        # gravity accelerations (positions only)
        a_g = solver.accelerations(state, law)
        # external (e.g., drag) — use current velocity
        a_e = _external_accels(state["v"])
        a1 = a_g + a_e
        v_half = state["v"] + 0.5 * dt * a1
        r_new = state["r"] + dt * v_half
        # recompute gravity on new positions
        a_g2 = solver.accelerations({"r": r_new, "m": state["m"]}, law)
        # approx external at half-step velocity
        a_e2 = _external_accels(v_half)
        v_new = v_half + 0.5 * dt * (a_g2 + a_e2)
        state = {"t": state["t"] + dt, "r": r_new, "v": v_new, "m": state["m"]}

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

    _arrays_to_world(world, state["r"], state["v"])

    return RunResult(
        steps=i + 1,
        dt_seconds=dt,
        final_state=state,
        initial_invariants=inv0,
        final_invariants=invN,
        drifts={
            "Energy": rel_drift(invN["Energy"], inv0["Energy"]),
            "LinearMomentum": rel_drift(invN["LinearMomentum"], inv0["LinearMomentum"]),
            "AngularMomentum": rel_drift(invN["AngularMomentum"], inv0["AngularMomentum"]),
        },
    )