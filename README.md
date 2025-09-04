# worldsim-core

**RuleGraph’s minimal, dependency-light kernel for running worlds from rules as data (LawCards).**
It loads JSON(-LD) Worlds, resolves LawCards, validates units/blocks, runs a Velocity-Verlet stepper, audits invariants, and writes a reproducible lockfile.

**Status**: alpha (v0.1.x) — stable enough to try; APIs may evolve.

What’s new (since 0.1.0)

- **RG-AST v1.2 support** — piecewise, relations/logicals (lt/le/gt/ge/eq/ne, and/or/not), elementary math (exp/log/sqrt/sin/cos/…).
- **LawCard v0.2 support** — symbols, equations[*].astProfile, extensions (x-*) and stability/test blocks, plus dissipative flag handling.
- **Composable dynamics** — multiple laws in one world (e.g., gravity + linear drag + springs).
- **Selectors** — apply a law to specific bodies/pairs via structured selectors.
- **Overrides** — world-local parameter overrides per dynamic entry.
- **Index-based card resolution** — resolve rg:law/... via a local index.json (or file paths), with sha256 verification.
- **Lockfiles** — exact card digests + run metadata for deterministic re-runs.

# Key concepts

- LawCards — self-contained, signed JSON rules (equations as canonical AST, units, invariants, provenance).
Schemas:

    - AST: https://rulegraph.org/schema/rg-ast/v1.2/rg-ast-v1.2.schema.json
    - LawCard: https://rulegraph.org/schema/lawcard/v0.2/lawcard-v0.2.schema.json

- World — a minimal JSON describing entities (state + units) and a list of dynamics (which cards to apply to which subsets).

- Lockfile — output JSON recording exact card digests and key run parameters.

# Install
```
# from repo root
python -m venv .venv
. .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -e .
```

(Optional) point to your LawCard index:
```
export RULEGRAPH_CARD_PATHS=/absolute/path/to/lawcards/index.json
# Windows PowerShell:
# $Env:RULEGRAPH_CARD_PATHS="C:\path\to\lawcards\index.json"
```

# Quickstart

Run a built-in example world:
```
worldsim-run examples/data/worlds/two-body.demo.json --steps 21600 --dt 120
# → prints invariant drifts and writes run.lock.json
```

Typical output:
```
Steps=21600 dt=120.0 drifts={'Energy': 3.9e-15, 'LinearMomentum': 8.9e-15, 'AngularMomentum': 8.5e-15} lock=run.lock.json
```

**Programmatic use**
```
from pathlib import Path
import json
from worldsim_core.engine import run_world
from worldsim_core.models import World

world = World(**json.loads(Path("examples/data/worlds/two-body.demo.json").read_text()))
result = run_world(world, steps=21600, dt=120.0)
print(result.drifts)
Path("run.lock.json").write_text(result.lock_json, encoding="utf-8")
```

# World schema (essentials)

A world specifies entities and a list of dynamics:
```
{
  "entities": [
    {
      "id": "body1",
      "state": {
        "position": {"value": [0, 0, 0], "unit": "unit:M"},
        "velocity": {"value": [0, 29780, 0], "unit": "unit:M-PER-SEC"},
        "mass":     {"value": 5.972e24, "unit": "unit:KG"}
      }
    },
    { "id": "body2", "state": { /* ... */ } }
  ],
  "dynamics": [
    {
      "ref": "rg:law/physics.gravity.newton.v1",
      "selector": { "pairs": [["body1","body2"]] }
    },
    {
      "ref": "rg:law/physics.fluids.drag.linear.v1",
      "selector": { "bodies": ["body1"] },
      "override": { "alpha": 0.02 }
    }
  ],
  "integrator": { "kind": "velocity-verlet" }
}
```

**Selectors**

- {"pairs": [[idA, idB], ...]} — apply a pairwise law to listed ordered pairs.
- {"bodies": [id, ...]} — apply a single-body law to listed bodies.

**Overrides**

override is a dict of parameter name → value, merged on top of the card’s parameters.

# LawCard resolution

Resolution order:

1. IRI via index — the engine looks up ref in RULEGRAPH_CARD_PATHS (a JSON mapping of rg:law/... → file path or URL).
2. Direct path — if ref looks like a file path, it’s loaded directly.

All cards are sha256-verified (field sha256) post-canonicalization of their JSON.

# Invariant audit & lockfile

After each run the engine:

- Computes relative drifts for declared invariants (e.g., Energy, Linear/Angular momentum).
- Writes a lockfile with:
    - world metadata (dt, steps),
    - resolved cards (IRI + sha256),
    - minimal run provenance.

Used for reproducibility and for training/analysis pipelines to associate exact rule versions.

# CLI
```
worldsim-run <world.json> [--steps N] [--dt SEC] [--lock out.json]
```

- --steps number of integration steps
- --dt timestep (seconds)
- --lock output lockfile path (default: run.lock.json)

# Schemas & validation

- **AST** (used inside LawCards):
https://rulegraph.org/schema/rg-ast/v1.2/rg-ast-v1.2.schema.json
- **LawCard**:
https://rulegraph.org/schema/lawcard/v0.2.1/lawcard-v0.2.1.schema.json
- **World** (repo local, minimal): see examples/data/worlds/ and tests for shape.

If you publish your own cards, use the LawCards repo tooling to canonicalize AST and compute sha256, then reference them here.

# Examples

- examples/data/worlds/two-body.demo.json — gravity only (two-body).
- examples/data/worlds/gravity-drag.demo.json — gravity + linear drag.
- (You can add springs, Coulomb, hybrid drag, etc., as more cards land.)

# Roadmap (short version)

- Semi-implicit/implicit integrators & adaptive dt.
- Sparse selectors (patterns/predicates).
- Richer audit hooks (per-dynamic energy budgets).
- Streaming/online locking for long runs.

# Contributing

PRs welcome! Keep changes small and well-tested.

- Fast tests: pytest -q -m "not slow"
- Full examples: run via worldsim-run above.

# License & author

- LawCards carry their own licenses (see each card’s license field, most common : CC-BY-4.0). 
- The worldsim-core v1 have been developped by GourouWeb (https://gourouweb.com) and gifted to us under Apache 2.0 license.

**Pointers**

- LawCards repo: https://github.com/RuleGraph/lawcards
- Spec (schemas & docs): https://github.com/RuleGraph/spec
