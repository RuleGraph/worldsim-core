from pathlib import Path
import json
from worldsim_core.models import World
from worldsim_core.resolver import resolve_cards
from worldsim_core.validate import validate
from worldsim_core.simulate import simulate

EX = Path(__file__).resolve().parents[1] / "examples" / "data"

REL_TOL = 5e-5  # 30-day @ 120 s

def test_two_body_30day_energy_drift():
    w = World(**json.loads((EX / "worlds" / "two-body.demo.json").read_text()))
    # Configure a 30-day run at 120 s
    w.config = dict(w.config or {})
    w.config["dtSeconds"] = 120.0
    w.config["steps"] = int(30 * 86400 / w.config["dtSeconds"])  # 21600

    cards = resolve_cards([w.dynamics[0]["ref"]])
    rep = validate(w, cards)
    assert rep.ok, f"validation failed: {[ (i.path, i.message) for i in rep.issues ]}"

    run = simulate(w, cards)
    assert run.drifts["Energy"] < REL_TOL, f"Energy drift {run.drifts['Energy']:.3e} exceeds {REL_TOL}"