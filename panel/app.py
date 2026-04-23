import os
import sys
import hmac
import json
import re
import subprocess
import logging
from datetime import datetime, date, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, request, render_template, jsonify, url_for, redirect, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

load_dotenv()

PASSWORD = os.getenv("PANEL_PASSWORD", "changeme")
SERVICE = "discord-bot"

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
ADMIN_DISCORD_ID = os.getenv("ADMIN_DISCORD_ID", "")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-secret-change-me")

# Pfade: Panel liegt in <repo>/panel/app.py, Bot-Stats unter <repo>/stats/
REPO_ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = REPO_ROOT / "stats"

# Bot-Module fuer History-Reader importierbar machen
sys.path.insert(0, str(REPO_ROOT))
from playerstats import (  # noqa: E402
    read_history,
    get_all_players_historical,
    record_rating,
    read_ratings,
    ratings_by_user_fingerprint,
    class_fingerprint,
)
import randomClass as rc_module  # noqa: E402
from scoringmodel import calculate_class_score  # noqa: E402

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

oauth = OAuth(app)
oauth.register(
    name="discord",
    client_id=DISCORD_CLIENT_ID,
    client_secret=DISCORD_CLIENT_SECRET,
    authorize_url="https://discord.com/oauth2/authorize",
    access_token_url="https://discord.com/api/oauth2/token",
    api_base_url="https://discord.com/api/",
    client_kwargs={"scope": "identify"},
)


def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth_login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth_login", next=request.path))
        if str(session["user"].get("id", "")) != str(ADMIN_DISCORD_ID):
            return render_template("forbidden.html"), 403
        return f(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_user():
    return {
        "current_user": session.get("user"),
        "is_admin": bool(session.get("user") and str(session["user"].get("id", "")) == str(ADMIN_DISCORD_ID)),
    }

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


def build_stats_context(user_filter: str = ""):
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

    # User-Liste fuer Dropdown (sortiert nach Rolls desc)
    user_options = sorted(
        [
            {"id": uid, "name": s.get("name") or f"User {uid[-4:]}", "rolls": s.get("rolls", 0)}
            for uid, s in players_raw.items()
            if s.get("rolls", 0) > 0
        ],
        key=lambda x: x["rolls"],
        reverse=True,
    )

    # Filter anwenden wenn gesetzt
    filtered_history = full_history
    filtered_players = players_raw
    if user_filter:
        filtered_history = [e for e in full_history if str(e.get("user_id", "")) == user_filter]
        filtered_players = {uid: s for uid, s in players_raw.items() if uid == user_filter}

    total_rolls_daily = sum(p.get("rolls", 0) for p in filtered_players.values())
    total_rolls = max(len(filtered_history), total_rolls_daily)

    # Primary / Secondary Aggregate
    if filtered_history:
        primary_counts = {}
        secondary_counts = {}
        for e in filtered_history:
            p = weapon_base(e.get("primary", ""))
            s = weapon_base(e.get("secondary", ""))
            if p:
                primary_counts[p] = primary_counts.get(p, 0) + 1
            if s:
                secondary_counts[s] = secondary_counts.get(s, 0) + 1
    else:
        primary_counts = {}
        secondary_counts = {}
        for p in filtered_players.values():
            for weapon, count in p.get("weapons", {}).items():
                primary_counts[weapon] = primary_counts.get(weapon, 0) + count

    top_primary = sorted(primary_counts.items(), key=lambda x: x[1], reverse=True)
    top_secondary = sorted(secondary_counts.items(), key=lambda x: x[1], reverse=True)
    top_perk1 = aggregate_counts(filtered_history, "perk1")
    top_perk2 = aggregate_counts(filtered_history, "perk2")
    top_perk3 = aggregate_counts(filtered_history, "perk3")
    top_equip = aggregate_counts(filtered_history, "equipment")
    top_grenade = aggregate_counts(filtered_history, "special_grenade")

    leaderboard = []
    for uid, stats in filtered_players.items():
        rolls = stats.get("rolls", 0)
        if rolls == 0:
            continue
        avg = stats.get("total_score", 0) / rolls
        worst = stats.get("worst_score", 999)
        leaderboard.append({
            "id": uid,
            "name": stats.get("name") or f"User {uid[-4:]}",
            "rolls": rolls,
            "avg": round(avg, 1),
            "best": stats.get("best_score", 0),
            "worst": worst if worst != 999 else 0,
            "legendary": stats.get("legendary_count", 0),
            "trash": stats.get("trash_count", 0),
        })
    leaderboard.sort(key=lambda p: p["rolls"], reverse=True)

    # Recent rolls: filtered oder all
    recent_source = filtered_history if user_filter else full_history
    recent = list(reversed(recent_source))[:50]
    for r in recent:
        r["tier"] = tier_for(r.get("score", 0))
        r["time"] = r.get("ts", "")[11:16]
        r["date"] = r.get("ts", "")[:10]

    selected_user_name = ""
    if user_filter:
        for u in user_options:
            if u["id"] == user_filter:
                selected_user_name = u["name"]
                break

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
        "user_options": user_options,
        "user_filter": user_filter,
        "selected_user_name": selected_user_name,
    }


@app.route("/")
def index():
    return render_template("index.html", status=bot_status(), logs=bot_logs())


@app.route("/stats")
def stats_page():
    user_filter = request.args.get("user", "").strip()
    ctx = build_stats_context(user_filter=user_filter)
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


# ==================== AUTH (Discord OAuth) ====================

@app.route("/auth/login")
def auth_login():
    next_path = request.args.get("next", "/rate")
    session["next_url"] = next_path
    redirect_uri = url_for("auth_callback", _external=True, _scheme="https")
    return oauth.discord.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    try:
        token = oauth.discord.authorize_access_token()
        resp = oauth.discord.get("users/@me", token=token)
        user = resp.json()
    except Exception as e:
        log.warning(f"OAuth callback failed: {e}")
        return render_template("auth_error.html"), 400

    session["user"] = {
        "id": str(user.get("id", "")),
        "username": user.get("username", ""),
        "global_name": user.get("global_name") or user.get("username", ""),
        "avatar": user.get("avatar"),
    }
    log.info(f"Login: {session['user']['global_name']} ({session['user']['id']})")
    next_url = session.pop("next_url", "/rate")
    return redirect(next_url)


@app.route("/auth/logout")
def auth_logout():
    session.pop("user", None)
    return redirect(url_for("index"))


# ==================== RATING ====================

def _parse_history_entries() -> list:
    history_file = STATS_DIR / "history.jsonl"
    entries = []
    if not history_file.exists():
        return entries
    with open(history_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _filter_history_by_date(entries: list, date_range: str) -> list:
    today = date.today()
    if date_range == "today":
        cutoff = today
        return [e for e in entries if e.get("ts", "")[:10] == cutoff.isoformat()]
    if date_range == "yesterday":
        cutoff = today - timedelta(days=1)
        return [e for e in entries if e.get("ts", "")[:10] == cutoff.isoformat()]
    if date_range == "7days":
        cutoff = today - timedelta(days=7)
        return [e for e in entries if e.get("ts", "")[:10] >= cutoff.isoformat()]
    return entries  # "all"


def _history_to_rate_card(entry: dict) -> dict:
    class_data = {
        "primary": entry.get("primary", ""),
        "secondary": entry.get("secondary", ""),
        "equipment": entry.get("equipment", ""),
        "special_grenade": entry.get("special_grenade", ""),
        "perk1": entry.get("perk1", ""),
        "perk2": entry.get("perk2", ""),
        "perk3": entry.get("perk3", ""),
    }
    return {
        "class": class_data,
        "current_score": entry.get("score", 0),
        "fingerprint": class_fingerprint(class_data),
        "rolled_by": entry.get("name", ""),
        "rolled_at": entry.get("ts", ""),
    }


def _generate_training_card() -> dict:
    r = rc_module.RandomClass()
    perk1 = r.get_random_perk1()
    perk2 = r.get_random_perk2()
    perk3 = r.get_random_perk3()
    primary = r.get_random_primary(perk1)
    secondary = r.get_random_secondary(perk1)
    equipment = r.get_random_equipment()
    special_grenade = r.get_random_special_grenade()
    class_data = {
        "primary": primary,
        "secondary": secondary,
        "equipment": equipment,
        "special_grenade": special_grenade,
        "perk1": perk1,
        "perk2": perk2,
        "perk3": perk3,
    }
    score = calculate_class_score(class_data)
    return {
        "class": class_data,
        "current_score": score,
        "fingerprint": class_fingerprint(class_data),
        "rolled_by": "",
        "rolled_at": "",
    }


@app.route("/rate")
@require_login
def rate_home():
    user_id = session["user"]["id"]
    all_ratings = read_ratings()
    today_str = date.today().isoformat()
    my_today = sum(1 for r in all_ratings if r.get("rater_id") == user_id and r.get("ts", "")[:10] == today_str)
    my_total = sum(1 for r in all_ratings if r.get("rater_id") == user_id)
    total = len(all_ratings)
    return render_template(
        "rate.html",
        my_today=my_today,
        my_total=my_total,
        total_ratings=total,
    )


@app.route("/rate/session")
@require_login
def rate_session():
    return render_template("rate_session.html")


@app.route("/rate/train")
@require_login
def rate_train():
    return render_template("rate_train.html")


@app.route("/rate/analysis")
@require_admin
def rate_analysis():
    # Aggregation nach (user, fingerprint) - letztes Rating zaehlt
    latest = ratings_by_user_fingerprint()
    ratings = list(latest.values())

    JUDGMENT_VALUE = {"low": +1, "fair": 0, "high": -1}

    def _primary_weapon(class_data: dict) -> str:
        p = class_data.get("primary", "")
        return p.split(" with ")[0].strip() if " with " in p else p.strip()

    def _secondary_weapon(class_data: dict) -> str:
        s = class_data.get("secondary", "")
        return s.split(" with ")[0].strip() if " with " in s else s.strip()

    by_component: dict[tuple[str, str], dict] = {}

    def _add(cat: str, name: str, r: dict):
        if not name:
            return
        key = (cat, name)
        b = by_component.setdefault(key, {"count": 0, "judgment_sum": 0, "delta_sum": 0, "delta_count": 0})
        b["count"] += 1
        b["judgment_sum"] += JUDGMENT_VALUE.get(r.get("judgment", "fair"), 0)
        if r.get("suggested_score") is not None:
            b["delta_sum"] += r["suggested_score"] - r["current_score"]
            b["delta_count"] += 1

    for r in ratings:
        cd = r.get("class", {})
        _add("Primary", _primary_weapon(cd), r)
        _add("Secondary", _secondary_weapon(cd), r)
        _add("Equipment", cd.get("equipment", ""), r)
        _add("Grenade", cd.get("special_grenade", ""), r)
        _add("Perk1", cd.get("perk1", ""), r)
        _add("Perk2", cd.get("perk2", ""), r)
        _add("Perk3", cd.get("perk3", ""), r)

    rows = []
    for (cat, name), b in by_component.items():
        count = b["count"]
        avg_judgment = b["judgment_sum"] / count if count else 0.0
        avg_delta = b["delta_sum"] / b["delta_count"] if b["delta_count"] else None
        rows.append({
            "category": cat,
            "name": name,
            "count": count,
            "avg_judgment": round(avg_judgment, 2),
            "avg_delta": round(avg_delta, 1) if avg_delta is not None else None,
            "bias": "zu hoch" if avg_judgment < -0.25 else ("zu niedrig" if avg_judgment > 0.25 else "passt"),
        })

    rows.sort(key=lambda x: abs(x["avg_judgment"]), reverse=True)

    return render_template(
        "rate_analysis.html",
        rows=rows,
        total_ratings=len(ratings),
    )


# ==================== RATING API (AJAX) ====================

@app.route("/rate/api/next")
@require_login
def rate_api_next():
    mode = request.args.get("mode", "session")
    user_id = session["user"]["id"]

    if mode == "training":
        card = _generate_training_card()
        return jsonify({"ok": True, "card": card})

    # Session mode
    date_range = request.args.get("date", "today")
    unrated_only = request.args.get("unrated", "true") == "true"
    cursor = int(request.args.get("cursor", "0"))

    entries = _parse_history_entries()
    entries = _filter_history_by_date(entries, date_range)
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)  # neueste zuerst

    if unrated_only:
        latest = ratings_by_user_fingerprint()
        rated_fps = {fp for (uid, fp) in latest.keys() if uid == user_id}
        entries = [e for e in entries if class_fingerprint(_history_to_rate_card(e)["class"]) not in rated_fps]

    total = len(entries)
    if total == 0:
        return jsonify({"ok": True, "card": None, "total": 0, "index": 0})

    cursor = max(0, min(cursor, total - 1))
    card = _history_to_rate_card(entries[cursor])
    return jsonify({"ok": True, "card": card, "total": total, "index": cursor})


@app.route("/rate/api/submit", methods=["POST"])
@require_login
@limiter.limit("120/minute")
def rate_api_submit():
    data = request.get_json(silent=True) or {}
    class_data = data.get("class") or {}
    current_score = data.get("current_score")
    judgment = data.get("judgment")
    suggested_score = data.get("suggested_score")
    source = data.get("source", "session")

    if not class_data or current_score is None or judgment not in ("low", "fair", "high"):
        return jsonify({"ok": False, "error": "Invalid payload"}), 400

    user = session["user"]
    record_rating(
        rater_id=user["id"],
        rater_name=user.get("global_name") or user.get("username", ""),
        class_data=class_data,
        current_score=int(current_score),
        judgment=judgment,
        suggested_score=int(suggested_score) if suggested_score is not None else None,
        source=source if source in ("session", "training") else "session",
    )
    return jsonify({"ok": True})


@app.route("/rate/api/stats")
@require_login
def rate_api_stats():
    user_id = session["user"]["id"]
    all_ratings = read_ratings()
    today_str = date.today().isoformat()
    my_today = sum(1 for r in all_ratings if r.get("rater_id") == user_id and r.get("ts", "")[:10] == today_str)
    my_total = sum(1 for r in all_ratings if r.get("rater_id") == user_id)
    return jsonify({"ok": True, "my_today": my_today, "my_total": my_total, "total": len(all_ratings)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
