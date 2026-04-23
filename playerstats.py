# playerstats.py
# Persistent + Session player statistics
# Historische Stats werden taeglich in stats/DDMMYYYY_stats.json gespeichert

import json
import os
from datetime import datetime

import config as app_config

STATS_DIR = os.path.join(os.path.dirname(__file__), "stats")
HISTORY_FILE = os.path.join(STATS_DIR, "history.jsonl")
NAMES_FILE = os.path.join(STATS_DIR, "user_names.json")


def _today_file() -> str:
    return os.path.join(STATS_DIR, datetime.now().strftime("%d%m%Y") + "_stats.json")


def _empty_stats():
    return {
        "rolls": 0,
        "total_score": 0,
        "best_score": 0,
        "worst_score": 999,
        "legendary_count": 0,
        "trash_count": 0,
        "weapons": {},
        "name": "",
    }


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_all_historical() -> dict:
    """Merge all daily stats files into one combined dict."""
    combined = {}
    names = _load_json(NAMES_FILE)
    if not os.path.exists(STATS_DIR):
        return combined
    for filename in os.listdir(STATS_DIR):
        if not filename.endswith("_stats.json"):
            continue
        filepath = os.path.join(STATS_DIR, filename)
        daily = _load_json(filepath)
        for uid, stats in daily.items():
            if uid not in combined:
                combined[uid] = _empty_stats()
            c = combined[uid]
            c["rolls"] += stats.get("rolls", 0)
            c["total_score"] += stats.get("total_score", 0)
            if stats.get("best_score", 0) > c["best_score"]:
                c["best_score"] = stats["best_score"]
            worst = stats.get("worst_score", 999)
            if worst < c["worst_score"]:
                c["worst_score"] = worst
            c["legendary_count"] += stats.get("legendary_count", 0)
            c["trash_count"] += stats.get("trash_count", 0)
            for weapon, count in stats.get("weapons", {}).items():
                c["weapons"][weapon] = c["weapons"].get(weapon, 0) + count
            if stats.get("name") and not c.get("name"):
                c["name"] = stats["name"]
        # Fallback: aus zentraler names-Datei
        for uid, data in combined.items():
            if not data.get("name") and uid in names:
                data["name"] = names[uid]
    return combined


def _record_history(user_id: int, display_name: str, class_data: dict, total_score: int):
    """Append a single roll entry to history.jsonl."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user_id": str(user_id),
        "name": display_name,
        "primary": class_data.get("primary", ""),
        "secondary": class_data.get("secondary", ""),
        "equipment": class_data.get("equipment", ""),
        "special_grenade": class_data.get("special_grenade", ""),
        "perk1": class_data.get("perk1", ""),
        "perk2": class_data.get("perk2", ""),
        "perk3": class_data.get("perk3", ""),
        "score": total_score,
    }
    os.makedirs(STATS_DIR, exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _remember_name(user_id: int, display_name: str):
    if not display_name:
        return
    names = _load_json(NAMES_FILE)
    uid = str(user_id)
    if names.get(uid) != display_name:
        names[uid] = display_name
        _save_json(NAMES_FILE, names)


def read_history(limit: int = 50) -> list:
    """Returns the last `limit` history entries (newest first)."""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    entries = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(entries) >= limit:
            break
    return entries


# In-memory stores
_today: dict = _load_json(_today_file())
_session: dict = {}


def _ensure_player(store: dict, user_id: str):
    if user_id not in store:
        store[user_id] = _empty_stats()


def record_roll(user_id: int, class_data: dict, total_score: int, display_name: str = ""):
    """Record a roll for today's file, session stats and history."""
    uid = str(user_id)

    for store in (_today, _session):
        _ensure_player(store, uid)
        s = store[uid]
        s["rolls"] += 1
        s["total_score"] += total_score
        if total_score > s["best_score"]:
            s["best_score"] = total_score
        if total_score < s["worst_score"]:
            s["worst_score"] = total_score
        if total_score > app_config.get("legendary_min"):
            s["legendary_count"] += 1
        if total_score < app_config.get("trash_max"):
            s["trash_count"] += 1
        if display_name:
            s["name"] = display_name

        primary = class_data.get("primary", "")
        weapon = primary.split(" with ")[0].strip() if " with " in primary else primary.strip()
        if weapon:
            s["weapons"][weapon] = s["weapons"].get(weapon, 0) + 1

    _save_json(_today_file(), _today)
    _remember_name(user_id, display_name)
    _record_history(user_id, display_name, class_data, total_score)


def get_player_stats(user_id: int) -> tuple[dict, dict]:
    """Returns (historical_stats, session_stats) for a player."""
    uid = str(user_id)
    historical = _load_all_historical()
    hist = historical.get(uid, _empty_stats())
    sess = _session.get(uid, _empty_stats())
    return hist, sess


def reset_session():
    """Reset all session stats (call on bot start or manually)."""
    _session.clear()


def get_all_players_session() -> dict:
    """Returns all session stats."""
    return _session


def get_all_players_historical() -> dict:
    """Returns all historical stats."""
    return _load_all_historical()
