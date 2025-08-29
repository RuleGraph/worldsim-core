from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ---- Pydantic stubs (strict-enough for v0) ----

class Quantity(BaseModel):
    value: Any
    unit: str
    sigma: Optional[float] = None

class Vec3Quantity(BaseModel):
    value: List[float]
    unit: str
    sigma: Optional[float] = None

class State(BaseModel):
    frame: str
    t: str  # ISO 8601
    position: Vec3Quantity
    velocity: Vec3Quantity

from typing import Literal
class Body(BaseModel):
    id: str
    type: Literal["rg:Body"] = "rg:Body"
    mass: Quantity
    state: State

class Frame(BaseModel):
    id: str
    type: Literal["rg:InertialFrame"] = "rg:InertialFrame"
    metric: str
    units: Dict[str, str]  # {length, time, mass}

# --- Insert Equation model ---
class Equation(BaseModel):
    name: Optional[str] = None
    machine: Optional[str] = None
    tex: Optional[str] = None
    ast: Optional[Dict[str, Any]] = None  # allow structured AST

# --- Update LawCard and World models ---
class LawCard(BaseModel):
    id: str  # e.g. rg:law/gravity.newton.v1
    version: str
    # accept either legacy "gw:LawCard" or new "rg:LawCard"
    type: str = Field(pattern="^(gw|rg):LawCard$")
    title: str
    kind: List[str]
    equations: List[Equation]  # <-- was List[Dict[str, str]]
    parameters: Dict[str, "Parameter"]
    validity: Dict[str, Any]
    invariants: Dict[str, Any]
    stabilityModel: Optional[Dict[str, Any]] = None
    testVectors: Optional[List[Dict[str, Any]]] = None
    provenance: Optional[Dict[str, Any]] = None
    sha256: Optional[str] = None
    # optional enrichments (won't break older cards)
    symbols: Optional[Dict[str, Any]] = None
    numericProfile: Optional[Dict[str, Any]] = None

# also make World.type accept rg:World or gw:World
class World(BaseModel):
    id: str
    type: str = Field(pattern="^(gw|rg):World$")
    version: str
    frames: List["Frame"]
    entities: List["Body"]
    dynamics: List[Dict[str, str]]  # [{"ref": LawCard IRI or path}]
    solvers: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None

class Parameter(BaseModel):
    value: float
    unit: str
    sigma: Optional[float] = None

# Validation result containers
class ValidationIssue(BaseModel):
    path: str
    message: str

class ValidationReport(BaseModel):
    ok: bool
    issues: List[ValidationIssue] = []