"""
Persist 'Mark as resolved' and 'Exclude' UI state to disk so it survives browser refresh.
- Resolved: cleared on new scan or load synthetic; used for Wins.
- Excluded: persisted by resource ID (Service+Resource); not cleared on scan (exceptions).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Project root (src/cwt_ui/utils -> project root)
_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR.parent.parent.parent / "data"
_RESOLVED_FILE = _DATA_DIR / "waste_resolved.json"
_EXCLUDED_FILE = _DATA_DIR / "waste_excluded.json"


def _ensure_data_dir() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def load_resolved() -> list[dict[str, Any]]:
    """Load resolved recommendations from file. Returns [] if missing or invalid."""
    if not _RESOLVED_FILE.exists():
        return []
    try:
        with open(_RESOLVED_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_resolved(items: list[dict[str, Any]]) -> None:
    """Write resolved list to file. Silently no-op on write error (e.g. read-only fs)."""
    try:
        _ensure_data_dir()
        with open(_RESOLVED_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=0)
    except OSError:
        pass


def clear_resolved() -> None:
    """Remove persisted file (e.g. on new scan)."""
    try:
        if _RESOLVED_FILE.exists():
            _RESOLVED_FILE.unlink()
    except OSError:
        pass


# --- Excluded (hide from list; persisted, not cleared on scan) ---

def load_excluded() -> list[dict[str, Any]]:
    """Load excluded recommendations from file. Returns [] if missing or invalid."""
    if not _EXCLUDED_FILE.exists():
        return []
    try:
        with open(_EXCLUDED_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_excluded(items: list[dict[str, Any]]) -> None:
    """Write excluded list to file."""
    try:
        _ensure_data_dir()
        with open(_EXCLUDED_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=0)
    except OSError:
        pass
