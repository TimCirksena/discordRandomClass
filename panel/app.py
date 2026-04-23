import os
import sys
import hmac
import json
import re
import subprocess
import logging
from datetime import datetime, date, timedelta, timezone
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")

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
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")
ADMIN_DISCORD_ID = os.getenv("ADMIN_DISCORD_ID", "")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-secret-change-me")

# Pfade: Panel liegt in <repo>/panel/app.py, Bot-Stats unter <repo>/stats/
REPO_ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = REPO_ROOT / "stats"

# Bot-Module für History-Reader importierbar machen
sys.path.insert(0, str(REPO_ROOT))
from playerstats import (  # noqa: E402
    read_history,
    get_all_players_historical,
    record_rating,
    read_ratings,
    ratings_by_user_fingerprint,
    class_fingerprint,
    record_haudentim_score,
    haudentim_leaderboard,
    haudentim_user_best,
    record_crawler_score,
    crawler_leaderboard,
    crawler_user_best,
)
import randomClass as rc_module  # noqa: E402
from scoringmodel import calculate_class_score, get_score_breakdown  # noqa: E402
import scoringmodel as sm  # noqa: E402

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
    client_kwargs={"scope": "identify guilds"},
)


def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            # Fuer JSON/AJAX-Endpoints: 401 statt Redirect
            if request.path.startswith("/rate/api") or request.accept_mimetypes.best == "application/json":
                return jsonify({"ok": False, "error": "not logged in"}), 401
            return redirect(url_for("login_page", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login_page", next=request.path))
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


@app.context_processor
def inject_bot_status():
    # Fuer die Navbar-Anzeige; JS aktualisiert spaeter live.
    try:
        return {"nav_bot_status": bot_status()}
    except Exception:
        return {"nav_bot_status": "unknown"}

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
            dt = datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc).astimezone(BERLIN_TZ)
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


def _date_range_bounds(date_range: str):
    """Gibt (date_from, date_to) als date oder None zurück. None = unbegrenzt."""
    today = date.today()
    if date_range == "today":
        return today, today
    if date_range == "yesterday":
        y = today - timedelta(days=1)
        return y, y
    if date_range == "7days":
        return today - timedelta(days=7), today
    if date_range == "30days":
        return today - timedelta(days=30), today
    return None, None


def build_stats_context(user_filter: str = "", date_range: str = "all"):
    date_from, date_to = _date_range_bounds(date_range)

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
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Datumsfilter fuer History
                if date_from is not None:
                    ts_date_str = entry.get("ts", "")[:10]
                    if not ts_date_str:
                        continue
                    if ts_date_str < date_from.isoformat() or ts_date_str > date_to.isoformat():
                        continue
                full_history.append(entry)

    # Leaderboard + Aggregat-Daten aus Daily Stats, mit Datumsfilter
    players_raw = get_all_players_historical(date_from=date_from, date_to=date_to)
    # Optionen-Dropdown (immer alle User, nicht gefiltert, damit Wechsel moeglich bleibt)
    players_all = get_all_players_historical()

    # User-Liste für Dropdown (immer all-time, damit Wechsel jederzeit möglich)
    user_options = sorted(
        [
            {"id": uid, "name": s.get("name") or f"User {uid[-4:]}", "rolls": s.get("rolls", 0)}
            for uid, s in players_all.items()
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

    # Für Aggregationen nur Initial-Rolls zählen (Rerolls würden sonst doppelt zählen).
    rolls_only = [e for e in filtered_history if e.get("event", "roll") != "reroll"]

    total_rolls_daily = sum(p.get("rolls", 0) for p in filtered_players.values())
    total_rolls = max(len(rolls_only), total_rolls_daily)

    # Primary / Secondary Aggregate
    if rolls_only:
        primary_counts = {}
        secondary_counts = {}
        for e in rolls_only:
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
    top_perk1 = aggregate_counts(rolls_only, "perk1")
    top_perk2 = aggregate_counts(rolls_only, "perk2")
    top_perk3 = aggregate_counts(rolls_only, "perk3")
    top_equip = aggregate_counts(rolls_only, "equipment")
    top_grenade = aggregate_counts(rolls_only, "special_grenade")

    leaderboard = []
    for uid, stats in filtered_players.items():
        rolls = stats.get("rolls", 0)
        if rolls == 0:
            continue
        avg = stats.get("total_score", 0) / rolls
        worst = stats.get("worst_score", 999)
        rerolls = stats.get("rerolls", 0)
        reroll_rate = round(rerolls / rolls * 100, 1) if rolls else 0.0
        leaderboard.append({
            "id": uid,
            "name": stats.get("name") or f"User {uid[-4:]}",
            "rolls": rolls,
            "avg": round(avg, 1),
            "best": stats.get("best_score", 0),
            "worst": worst if worst != 999 else 0,
            "legendary": stats.get("legendary_count", 0),
            "trash": stats.get("trash_count", 0),
            "rerolls": rerolls,
            "reroll_rate": reroll_rate,
            "reroll_breakdown": stats.get("reroll_breakdown", {}),
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
        "date_range": date_range,
    }


@app.route("/")
@require_login
def index():
    return render_template("index.html", status=bot_status(), logs=bot_logs())


@app.route("/stats")
@require_login
def stats_page():
    user_filter = request.args.get("user", "").strip()
    date_range = request.args.get("date", "all").strip() or "all"
    if date_range not in ("today", "yesterday", "7days", "30days", "all"):
        date_range = "all"
    # Default auf eingeloggten User wenn kein Filter gesetzt
    if user_filter == "" and "user" not in request.args:
        user_filter = session["user"]["id"]
    ctx = build_stats_context(user_filter=user_filter, date_range=date_range)
    return render_template("stats.html", **ctx)


@app.route("/status")
@require_login
@limiter.limit("60/minute")
def status():
    return jsonify({"status": bot_status(), "logs": bot_logs()})


@app.route("/action", methods=["POST"])
@require_login
@limiter.limit("10/minute;30/hour")
def action():
    ip = client_ip()
    user = session["user"]
    act = request.form.get("action")
    log.info(f"{(act or 'UNKNOWN').upper()} from {user.get('global_name')} ({user.get('id')}) ip={ip}")
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

@app.route("/login")
def login_page():
    if "user" in session:
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/access-denied")
def access_denied():
    return render_template("access_denied.html"), 403


@app.route("/auth/login")
def auth_login():
    next_path = request.args.get("next", "/")
    session["next_url"] = next_path
    redirect_uri = url_for("auth_callback", _external=True, _scheme="https")
    return oauth.discord.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    try:
        token = oauth.discord.authorize_access_token()
        user = oauth.discord.get("users/@me", token=token).json()
    except Exception as e:
        log.warning(f"OAuth callback failed: {e}")
        return render_template("auth_error.html"), 400

    # Guild-Membership prüfen
    try:
        guilds = oauth.discord.get("users/@me/guilds", token=token).json()
    except Exception as e:
        log.warning(f"Guild fetch failed for {user.get('username')}: {e}")
        guilds = []

    guild_ids = {g.get("id") for g in guilds if isinstance(g, dict)}
    if DISCORD_GUILD_ID and DISCORD_GUILD_ID not in guild_ids:
        log.warning(f"Access denied for {user.get('username')} ({user.get('id')}): not in guild {DISCORD_GUILD_ID}")
        session.pop("user", None)
        return redirect(url_for("access_denied"))

    session["user"] = {
        "id": str(user.get("id", "")),
        "username": user.get("username", ""),
        "global_name": user.get("global_name") or user.get("username", ""),
        "avatar": user.get("avatar"),
    }
    log.info(f"Login OK: {session['user']['global_name']} ({session['user']['id']})")
    next_url = session.pop("next_url", "/")
    return redirect(next_url)


@app.route("/auth/logout")
def auth_logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))


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
        "breakdown": get_score_breakdown(class_data),
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
        "breakdown": get_score_breakdown(class_data),
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


JUDGMENT_VALUE = {"low": +1, "fair": 0, "high": -1}
JUDGMENT_STEP = 2     # fixer Delta-Betrag für Quick-Button-Ratings ohne Slider
SLIDER_WEIGHT = 2.0   # Slider-Ratings zaehlen doppelt ggü. Quick-Buttons
BUTTON_WEIGHT = 1.0
MIN_SAMPLES_DEFAULT = 3


def _implied_delta(rating: dict):
    """Gibt (delta, weight) fuer ein Rating zurueck. Slider-Ratings gewichtet staerker."""
    if rating.get("suggested_score") is not None:
        return rating["suggested_score"] - rating["current_score"], SLIDER_WEIGHT
    j = rating.get("judgment", "fair")
    step = {"low": +JUDGMENT_STEP, "fair": 0, "high": -JUDGMENT_STEP}.get(j, 0)
    return step, BUTTON_WEIGHT


def _lookup_current_value(category: str, name: str):
    """Aktueller Score-Wert aus scoringmodel fuer eine Komponente. None wenn unbekannt."""
    if not name:
        return None
    if category == "Primary":
        for wdict in (sm.ar_data, sm.smg_data, sm.lmg_data, sm.sniper_data, sm.riot_shield_data):
            if name in wdict:
                return wdict[name].get("base")
    elif category == "Secondary":
        for wdict in (sm.pistol_secondary_data, sm.mp_secondary_data, sm.shotgun_secondary_data, sm.launcher_secondary_data):
            if name in wdict:
                return wdict[name].get("base")
    elif category == "Equipment":
        return sm.equipment_scores.get(name)
    elif category == "Grenade":
        return sm.special_grenade_scores.get(name)
    elif category.startswith("Perk"):
        # Perk-Modifier sind kategorie-abhaengig (AR/SMG/LMG/Sniper). Zeige AR-Wert als Referenz.
        return sm.ar_perk_modifiers.get(name)
    return None


def _count_history_occurrences() -> dict:
    """Zaehlt pro (category, name) wie viele History-Rolls die Komponente enthalten."""
    counts: dict[tuple[str, str], int] = {}
    history_file = STATS_DIR / "history.jsonl"
    if not history_file.exists():
        return counts
    with open(history_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            pw = weapon_base(e.get("primary", ""))
            sw = weapon_base(e.get("secondary", ""))
            for key in (
                ("Primary", pw),
                ("Secondary", sw),
                ("Equipment", e.get("equipment", "")),
                ("Grenade", e.get("special_grenade", "")),
                ("Perk1", e.get("perk1", "")),
                ("Perk2", e.get("perk2", "")),
                ("Perk3", e.get("perk3", "")),
            ):
                if key[1]:
                    counts[key] = counts.get(key, 0) + 1
    return counts


@app.route("/rate/analysis")
@require_login
def rate_analysis():
    show_all = request.args.get("all") == "1"
    min_samples = 1 if show_all else MIN_SAMPLES_DEFAULT

    latest = ratings_by_user_fingerprint()
    ratings = list(latest.values())

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
        b = by_component.setdefault(key, {"count": 0, "judgment_sum": 0, "deltas": [], "weights": []})
        b["count"] += 1
        b["judgment_sum"] += JUDGMENT_VALUE.get(r.get("judgment", "fair"), 0)
        delta, weight = _implied_delta(r)
        b["deltas"].append(delta)
        b["weights"].append(weight)

    for r in ratings:
        cd = r.get("class", {})
        _add("Primary", _primary_weapon(cd), r)
        _add("Secondary", _secondary_weapon(cd), r)
        _add("Equipment", cd.get("equipment", ""), r)
        _add("Grenade", cd.get("special_grenade", ""), r)
        _add("Perk1", cd.get("perk1", ""), r)
        _add("Perk2", cd.get("perk2", ""), r)
        _add("Perk3", cd.get("perk3", ""), r)

    history_counts = _count_history_occurrences()

    rows = []
    for (cat, name), b in by_component.items():
        count = b["count"]
        if count < min_samples:
            continue
        avg_judgment = b["judgment_sum"] / count if count else 0.0
        total_weight = sum(b["weights"])
        weighted_delta = (
            sum(d * w for d, w in zip(b["deltas"], b["weights"])) / total_weight
            if total_weight else 0.0
        )
        # Standardabweichung der rohen Deltas (Konsens)
        if len(b["deltas"]) > 1:
            mean_d = sum(b["deltas"]) / len(b["deltas"])
            variance = sum((d - mean_d) ** 2 for d in b["deltas"]) / len(b["deltas"])
            stddev = variance ** 0.5
        else:
            stddev = 0.0
        confidence = min(count / 10.0, 1.0)

        current = _lookup_current_value(cat, name)
        if current is not None:
            suggested = current + round(weighted_delta)
            diff = suggested - current
        else:
            suggested = None
            diff = None

        rolls_affected = history_counts.get((cat, name), 0)
        rows.append({
            "category": cat,
            "name": name,
            "count": count,
            "avg_judgment": round(avg_judgment, 2),
            "weighted_delta": round(weighted_delta, 1),
            "current": current,
            "suggested": suggested,
            "diff": diff,
            "confidence": round(confidence, 2),
            "confidence_bar": int(round(confidence * 5)),  # 0-5 Balken
            "stddev": round(stddev, 2),
            "rolls_affected": rolls_affected,
            "bias": "zu hoch" if avg_judgment < -0.25 else ("zu niedrig" if avg_judgment > 0.25 else "passt"),
        })

    # Sortierung nach Actionability (|weighted_delta| * confidence)
    rows.sort(key=lambda x: abs(x["weighted_delta"]) * x["confidence"], reverse=True)

    return render_template(
        "rate_analysis.html",
        rows=rows,
        total_ratings=len(ratings),
        show_all=show_all,
        min_samples=min_samples,
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


# ==================== HAU DEN TIM (Minigame) ====================

@app.route("/haudentim")
@require_login
def haudentim_page():
    return render_template("haudentim.html")


@app.route("/haudentim/api/submit", methods=["POST"])
@require_login
@limiter.limit("30/minute")
def haudentim_submit():
    data = request.get_json(silent=True) or {}
    try:
        time_ms = int(data.get("time_ms", 0))
        clicks = int(data.get("clicks", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    # Anti-Cheat: offensichtliche Manipulation filtern
    if time_ms < 800:
        return jsonify({"ok": False, "error": "zu schnell um echt zu sein"}), 400
    if time_ms > 120000:
        return jsonify({"ok": False, "error": "zu lang (AFK?)"}), 400
    if clicks < 10 or clicks > 500:
        return jsonify({"ok": False, "error": "klick-zahl unrealistisch"}), 400
    # Mehr als 20 klicks/sec sustained ist nicht menschlich
    if clicks / (time_ms / 1000.0) > 20:
        return jsonify({"ok": False, "error": "zu schnell geklickt"}), 400

    user = session["user"]
    name = user.get("global_name") or user.get("username", "") or ""
    record_haudentim_score(user["id"], name, time_ms, clicks)
    log.info(f"HAUDENTIM {name} ({user['id']}): {time_ms}ms in {clicks} clicks")
    return jsonify({"ok": True})


@app.route("/haudentim/api/leaderboard")
@require_login
def haudentim_api_leaderboard():
    top = haudentim_leaderboard(limit=20)
    me = haudentim_user_best(session["user"]["id"])
    my_rank = None
    if me is not None:
        for i, row in enumerate(top, start=1):
            if row.get("user_id") == me.get("user_id"):
                my_rank = i
                break
    return jsonify({"ok": True, "top": top, "me": me, "my_rank": my_rank})


# ==================== CRAWLER (Boss-Kampf-Game) ====================

@app.route("/crawler")
@require_login
def crawler_page():
    return render_template("crawler.html")


@app.route("/crawler/api/submit", methods=["POST"])
@require_login
@limiter.limit("30/minute")
def crawler_submit():
    data = request.get_json(silent=True) or {}
    try:
        time_ms = int(data.get("time_ms", 0))
        won = bool(data.get("won", False))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    if won:
        if time_ms < 5000 or time_ms > 600000:
            return jsonify({"ok": False, "error": "unrealistische Zeit"}), 400
    user = session["user"]
    name = user.get("global_name") or user.get("username", "") or ""
    record_crawler_score(user["id"], name, time_ms, won)
    log.info(f"CRAWLER {name} ({user['id']}): {time_ms}ms won={won}")
    return jsonify({"ok": True})


@app.route("/crawler/api/leaderboard")
@require_login
def crawler_api_leaderboard():
    top = crawler_leaderboard(limit=20)
    me = crawler_user_best(session["user"]["id"])
    my_rank = None
    if me is not None:
        for i, row in enumerate(top, start=1):
            if row.get("user_id") == me.get("user_id"):
                my_rank = i
                break
    return jsonify({"ok": True, "top": top, "me": me, "my_rank": my_rank})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
