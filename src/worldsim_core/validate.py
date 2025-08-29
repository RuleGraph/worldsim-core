from __future__ import annotations
from typing import Dict, List
from .models import World, LawCard, ValidationReport, ValidationIssue

REQ_WORLD_KEYS = ["frames", "entities", "dynamics"]
REQ_UNITS = ["length", "time", "mass"]

def _has_units(frame_units: Dict[str, str]) -> bool:
    return all(k in frame_units and isinstance(frame_units[k], str) and frame_units[k] for k in REQ_UNITS)

def validate(world: World, cards: Dict[str, LawCard]) -> ValidationReport:
    issues: List[ValidationIssue] = []

    # Basic presence
    for k in REQ_WORLD_KEYS:
        if getattr(world, k, None) in (None, []):
            issues.append(ValidationIssue(path=f"world.{k}", message=f"Missing required field '{k}'"))

    # Units present on frame 0
    if world.frames:
        if not _has_units(world.frames[0].units):
            issues.append(ValidationIssue(path="world.frames[0].units", message="Units must include length,time,mass"))

    # Units present on all physical values
    for ent in world.entities:
        if not ent.mass.unit:
            issues.append(ValidationIssue(path=f"{ent.id}.mass.unit", message="Mass unit required"))
        if not ent.state.position.unit:
            issues.append(ValidationIssue(path=f"{ent.id}.state.position.unit", message="Position unit required"))
        if not ent.state.velocity.unit:
            issues.append(ValidationIssue(path=f"{ent.id}.state.velocity.unit", message="Velocity unit required"))

    # LawCards must include validity and invariants
    for law_id in [d.ref for d in world.dynamics]:
        lc = cards.get(law_id) or next((c for c in cards.values() if c.id == law_id), None)
        if lc is None:
            issues.append(ValidationIssue(path=f"dynamics:{law_id}", message="LawCard not resolved"))
            continue
        if lc.validity is None:
            issues.append(ValidationIssue(path=f"{lc.id}.validity", message="LawCard.validity required"))
        if lc.invariants is None:
            issues.append(ValidationIssue(path=f"{lc.id}.invariants", message="LawCard.invariants required"))

    ok = len(issues) == 0
    return ValidationReport(ok=ok, issues=issues)