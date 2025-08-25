from pathlib import Path
import json
import pytest
from worldsim_core.resolver import resolve_cards

EX = Path(__file__).resolve().parents[1] / "examples" / "data"

def test_lawcard_sha256_mismatch_raises():
    bad = EX / "lawcards" / "gravity.newton.v1.badhash.json"
    with pytest.raises(ValueError) as ei:
        resolve_cards([str(bad)])
    assert "sha256 mismatch" in str(ei.value)