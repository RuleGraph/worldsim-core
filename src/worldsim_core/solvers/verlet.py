from __future__ import annotations
import numpy as np
from typing import Dict, Any

from ..models import LawCard

class VerletNBodySolver:
    """
    Velocity-Verlet integrator for pairwise Newtonian gravity.

    State dict:
      {"t": float_seconds, "r": (N,3) float64, "v": (N,3) float64, "m": (N,) float64}

    Params:
      softening: Plummer-like softening length (meters). 0.0 = none.
      vectorized: allow O(N^2) vectorized accelerations when feasible.
      vectorize_threshold: minimum N to switch to vectorized path.
      max_vectorized_bytes: cap memory the vectorized kernels are allowed to allocate.
    """

    def __init__(
        self,
        softening: float = 0.0,
        vectorized: bool = True,
        vectorize_threshold: int = 64,
        max_vectorized_bytes: int = 256_000_000,  # ~256MB
    ):
        self.softening = float(softening)
        self.vectorized = bool(vectorized)
        self.vectorize_threshold = int(vectorize_threshold)
        self.max_vectorized_bytes = int(max_vectorized_bytes)

    # ---------- acceleration kernels ----------

    @staticmethod
    def _accels_loop(G: float, m: np.ndarray, r: np.ndarray, eps2: float) -> np.ndarray:
        n = r.shape[0]
        a = np.zeros_like(r)
        for i in range(n):
            dr = r[i] - r
            dist2 = np.sum(dr * dr, axis=1) + eps2
            dist2[i] = np.inf  # avoid self singularity BEFORE division
            inv_r3 = 1.0 / np.power(dist2, 1.5)
            a[i] = -G * (dr * (m * inv_r3)[:, None]).sum(axis=0)
        return a

    @staticmethod
    def _accels_vectorized(G: float, m: np.ndarray, r: np.ndarray, eps2: float) -> np.ndarray:
        # Pairwise differences: (N,N,3)
        diff = r[:, None, :] - r[None, :, :]
        # Squared distances: (N,N)
        dist2 = np.einsum("ijk,ijk->ij", diff, diff) + eps2
        np.fill_diagonal(dist2, np.inf)           # avoid self division
        inv_r3 = 1.0 / np.power(dist2, 1.5)       # (N,N)
        # Broadcast masses on j-index then sum over j
        return -G * (diff * (m[None, :] * inv_r3)[:, :, None]).sum(axis=1)

    def _should_vectorize(self, n: int) -> bool:
        if not self.vectorized or n < self.vectorize_threshold:
            return False
        # Rough memory estimate: diff(N,N,3) + dist2(N,N) + inv_r3(N,N) ~ 48*N^2 bytes
        estimated = 48 * (n ** 2)
        return estimated < self.max_vectorized_bytes

    # ---------- time step ----------

    @staticmethod
    def _take_step(
        G: float,
        m: np.ndarray,
        r: np.ndarray,
        v: np.ndarray,
        dt_seconds: float,
        eps2: float,
        vectorized: bool,
    ) -> tuple[np.ndarray, np.ndarray]:
        if vectorized:
            a = VerletNBodySolver._accels_vectorized(G, m, r, eps2)
        else:
            a = VerletNBodySolver._accels_loop(G, m, r, eps2)
        v_half = v + 0.5 * dt_seconds * a
        r_new = r + dt_seconds * v_half
        if vectorized:
            a_new = VerletNBodySolver._accels_vectorized(G, m, r_new, eps2)
        else:
            a_new = VerletNBodySolver._accels_loop(G, m, r_new, eps2)
        v_new = v_half + 0.5 * dt_seconds * a_new
        return r_new, v_new

    def step(self, state: Dict[str, Any], lawcard: LawCard, dt_seconds: float) -> Dict[str, Any]:
        r = state["r"]
        v = state["v"]
        m = state["m"]
        t = state.get("t", 0.0)
        G = lawcard.parameters["G"].value
        eps2 = self.softening**2

        vectorized = self._should_vectorize(r.shape[0])
        r_new, v_new = self._take_step(G, m, r, v, dt_seconds, eps2, vectorized)
        return {"t": t + dt_seconds, "r": r_new, "v": v_new, "m": m}