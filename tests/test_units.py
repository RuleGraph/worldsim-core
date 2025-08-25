from pathlib import Path
import json
import pytest
from worldsim_core.models import World
from worldsim_core.resolver import resolve_cards
from worldsim_core.validate import validate

EX = Path(__file__).resolve().parents[1] / "examples" / "data"

def test_missing_unit_raises():
    world = World(**json.loads((EX / "worlds" / "two-body.demo.json").read_text()))
    world.entities[1].state.velocity.unit = ""

    cards = resolve_cards([world.dynamics[0]["ref"]])
    rep = validate(world, cards)
    assert not rep.ok
    msgs = [i.message for i in rep.issues]
    assert any("Velocity unit required" in m for m in msgs)