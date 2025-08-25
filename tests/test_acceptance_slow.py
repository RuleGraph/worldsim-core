import json, pytest
from pathlib import Path
from worldsim_core.models import World
from worldsim_core.resolver import resolve_cards
from worldsim_core.simulate import simulate

EX = Path(__file__).resolve().parents[1] / "examples" / "data"
TARGET = 1e-5  # 1-year @ 60s

@pytest.mark.slow
def test_earth_sun_one_year_energy_drift():
    w = World(**json.loads((EX / "worlds" / "two-body.demo.json").read_text()))
    w.config = dict(w.config or {})
    w.config["dtSeconds"] = 60.0
    w.config["steps"] = int(365 * 86400 / w.config["dtSeconds"])
    cards = resolve_cards([w.dynamics[0]["ref"]])
    run = simulate(w, cards)
    assert run.drifts["Energy"] < TARGET
