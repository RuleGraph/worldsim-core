from __future__ import annotations
import numpy as np
from typing import Dict

# Invariants: Energy, LinearMomentum, AngularMomentum

def kinetic_energy(m: np.ndarray, v: np.ndarray) -> float:
    return 0.5 * float(np.sum(m * np.sum(v*v, axis=1)))

def potential_energy(G: float, m: np.ndarray, r: np.ndarray) -> float:
    n = r.shape[0]
    pe = 0.0
    for i in range(n):
        dr = r[i+1:] - r[i]
        dist = np.linalg.norm(dr, axis=1)
        if dist.size:
            pe -= float(G * m[i] * np.sum(m[i+1:] / dist))
    return pe

def linear_momentum(m: np.ndarray, v: np.ndarray) -> np.ndarray:
    return (m[:, None] * v).sum(axis=0)

def angular_momentum(m: np.ndarray, r: np.ndarray, v: np.ndarray) -> np.ndarray:
    return np.cross(r, m[:, None] * v, axis=1).sum(axis=0)

def rel_drift(current: float | np.ndarray, baseline: float | np.ndarray) -> float:
    def _norm(x):
        return float(np.linalg.norm(x)) if not np.isscalar(x) else abs(float(x))
    denom = _norm(baseline)
    if denom == 0.0:
        return _norm(current)
    return abs((_norm(current) - denom) / denom)

def audit_invariants(G: float, m: np.ndarray, r: np.ndarray, v: np.ndarray) -> Dict[str, object]:
    ke = kinetic_energy(m, v)
    pe = potential_energy(G, m, r)
    E = ke + pe
    P = linear_momentum(m, v)
    L = angular_momentum(m, r, v)
    return {"Energy": E, "LinearMomentum": P, "AngularMomentum": L}