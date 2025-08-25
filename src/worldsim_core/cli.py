from __future__ import annotations
from pathlib import Path
import json
import argparse
from .models import World
from .resolver import resolve_cards
from .validate import validate
from .simulate import simulate
from .provenance import write_lockfile

def main() -> None:
    ap = argparse.ArgumentParser(description="Run a JSON-LD world with worldsim-core")
    ap.add_argument("world", help="Path to world JSON-LD")
    ap.add_argument("--dt", type=float, help="Override dtSeconds")
    ap.add_argument("--steps", type=int, help="Override steps")
    ap.add_argument("--lock", default="run.lock.json", help="Path to write lockfile JSON")
    args = ap.parse_args()

    world_path = Path(args.world)
    data = json.loads(world_path.read_text(encoding="utf-8"))
    w = World(**data)

    if args.dt is not None or args.steps is not None:
        w.config = dict(w.config or {})
        if args.dt is not None:
            w.config["dtSeconds"] = float(args.dt)
        if args.steps is not None:
            w.config["steps"] = int(args.steps)

    cards = resolve_cards([w.dynamics[0]["ref"]])
    rep = validate(w, cards)
    if not rep.ok:
        for i in rep.issues:
            print(f"VALIDATION: {i.path}: {i.message}")
        raise SystemExit(2)

    run = simulate(w, cards)
    write_lockfile(run, cards, args.lock)
    print(f"Steps={run.steps} dt={run.dt_seconds} drifts={run.drifts} lock={args.lock}")
