# src/worldsim_core/resolver.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Iterable, Optional
import os, json, hashlib

from .models import LawCard

# ---- canonical hash (sha256 over canonical JSON with 'sha256' removed) ----
def _canonical_sha256(payload: dict) -> str:
    to_hash = dict(payload)
    to_hash.pop("sha256", None)
    blob = json.dumps(to_hash, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()

def _load_lawcard_from_path(path: Path, verify_hash: bool = True) -> LawCard:
    data = json.loads(path.read_text(encoding="utf-8"))
    card = LawCard(**data)
    if verify_hash and card.sha256:
        actual = _canonical_sha256(data)
        if actual != card.sha256:
            raise ValueError(
                f"sha256 mismatch for {path.name}: expected {card.sha256}, computed {actual}"
            )
    return card

# ---- search path assembly ---------------------------------------------------
def _env_paths() -> list[Path]:
    """Parse RULEGRAPH_CARD_PATHS (dirs or index.json files), pathsep-aware."""
    env = os.environ.get("RULEGRAPH_CARD_PATHS", "")
    if not env:
        return []
    out: list[Path] = []
    for raw in env.split(os.pathsep):
        raw = raw.strip()
        if not raw:
            continue
        out.append(Path(raw))
    return out

def _dev_mono_repo_paths() -> list[Path]:
    """
    Heuristic for local dev when worldsim-core is in a mono-repo:
    <repo>/worldsim-core/src/worldsim_core/resolver.py
    look for sibling '../lawcards/cards' and local examples.
    """
    here = Path(__file__).resolve()
    # repo_root ~= <...>/worldsim-core
    repo_root = here.parents[2] if len(here.parents) >= 3 else here.parent
    candidates = []
    # sibling lawcards/cards
    sib = repo_root.parent / "lawcards" / "cards"
    if sib.exists():
        candidates.append(sib)
    # legacy examples (keep as lowest priority)
    ex = repo_root / "examples" / "data" / "lawcards"
    if ex.exists():
        candidates.append(ex)
    return candidates

def _iter_json_files_in_dir(d: Path) -> Iterable[Path]:
    # walk recursively for *.json
    yield from d.rglob("*.json")

def _load_index(index_path: Path) -> dict[str, Path]:
    """
    Support a simple index JSON mapping id -> relative/absolute file path.
    Example file (lawcards/index.json):
      { "rg:law/gravity.newton.v1": "cards/physics/gravity/gravity.newton.v1.json", ... }
    """
    mapping = json.loads(index_path.read_text(encoding="utf-8"))
    out: dict[str, Path] = {}
    base = index_path.parent
    if isinstance(mapping, dict):
        for k, v in mapping.items():
            p = (base / v).resolve() if not str(v).startswith(("/", "\\")) and not Path(v).drive else Path(v).resolve()
            out[str(k)] = p
    return out

def _gather_search_space() -> tuple[list[Path], dict[str, Path]]:
    """
    Returns:
      (search_dirs, index_by_id)
      - search_dirs: directories to scan recursively for cards
      - index_by_id: id -> Path from any explicit index.json supplied in env
    """
    search_dirs: list[Path] = []
    index_by_id: dict[str, Path] = {}

    # 1) env: directories or index.json files
    for p in _env_paths():
        if p.is_file() and p.name.lower().endswith(".json"):
            try:
                index_by_id.update(_load_index(p))
            except Exception:
                # ignore bad index files; keep going
                pass
        elif p.is_dir():
            search_dirs.append(p)

    # 2) dev mono-repo heuristic (only if no env provided)
    if not search_dirs and not index_by_id:
        search_dirs.extend(_dev_mono_repo_paths())

    # de-dup while preserving order
    seen = set()
    dedup_dirs: list[Path] = []
    for d in search_dirs:
        rp = d.resolve()
        if rp not in seen:
            dedup_dirs.append(rp)
            seen.add(rp)
    return (dedup_dirs, index_by_id)

# ---- resolution -------------------------------------------------------------
def _resolve_iri_to_path(ref: str) -> Optional[Path]:
    """
    Resolve a LawCard id (IRI) to a local JSON file using:
      - any explicit index.json from RULEGRAPH_CARD_PATHS
      - scanning configured search directories (recursive)
    Cards whose sha256 does not verify are ignored (useful for *badhash* fixtures).
    """
    search_dirs, index_by_id = _gather_search_space()

    # 0) index mapping wins immediately
    if ref in index_by_id:
        p = index_by_id[ref]
        if p.exists():
            try:
                _ = _load_lawcard_from_path(p, verify_hash=True)
                return p
            except Exception:
                # if indexed file fails verification, treat as not found
                pass

    # 1) scan dirs for a matching id
    last_error: Optional[Exception] = None
    for d in search_dirs:
        if not d.exists():
            continue
        for p in _iter_json_files_in_dir(d):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("id") != ref:
                    continue
                # verify; skip if bad (e.g., *badhash* fixtures)
                _ = _load_lawcard_from_path(p, verify_hash=True)
                return p
            except Exception as e:
                last_error = e
                continue

    if last_error:
        # surface the last parse/verify error to aid debugging
        raise last_error
    return None

def resolve_cards(law_refs: List[str]) -> Dict[str, LawCard]:
    """
    Resolve LawCards by local file path or by IRI id.
    - If 'ref' is a path that exists, load and (by default) verify sha256.
    - Else, search by id using RULEGRAPH_CARD_PATHS / dev heuristics.
    Returns a dict keyed by LawCard.id.
    """
    out: Dict[str, LawCard] = {}
    for ref in law_refs:
        p = Path(ref)
        if p.exists():
            card = _load_lawcard_from_path(p)  # direct path: verify hash
        else:
            p2 = _resolve_iri_to_path(ref)
            if not p2:
                raise FileNotFoundError(
                    f"Cannot resolve LawCard ref '{ref}'. "
                    f"Provide a local path or set RULEGRAPH_CARD_PATHS."
                )
            card = _load_lawcard_from_path(p2, verify_hash=True)
        out[card.id] = card
    return out
