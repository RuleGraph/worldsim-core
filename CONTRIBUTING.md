# Contributing to worldsim-core

First off, thanks for taking the time to contribute! 🎉  
This project is part of the **RuleGraph** org and follows a “small, verifiable core” philosophy: laws-as-data (LawCards), typed state with units, invariants, and provenance.

> By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## How can I help?

- **Bug fixes & improvements** — issues labeled `good first issue` or `help wanted`.
- **Docs** — clarify README/CLI, examples, and contributor docs.
- **LawCards** — add/upgrade cards with validity ranges, invariants, test vectors, and hashes.
- **Spec** — propose schema/context changes via RFCs (see below).

---

## Development setup

```bash
git clone https://github.com/RuleGraph/worldsim-core.git
cd worldsim-core
python -m venv .venv
# mac/linux: source .venv/bin/activate
# windows:   .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

Python: 3.9+ (CI runs 3.11)

Run the demo:

```bash
worldsim-run examples/data/worlds/two-body.demo.json --dt 120 --steps 21600
```

- Fast tests: pytest

- Slow acceptance: pytest -m slow (1-year drift check)

# Coding guidelines

- Style: idiomatic Python; keep dependencies minimal (NumPy, Pydantic, pytest).

- Types: type your public APIs; prefer small, pure functions.

- Units & invariants: always check presence in validators; do not bypass.

- Errors: raise clear ValueError/FileNotFoundError with actionable messages.

- Commit messages: Conventional Commits (e.g., fix: …, feat: …, docs: …, test: …).

- Tests: add/extend tests for every change; keep slow tests under @pytest.mark.slow.

# LawCards: how to contribute

A LawCard is rules as data (JSON-LD). Each card must include:

- id (e.g., rg:law/gravity.newton.v1) and "version":"MAJOR.MINOR.PATCH"

- equations[*].machine (SymPy string) and equations[*].tex (optional but recommended)

- parameters with units and optional sigma

- validity (regimes, ranges, and assumptions)

- invariants (conserves + driftBudget with relative tolerances)

- stabilityModel (e.g., dtMaxRuleMachine, cflHint)

- testVectors (inputs → expected outputs with tolerances)

- sha256 (content hash of canonical JSON; see below)

If you submit a new or updated card, please also:

- Add a smoke test (or extend existing ones) using the card.

- Include a short CHANGELOG entry in your PR description.

For major schema changes or new families of laws, please open an RFC in the RuleGraph/spec repo first.

# Proposing spec/schema changes (RFC)

- Open an issue in RuleGraph/spec with [RFC] in the title.

- Include: problem statement, proposed fields, examples, and migration notes.


# Licensing

Code & specs: Apache-2.0

LawCards: CC-BY-4.0

By contributing, you agree your contributions are licensed under the repository’s licenses.