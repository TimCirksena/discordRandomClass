import os
import sys
import hmac
import json
import re
import subprocess
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, render_template, jsonify, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

PASSWORD = os.getenv("PANEL_PASSWORD", "changeme")
SERVICE = "discord-bot"

# Pfade: Panel liegt in <repo>/panel/app.py, Bot-Stats unter <repo>/stats/
REPO_ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = REPO_ROOT / "stats"

# Bot-Module fuer History-Reader importierbar machen
sys.path.insert(0, str(REPO_ROOT))
from playerstats import read_history, get_all_players_historical  # noqa: E402

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot-panel")

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

_PY_TIME_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*")


def client_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
    return fwd.split(",")[0].strip()


def check_password(provided: str) -> bool:
    if not provided:
        return False
    return hmac.compare_digest(provided.encode(), PASSWORD.encode())


def bot_status() -> str:
    r = subprocess.run(["systemctl", "is-active", SERVICE], capture_output=True, text=True)
    return r.stdout.strip()


def bot_logs(lines: int = 50) -> str:
    r = subprocess.run(
        ["journalctl", "-u", SERVICE, "-n", str(lines), "--no-pager", "-o", "json"],
        capture_output=True, text=True,
    )
    output = r.stdout.strip()
    if not output:
        return "Noch keine Logs."
    result = []
    for line in output.split("\n"):
        try:
            entry = json.loads(line)
            ts = int(entry.get("__REALTIME_TIMESTAMP", "0"))
            dt = datetime.fromtimestamp(ts / 1_000_000)
            msg = _PY_TIME_RE.sub("", entry.get("MESSAGE", ""))
            result.append(f"{dt.strftime('%H:%M:%S')}  {msg}")
        except (json.JSONDecodeError, ValueError):
            continue
    return "\n".join(result) or "Noch keine Logs."


def tier_for(score: int) -> str:
    if score > 40:
        return "legendary"
    if score < 18:
        return "trash"
    return "normal"


def aggregate_counts(history: list, field: str) -> list:
    counts = {}
    for entry in history:
        val = entry.get(field, "")
        if not val:
            continue
        counts[val] = counts.get(val, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def weapon_base(raw: str) -> str:
    """'M4A1 with FMJ' -> 'M4A1'."""
    return raw.split(" with ")[0].strip() if " with " in raw else raw.strip()


def build_stats_context():
    # Granular history (neues Format, pro Roll eine Zeile)
    full_history = []
    history_file = STATS_DIR / "history.jsonl"
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    full_history.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Leaderboard + Aggregat-Daten aus Daily Stats (alter + neuer Bestand)
    players_raw = get_all_players_historical()

    total_rolls_daily = sum(p.get("rolls", 0) for p in players_raw.values())
    # History bevorzugen, wenn sie umfangreicher ist (sonst Daily-Stats)
    total_rolls = max(len(full_history), total_rolls_daily)

    # Primary Waffe: wenn History Daten hat -> von da, sonst aus Daily Stats aggregieren
    if full_history:
        primary_counts = {}
        secondary_counts = {}
        for e in full_history:
            p = weapon_base(e.get("primary", ""))
            s = weapon_base(e.get("secondary", ""))
            if p:
                primary_counts[p] = primary_counts.get(p, 0) + 1
            if s:
                secondary_counts[s] = secondary_counts.get(s, 0) + 1
    else:
        primary_counts = {}
        secondary_counts = {}
        for p in players_raw.values():
            for weapon, count in p.get("weapons", {}).items():
                primary_counts[weapon] = primary_counts.get(weapon, 0) + count

    top_primary = sorted(primary_counts.items(), key=lambda x: x[1], reverse=True)
    top_secondary = sorted(secondary_counts.items(), key=lambda x: x[1], reverse=True)
    top_perk1 = aggregate_counts(full_history, "perk1")
    top_perk2 = aggregate_counts(full_history, "perk2")
    top_perk3 = aggregate_counts(full_history, "perk3")
    top_equip = aggregate_counts(full_history, "equipment")
    top_grenade = aggregate_counts(full_history, "special_grenade")

    leaderboard = []
    for uid, stats in players_raw.items():
        rolls = stats.get("rolls", 0)
        if rolls == 0:
            continue
        avg = stats.get("total_score", 0) / rolls
        worst = stats.get("worst_score", 999)
        leaderboard.append({
            "name": stats.get("name") or f"User {uid[-4:]}",
            "rolls": rolls,
            "avg": round(avg, 1),
            "best": stats.get("best_score", 0),
            "worst": worst if worst != 999 else 0,
            "legendary": stats.get("legendary_count", 0),
            "trash": stats.get("trash_count", 0),
        })
    leaderboard.sort(key=lambda p: p["rolls"], reverse=True)

    recent = list(reversed(full_history))[:50]
    for r in recent:
        r["tier"] = tier_for(r.get("score", 0))
        r["time"] = r.get("ts", "")[11:16]
        r["date"] = r.get("ts", "")[:10]

    return {
        "total_rolls": total_rolls,
        "top_primary": top_primary[:10],
        "top_secondary": top_secondary[:10],
        "top_perk1": top_perk1[:10],
        "top_perk2": top_perk2[:10],
        "top_perk3": top_perk3[:10],
        "top_equip": top_equip[:10],
        "top_grenade": top_grenade[:10],
        "leaderboard": leaderboard,
        "recent": recent,
        "legacy_only": not full_history,
    }


@app.route("/")
def index():
    return render_template("index.html", status=bot_status(), logs=bot_logs())


@app.route("/stats")
def stats_page():
    ctx = build_stats_context()
    return render_template("stats.html", **ctx)


@app.route("/status")
@limiter.limit("60/minute")
def status():
    return jsonify({"status": bot_status(), "logs": bot_logs()})


@app.route("/action", methods=["POST"])
@limiter.limit("10/minute;30/hour")
def action():
    ip = client_ip()
    ua = request.headers.get("User-Agent", "?")[:120]
    if not check_password(request.form.get("password", "")):
        log.warning(f"FAILED auth from {ip} UA={ua}")
        return jsonify({"ok": False, "error": "Falsches Passwort"}), 403
    act = request.form.get("action")
    log.info(f"{(act or 'UNKNOWN').upper()} from {ip} UA={ua}")
    if act == "start":
        subprocess.run(["sudo", "systemctl", "start", SERVICE], check=False)
        return jsonify({"ok": True, "message": "Bot wird gestartet"})
    if act == "stop":
        subprocess.run(["sudo", "systemctl", "stop", SERVICE], check=False)
        return jsonify({"ok": True, "message": "Bot wird gestoppt"})
    return jsonify({"ok": False, "error": "Unbekannte Aktion"}), 400


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"ok": False, "error": "Zu viele Anfragen, kurz warten"}), 429


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
