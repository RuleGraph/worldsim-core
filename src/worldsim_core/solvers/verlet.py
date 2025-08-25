from __future__ import annotations
import numpy as np
from typing import Dict, Any

from ..models import LawCard

class VerletNBodySolver:
    """Simple velocity-Verlet integrator for pairwise Newtonian gravity.

    State dict contract:
      {"t": float_seconds, "r": (N,3) float64, "v": (N,3) float64, "m": (N,) float64}
    """

    def __init__(self, softening: float = 0.0):
        self.softening = softening

    @staticmethod
    def _accels(G: float, m: np.ndarray, r: np.ndarray, eps2: float = 0.0) -> np.ndarray:
        # Compute accelerations a_i = sum_{j!=i} -G m_j (r_i - r_j) / (|r_i - r_j|^2 + eps2)^(3/2)
        n = r.shape[0]
        a = np.zeros_like(r)
        for i in range(n):
            dr = r[i] - r
            dist2 = np.sum(dr*dr, axis=1) + eps2
            inv_r3 = np.where(dist2 > 0, 1.0 / np.power(dist2, 1.5), 0.0)
            # exclude self i
            inv_r3[i] = 0.0
            a[i] = -G * (dr * (m * inv_r3)[:, None]).sum(axis=0)
        return a

    def step(self, state: Dict[str, Any], lawcard: LawCard, dt_seconds: float) -> Dict[str, Any]:
        r = state["r"]
        v = state["v"]
        m = state["m"]
        t = state.get("t", 0.0)
        G = lawcard.parameters["G"].value
        eps2 = self.softening**2

        a = self._accels(G, m, r, eps2)
        v_half = v + 0.5 * dt_seconds * a
        r_new = r + dt_seconds * v_half
        a_new = self._accels(G, m, r_new, eps2)
        v_new = v_half + 0.5 * dt_seconds * a_new
        return {"t": t + dt_seconds, "r": r_new, "v": v_new, "m": m}