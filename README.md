# worldsim-core

**RuleGraph’s minimal, dependency-light kernel for declarative simulation.**  
Loads JSON-LD **Worlds**, resolves **LawCards** (rules as data) with sha256 verification, validates units/blocks, runs a tiny N-body **Velocity-Verlet** demo, audits **invariants**, and writes a reproducible **lockfile**.

> Status: **alpha (v0.1.0)** — stable enough to try; API may evolve.

---

## Features

- **Rules as data (LawCards)** — resolve by IRI or file path, verify **sha256**.
- **Validation** — required fields, units present, `validity` & `invariants` blocks.
- **Integrator** — velocity-Verlet with loop **and** vectorized kernels (auto-selects with memory guard).
- **Invariant audit** — Energy, LinearMomentum, AngularMomentum + relative drift.
- **Provenance** — JSON **lockfile** with exact card digests and run metadata.
- **CLI** — `worldsim-run` to execute any world JSON quickly.
- **Tests** — fast smoke + slow 1-year acceptance (`@slow` marker).

---

## Install

```bash
# create and activate a virtual env
python -m venv .venv
# mac/linux:
source .venv/bin/activate
# windows powershell:
# .\.venv\Scripts\Activate.ps1

# editable install with dev deps (pytest etc.)
pip install -e ".[dev]"
```

Requirements: Python ≥ 3.9, NumPy ≥ 1.24, Pydantic 2.x.

# Quickstart (CLI)
```bash
# run fast tests
pytest

# run the two-body demo (30 days @ 120 s)
worldsim-run examples/data/worlds/two-body.demo.json --dt 120 --steps 21600
# Example output:
# Steps=21600 dt=120.0 drifts={'Energy': ~3.9e-15, 'LinearMomentum': ~8.9e-15, 'AngularMomentum': ~8.5e-15}
```

# CLI usage
```bash
worldsim-run <world.json> [--dt <seconds>] [--steps <N>] [--lock <file>]
```

# LawCard search paths

The resolver looks in the repo’s examples/data/lawcards and any extra directories from:

```bash
RULEGRAPH_CARD_PATHS=/abs/path/to/cards[:/another/path]
```

Set RULEGRAPH_DEBUG=1 to print the directories being searched.

# Quickstart (Python API)

```bash
from worldsim_core import simulate, resolve_cards, validate
from worldsim_core.models import World
from worldsim_core.provenance import write_lockfile
import json

# Load the example world JSON-LD
with open("examples/data/worlds/two-body.demo.json", "r", encoding="utf-8") as f:
    world = World(**json.load(f))

# Configure a 30-day run at 120 s
world.config = dict(world.config or {})
world.config["dtSeconds"] = 120.0
world.config["steps"] = int(30 * 86400 / world.config["dtSeconds"])

# Resolve LawCard by IRI (or pass a file path)
cards = resolve_cards([world.dynamics[0]["ref"]])

# Validate world + card (units & blocks present)
report = validate(world, cards)
assert report.ok, report.issues

# Simulate and write a lockfile
run = simulate(world, cards)
print(run.drifts)  # {"Energy": ..., "LinearMomentum": ..., "AngularMomentum": ...}
write_lockfile(run, cards, "run.lock.json")
```

# Customizing the solver
```bash
from worldsim_core.simulate import SolverRegistry, simulate
from worldsim_core.solvers.verlet import VerletNBodySolver

reg = SolverRegistry()
reg.register(
    "rg:law/gravity.newton.v1",
    VerletNBodySolver(
        softening=0.0,
        vectorized=True,           # allow O(N^2) vectorization
        vectorize_threshold=64,    # switch to vectorized when N >= 64
        max_vectorized_bytes=256_000_000,  # memory guard
    ),
)
run = simulate(world, cards, registry=reg)
```

# Examples

- World: examples/data/worlds/two-body.demo.json

- LawCard: examples/data/lawcards/gravity.newton.v1.json

Both are used by the CLI and tests.

# Tests & Acceptance

- Fast suite: unit presence, hash mismatch, smoke drift, no-warnings.

- Slow acceptance (local, opt-in): 1 year @ 60 s → Energy drift < 1e-5.

```bash
pytest                 # runs fast tests
pytest -m slow         # runs the slow acceptance test
```

# Repository layout
```bash
worldsim-core/
├─ pyproject.toml
├─ src/worldsim_core/
│  ├─ __init__.py
│  ├─ cli.py
│  ├─ models.py
│  ├─ resolver.py
│  ├─ validate.py
│  ├─ invariants.py
│  ├─ simulate.py
│  ├─ provenance.py
│  └─ solvers/
│     ├─ __init__.py
│     └─ verlet.py
├─ examples/
│  ├─ run_two_body.py
│  └─ data/
│     ├─ lawcards/
│     │  ├─ gravity.newton.v1.json
│     │  └─ gravity.newton.v1.badhash.json   # test fixture (intentionally wrong hash)
│     └─ worlds/
│        └─ two-body.demo.json
└─ tests/
   ├─ test_units.py
   ├─ test_resolver_hash.py
   ├─ test_smoke_drift.py
   ├─ test_no_warnings.py
   └─ test_acceptance_slow.py   # marked @slow
   ```

   # Contributor 

   - Francis Bousquet