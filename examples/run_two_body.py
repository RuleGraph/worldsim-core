from pathlib import Path
import json
from worldsim_core.models import World
from worldsim_core.resolver import resolve_cards
from worldsim_core.validate import validate
from worldsim_core.simulate import simulate
from worldsim_core.provenance import write_lockfile

HERE = Path(__file__).resolve().parent
WORLD_PATH = HERE / "data" / "worlds" / "two-body.demo.json"

if __name__ == "__main__":
    world = World(**json.loads(WORLD_PATH.read_text()))

    world.config = dict(world.config or {})
    world.config["dtSeconds"] = 120.0
    world.config["steps"] = int(30 * 86400 / world.config["dtSeconds"])

    cards = resolve_cards([world.dynamics[0]["ref"]])

    rep = validate(world, cards)
    if not rep.ok:
        for issue in rep.issues:
            print(f"VALIDATION: {issue.path}: {issue.message}")
        raise SystemExit(1)

    run = simulate(world, cards)
    print("Steps:", run.steps, "dt:", run.dt_seconds)
    print("Drifts:", {k: f"{v:.2e}" for k, v in run.drifts.items()})

    lock_path = HERE / "two-body.lock.json"
    write_lockfile(run, cards, lock_path)
    print("Lockfile written:", lock_path)