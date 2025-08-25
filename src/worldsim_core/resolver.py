from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import json, hashlib

from .models import LawCard

# Compute sha256 over canonical JSON with the 'sha256' field removed.
def _canonical_sha256(payload: dict) -> str:
    to_hash = dict(payload)
    to_hash.pop("sha256", None)
    blob = json.dumps(to_hash, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()

# Attempt to resolve known IRI ids to local example files
_DEF_SEARCH_DIRS = [
    Path(__file__).resolve().parents[3] / "examples" / "data" / "lawcards",
]

def _resolve_iri_to_path(ref: str) -> Path | None:
    # Extendable search dirs via env var RULEGRAPH_CARD_PATHS (pathsep-separated)
    import os
    extra = os.getenv("RULEGRAPH_CARD_PATHS", "")
    dirs = list(_DEF_SEARCH_DIRS)
    for d in extra.split(os.pathsep):
        if d:
            dirs.append(Path(d))
    # Simple heuristic: scan example lawcards for matching id
    for d in dirs:
        if not d.exists():
            continue
        for p in d.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == ref:
                    return p
            except Exception:
                continue
    return None

def _load_lawcard_from_path(path: Path, verify_hash: bool = True) -> LawCard:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    card = LawCard(**data)
    if verify_hash and card.sha256:
        actual = _canonical_sha256(data)
        if actual != card.sha256:
            raise ValueError(
                f"sha256 mismatch for {path.name}: expected {card.sha256}, computed {actual}"
            )
    return card

def resolve_cards(law_refs: List[str]) -> Dict[str, LawCard]:
    """Resolve LawCards by local file path or by IRI id. Verify sha256 when present.

    The returned dict is keyed by LawCard.id (not by ref).
    """
    out: Dict[str, LawCard] = {}
    for ref in law_refs:
        p = Path(ref)
        if p.exists():
            card = _load_lawcard_from_path(p)
        else:
            p2 = _resolve_iri_to_path(ref)
            if not p2:
                raise FileNotFoundError(
                    f"Cannot resolve LawCard ref '{ref}'. Provide a local path or add an example under examples/data/lawcards."
                )
            card = _load_lawcard_from_path(p2)
        out[card.id] = card
    return out