import warnings
import json
from pathlib import Path
from worldsim_core.models import World
from worldsim_core.resolver import resolve_cards
from worldsim_core.simulate import simulate

EX = Path(__file__).resolve().parents[1] / "examples" / "data"

def test_no_runtime_warnings():
    w = World(**json.loads((EX / "worlds" / "two-body.demo.json").read_text()))
    w.config = dict(w.config or {})
    w.config["dtSeconds"] = 120.0
    w.config["steps"] = int(30 * 86400 / w.config["dtSeconds"])
    cards = resolve_cards([w.dynamics[0]["ref"]])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        simulate(w, cards)
