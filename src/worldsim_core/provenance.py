from __future__ import annotations
import json
from pathlib import Path
from typing import Dict
from datetime import datetime, timezone

from .models import LawCard


def write_lockfile(run_result, cards: Dict[str, LawCard], path: str | Path):
    path = Path(path)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dtSeconds": run_result.dt_seconds,
        "steps": run_result.steps,
        "cards": {
            c.id: {
                "version": c.version,
                "sha256": c.sha256,
                "title": c.title,
            } for c in cards.values()
        },
        "drifts": run_result.drifts,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path