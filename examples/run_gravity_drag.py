from pathlib import Path
import json, os
from worldsim_core.models import World
from worldsim_core.resolver import resolve_cards
from worldsim_core.validate import validate
from worldsim_core.simulate import simulate
from worldsim_core.provenance import write_lockfile

HERE = Path(__file__).resolve().parent
WORLD_PATH = HERE / "data" / "worlds" / "gravity_drag.demo.json"

def main():
    print("WORLD PATH:", WORLD_PATH, "exists:", WORLD_PATH.exists())
    print("RULEGRAPH_CARD_PATHS =", os.environ.get("RULEGRAPH_CARD_PATHS"))

    world = World(**json.loads(WORLD_PATH.read_text(encoding="utf-8")))
    refs = [getattr(d, "ref", d.get("ref")) for d in world.dynamics]
    print("Dynamics refs:", refs)

    try:
        cards = resolve_cards(refs)
    except Exception as e:
        print("ERROR resolving LawCards:", e)
        print("Hint: ensure RULEGRAPH_CARD_PATHS points to your lawcards/index.json, "
              "and that index contains all refs above.")
        raise

    rep = validate(world, cards)
    if not rep.ok:
        for issue in rep.issues:
            print(f"VALIDATION: {issue.path}: {issue.message}")
        raise SystemExit(1)

    run = simulate(world, cards)
    print("Steps:", run.steps, "dt:", run.dt_seconds)
    print("Drifts:", {k: f"{v:.2e}" for k, v in run.drifts.items()})
    lock_path = HERE / "gravity-drag.lock.json"
    write_lockfile(run, cards, lock_path)
    print("Lockfile written:", lock_path)

if __name__ == "__main__":
    main()
