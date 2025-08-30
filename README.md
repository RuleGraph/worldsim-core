# worldsim-core

**RuleGraph’s minimal, dependency-light kernel for declarative simulation.**  
Loads JSON-LD **Worlds**, resolves **LawCards** (rules as data) with sha256 verification, validates units/blocks, runs **Velocity-Verlet** demo, audits **invariants**, and writes a reproducible **lockfile**.

> Status: **alpha (v0.1.1)** — stable enough to try; API may evolve.

---


What’s new in v0.1.1

Composable dynamics: run gravity plus additional laws (e.g., linear/quadratic drag) in one world.
Structured World.dynamics: entries now support:
selector — apply a law to specific bodies or pairs
override — per-world parameter overrides
Dissipative aware: if any law is dissipative, conservative stop-gates are disabled and drifts are reported accordingly.
Back-compat: legacy dict-style dynamics access still works (world.dynamics[0]["ref"]).

## Features

- **Rules as data (LawCards)** — resolve by IRI or file path, verify **sha256**.
- **Validation** — required fields, units present, `validity` & `invariants`.
- **Integrator** — velocity-Verlet with loop **and** vectorized kernels (auto-selects with memory guard).
- **Invariant audit** — Energy, LinearMomentum, AngularMomentum + relative drift.
- **Provenance** — JSON **lockfile** with exact card digests and run metadata.
- **CLI** — `worldsim-run` to execute any world JSON.
- **Tests** — fast smoke + optional slow acceptance.

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
```

# Set your LawCards index so the resolver can find cards
```bash
# Windows PowerShell example – adjust to your lawcards repo path
$env:RULEGRAPH_CARD_PATHS = "C:\path\to\RuleGraph\lawcards\index.json"
```

# Validate world + card (units & blocks present)
report = validate(world, cards)
assert report.ok, report.issues

# Simulate and write a lockfile
```bash
run = simulate(world, cards)
print(run.drifts)  # {"Energy": ..., "LinearMomentum": ..., "AngularMomentum": ...}
write_lockfile(run, cards, "run.lock.json")

pytest                 # runs fast tests
pytest -m slow         # runs the slow acceptance test
```

   # Contributor 

   - Francis Bousquet
