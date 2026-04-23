# config.py
# Persistente Runtime-Config, aenderbar via /threshold Admin-Command.

import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "stats", "config.json")

_defaults = {
    "legendary_min": 40,   # Score > legendary_min -> Legendary Tier (Channel-Ansage + TTS + Leaderboard-Count)
    "trash_max": 18,       # Score < trash_max    -> Trash Tier     (Channel-Ansage + TTS + Leaderboard-Count)
}

_config: dict = dict(_defaults)


def _load():
    global _config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _config = {**_defaults, **data}
        except (json.JSONDecodeError, OSError):
            _config = dict(_defaults)


def _save():
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(_config, f, indent=2, ensure_ascii=False)


def get(key: str):
    return _config.get(key, _defaults.get(key))


def set_value(key: str, value):
    if key in _defaults:
        _config[key] = value
        _save()


def all_values() -> dict:
    return dict(_config)


_load()
