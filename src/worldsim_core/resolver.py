from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import os, json, hashlib
from .models import LawCard

def _canonical_sha256(payload: dict) -> str:
    to_hash = dict(payload)
    to_hash.pop("sha256", None)
    blob = json.dumps(to_hash, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()

# Build default search dirs robustly:
# 1) walk up a few levels and add <root>/examples/data/lawcards if it exists
# 2) include extra dirs from RULEGRAPH_CARD_PATHS (os.pathsep-separated)
_DEF_SEARCH_DIRS: List[Path] = []
_here = Path(__file__).resolve()
for n in range(2, 6):  # src/worldsim_core -> src -> repo root -> parent...
    cand = _here.parents[n] / "examples" / "data" / "lawcards"
    if cand.exists():
        _DEF_SEARCH_DIRS.append(cand)

_extra = os.getenv("RULEGRAPH_CARD_PATHS", "")
for d in _extra.split(os.pathsep):
    if d:
        p = Path(d).expanduser().resolve()
        if p.exists():
            _DEF_SEARCH_DIRS.append(p)

def _resolve_iri_to_path(ref: str) -> Path | None:
    """
    Scan known dirs for a LawCard whose `id` matches `ref`.
    Ignore candidates whose sha256 does NOT verify (useful for test fixtures like *badhash*).
    """
    last_error = None
    for d in _DEF_SEARCH_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") != ref:
                    continue
                # Verify this candidate; skip if bad hash
                _ = _load_lawcard_from_path(p, verify_hash=True)
                return p
            except Exception as e:
                last_error = e
                continue
    if last_error:
        raise last_error
    return None

def _load_lawcard_from_path(path: Path, verify_hash: bool = True) -> LawCard:
    data = json.load(open(path, "r", encoding="utf-8"))
    card = LawCard(**data)
    if verify_hash and card.sha256:
        actual = _canonical_sha256(data)
        if actual != card.sha256:
            raise ValueError(
                f"sha256 mismatch for {path.name}: expected {card.sha256}, computed {actual}"
            )
    return card

def resolve_cards(law_refs: List[str]) -> Dict[str, LawCard]:
    out: Dict[str, LawCard] = {}
    for ref in law_refs:
        p = Path(ref)
        if p.exists():
            card = _load_lawcard_from_path(p)
        else:
            p2 = _resolve_iri_to_path(ref)
            if not p2:
                raise FileNotFoundError(
                    f"Cannot resolve LawCard ref '{ref}'. Provide a local path or set RULEGRAPH_CARD_PATHS."
                )
            card = _load_lawcard_from_path(p2)
        out[card.id] = card
    return out
