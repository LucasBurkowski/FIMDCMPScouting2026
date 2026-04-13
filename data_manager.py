"""
Local data persistence for the FIM DCMP Scouting tool.

Files stored in the ``data/`` directory next to this module:
- ``teams_data.json``  — cached TBA team/match data
- ``notes.json``       — per-team scouting notes keyed by team key
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, "data")
TEAMS_FILE = os.path.join(DATA_DIR, "teams_data.json")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


# ------------------------------------------------------------------
# Teams cache
# ------------------------------------------------------------------

def load_teams_data() -> dict:
    """Return cached team/match data or an empty dict."""
    if os.path.exists(TEAMS_FILE):
        try:
            with open(TEAMS_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_teams_data(data: dict) -> None:
    _ensure_data_dir()
    with open(TEAMS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


# ------------------------------------------------------------------
# Notes
# ------------------------------------------------------------------

def load_notes() -> dict:
    """Return saved scouting notes or an empty dict."""
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_notes(notes: dict) -> None:
    _ensure_data_dir()
    with open(NOTES_FILE, "w", encoding="utf-8") as fh:
        json.dump(notes, fh, indent=2)


# ------------------------------------------------------------------
# Config  (API key — kept outside of version control)
# ------------------------------------------------------------------

CONFIG_FILE = os.path.join(_HERE, "config.json")


def load_api_key() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as fh:
                return json.load(fh).get("api_key", "")
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def save_api_key(key: str) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
        json.dump({"api_key": key}, fh, indent=2)
