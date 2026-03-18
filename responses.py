# response.py

from discord import Embed
import randomClass
from scoringmodel import calculate_class_score, get_score_breakdown, get_weapon_data, get_secondary_weapon_data, get_primary_category
from playerstats import get_player_stats


user_class_data = {}


# ==================== DEUTSCHE MW2-UEBERSETZUNGEN ====================

GERMAN_USER_IDS = {
    695156653770932274,
    530847300407263233,
    #692306678107996181,
    #424477646555185162,
    #683097369440813056,
    #897036287889006602,
}

TRANSLATIONS_DE = {
    # Perks (Extras)
    "Marathon": "Marathon",
    "Sleight of Hand": "Fingerfertigkeit",
    "Scavenger": "Gelegenheitsjäger",
    "Bling": "Bling",
    "Stopping Power": "Durchschlagskraft",
    "Lightweight": "Leichtgewicht",
    "Hardline": "Hartgesotten",
    "Cold-Blooded": "Kaltblütig",
    "Danger Close": "Sprengmeister",
    "Commando": "Kommando",
    "Ninja": "Ninja",
    "SitRep": "Feindaufklärung",
    "Steady Aim": "Zielsicherheit",
    "Last Stand": "Letztes Gefecht",
    "Scrambler": "Störsender",
    # Aufsätze
    "No Attachment": "Kein Aufsatz",
    "Grenade Launcher": "Granatwerfer",
    "Red Dot Sight": "Rotpunktvisier",
    "Silencer": "Schalldämpfer",
    "ACOG Scope": "ACOG-Zielfernrohr",
    "FMJ": "Vollmantelgeschoss",
    "Shotgun": "Schrotflinte",
    "Holographic Sight": "Holografisches Visier",
    "Heartbeat Sensor": "Herzschlagsensor",
    "Thermal Scope": "Wärmebildvisier",
    "Extended Mags": "Erweitertes Magazin",
    "Grip": "Vordergriff",
    "Rapid Fire": "Schnellfeuer",
    "Akimbo": "Akimbo",
    "Tactical Knife": "Taktisches Messer",
    # Ausrüstung
    "Frag": "Splittergranate",
    "Semtex": "Semtex",
    "Throwing Knife": "Wurfmesser",
    "Blast Shield": "Sprengschutz",
    "Claymore": "Claymore",
    "C4": "C4",
    # Taktisch
    "Flash Grenade": "Blendgranate",
    "Stun Grenade": "Betäubungsgranate",
    "Smoke Grenade": "Rauchgranate",
    # HP Regeneration
    "Fast": "Schnell",
    "Slow": "Langsam",
    "Normal": "Normal",
    "None": "Keine",
    # Team Damage
    "Enabled": "Aktiviert",
    "Reflective": "Reflektiert",
    "Shared": "Geteilt",
    "Without": "Ohne",
}


def _de(text, user_id):
    """Translate a single term to German if user is in GERMAN_USER_IDS."""
    if user_id not in GERMAN_USER_IDS:
        return text
    return TRANSLATIONS_DE.get(text, text)


def _format_weapon(weapon_str, user_id=None):
    """Format weapon string for embed display, translate attachments for German users."""
    if " with " in weapon_str:
        weapon, atts_str = weapon_str.split(" with ", 1)
        atts = [a.strip() for a in atts_str.split(" & ")]
        if user_id and user_id in GERMAN_USER_IDS:
            atts = [TRANSLATIONS_DE.get(a, a) for a in atts]
            return weapon + "\nmit " + "\n& ".join(atts)
        return weapon + "\nwith " + "\n& ".join(atts)
    return weapon_str


def _labels(user_id):
    """Return embed field labels based on user language."""
    if user_id and user_id in GERMAN_USER_IDS:
        return {
            "primary": "⚔️ Primärwaffe",
            "secondary": "🔫 Sekundärwaffe",
            "equipment": "💣 Ausrüstung",
            "special_grenade": "💨 Spezialgranate",
            "perk1": "🟩 Extra 1",
            "perk2": "🟦 Extra 2",
            "perk3": "🟨 Extra 3",
            "score": "📊 Klassen-Score",
            "loading": "🎰 Klasse wird generiert...",
            "perks_loading": "🎰 Extras werden geladen...",
            "equip_loading": "💣 Ausrüstung wird gewürfelt...",
            "weapons_loading": "⚔️ Waffen werden enthüllt...",
        }
    return {
        "primary": "⚔️ Primary",
        "secondary": "🔫 Secondary",
        "equipment": "💣 Equipment",
        "special_grenade": "💨 Special Grenade",
        "perk1": "🟩 Perk 1",
        "perk2": "🟦 Perk 2",
        "perk3": "🟨 Perk 3",
        "score": "📊 Klassen-Score",
        "loading": "🎰 Klasse wird generiert...",
        "perks_loading": "🎰 Perks werden geladen...",
        "equip_loading": "💣 Equipment wird gewürfelt...",
        "weapons_loading": "⚔️ Waffen werden enthüllt...",
    }


# ==================== SCORE TIERS & ANIMATION HELPERS ====================

def get_score_tier(total_score):
    """Returns tier info (color, title, footer) based on score."""
    if total_score > 40:
        return {
            "color": 0xFFD700,
            "title": "⚡ LEGENDARY DROP ⚡",
            "footer": "🔥 Diese Klasse ist OVERPOWERED! 🔥"
        }
    elif total_score < 18:
        return {
            "color": 0x808080,
            "title": "💀 Müll-Klasse 💀",
            "footer": "🗑️ Viel Glück damit... 🗑️"
        }
    else:
        return {
            "color": 0x3498db,
            "title": "🎲 Zufällige Ausrüstung",
            "footer": "Erstellt von Herr Herbert Zufallsklasse"
        }


def create_score_bar(score, max_score=50):
    """Creates a visual score bar for Discord."""
    ratio = max(0, min(1, score / max_score))
    filled = round(ratio * 10)
    empty = 10 - filled
    if score > 40:
        bar = "🟨" * filled + "⬛" * empty
    elif score < 18:
        bar = "🟥" * filled + "⬛" * empty
    else:
        bar = "🟩" * filled + "⬛" * empty
    return bar


def generate_class_data(user_id, min_score=None, max_score=None, excluded_categories=None):
    """Generates random class data with optional filters. Returns (class_data, total_score) or (None, None)."""
    MAX_ATTEMPTS = 50

    for _ in range(MAX_ATTEMPTS):
        r = randomClass.RandomClass()
        perk1 = r.get_random_perk1()
        perk2 = r.get_random_perk2()
        perk3 = r.get_random_perk3()
        primary = r.get_random_primary(perk1, excluded_categories=excluded_categories)
        secondary = r.get_random_secondary(perk1)
        equipment = r.get_random_equipment()
        special_grenade = r.get_random_special_grenade()

        class_data = {
            "perk1": perk1,
            "perk2": perk2,
            "perk3": perk3,
            "primary": primary,
            "secondary": secondary,
            "equipment": equipment,
            "special_grenade": special_grenade
        }
        total_score = calculate_class_score(class_data)

        if min_score is not None and total_score < min_score:
            continue
        if max_score is not None and total_score > max_score:
            continue

        user_class_data[user_id] = class_data
        return class_data, total_score

    return None, None


def create_loading_embed(user_id=None):
    """Creates the initial loading embed with ??? placeholders."""
    L = _labels(user_id)
    embed = Embed(title=L["loading"], color=0x2C2F33)
    embed.add_field(name=L["primary"], value='```\n???\n```', inline=True)
    embed.add_field(name=L["secondary"], value='```\n???\n```', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)
    embed.add_field(name=L["equipment"], value='```\n???\n```', inline=True)
    embed.add_field(name=L["special_grenade"], value='```\n???\n```', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)
    embed.add_field(name=L["perk1"], value='```\n???\n```', inline=True)
    embed.add_field(name=L["perk2"], value='```\n???\n```', inline=True)
    embed.add_field(name=L["perk3"], value='```\n???\n```', inline=True)
    return embed


def create_reveal_embed(class_data, step, total_score=None, user_id=None):
    """
    Creates an embed for a specific animation step.
    Step 1: Perks revealed
    Step 2: + Equipment & Grenade
    Step 3: + Primary & Secondary (spoilered)
    Step 4: Final with score + tier
    """
    L = _labels(user_id)

    if step >= 4 and total_score is not None:
        tier = get_score_tier(total_score)
        title = tier["title"]
        color = tier["color"]
    elif step == 3:
        title = L["weapons_loading"]
        color = 0x2C2F33
    elif step == 2:
        title = L["equip_loading"]
        color = 0x2C2F33
    else:
        title = L["perks_loading"]
        color = 0x2C2F33

    embed = Embed(title=title, color=color)

    # Primary & Secondary
    if step >= 3:
        primary_text = _format_weapon(class_data["primary"], user_id)
        secondary_text = _format_weapon(class_data["secondary"], user_id)
        embed.add_field(name=L["primary"], value=f'||{primary_text}||', inline=True)
        embed.add_field(name=L["secondary"], value=f'||{secondary_text}||', inline=True)
    else:
        embed.add_field(name=L["primary"], value='```\n???\n```', inline=True)
        embed.add_field(name=L["secondary"], value='```\n???\n```', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)

    # Equipment & Special Grenade
    if step >= 2:
        embed.add_field(name=L["equipment"], value=_de(class_data["equipment"], user_id), inline=True)
        embed.add_field(name=L["special_grenade"], value=_de(class_data["special_grenade"], user_id), inline=True)
    else:
        embed.add_field(name=L["equipment"], value='```\n???\n```', inline=True)
        embed.add_field(name=L["special_grenade"], value='```\n???\n```', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)

    # Perks
    if step >= 1:
        embed.add_field(name=L["perk1"], value=_de(class_data["perk1"], user_id), inline=True)
        embed.add_field(name=L["perk2"], value=_de(class_data["perk2"], user_id), inline=True)
        embed.add_field(name=L["perk3"], value=_de(class_data["perk3"], user_id), inline=True)
    else:
        embed.add_field(name=L["perk1"], value='```\n???\n```', inline=True)
        embed.add_field(name=L["perk2"], value='```\n???\n```', inline=True)
        embed.add_field(name=L["perk3"], value='```\n???\n```', inline=True)

    # Score (final step only)
    if step >= 4 and total_score is not None:
        score_bar = create_score_bar(total_score)
        bd = get_score_breakdown(class_data)

        def _sign(v):
            return f"+{v}" if v > 0 else str(v)

        breakdown_line = (
            f"⚔️ {_sign(bd['primary'])}  "
            f"🔫 {_sign(bd['secondary'])}  "
            f"💣 {_sign(bd['equipment'])}  "
            f"💨 {_sign(bd['special_grenade'])}  "
            f"🟩 {_sign(bd['perk1'])}  "
            f"🟦 {_sign(bd['perk2'])}  "
            f"🟨 {_sign(bd['perk3'])}"
        )

        embed.add_field(
            name=L["score"],
            value=f'**{total_score}** / 50\n{score_bar}\n`{breakdown_line}`',
            inline=False
        )
        tier = get_score_tier(total_score)
        if tier.get("footer"):
            embed.set_footer(text=tier["footer"])

    return embed


# =========================================================================

def check_special_perks(user_id: int) -> str:
    if user_id not in user_class_data:
        return ""

    data = user_class_data[user_id]
    special_count = 0

    if data.get("perk1") in ["Marathon", "Sleight of Hand"]:
        special_count += 1
    if data.get("perk2") == "Stopping Power":
        special_count += 1
    if data.get("perk3") == "Ninja":
        special_count += 1

    if special_count >= 2:
        return " 🌡️ Potenielle OP Klasse! 🌡️ "
    return ""


def get_response(user_input: str, user_id: int):
    if user_input in ["?random", "?zufall", "?"]:
        return create_and_store_random_embed(user_id)
    elif user_input == "?map":
        return create_map_embed(user_id)

    if user_input == "?stats":
        return create_stats_embed()

    if user_input.startswith("?change"):
        parts = user_input.split()
        if len(parts) == 1:
            return "Bitte benutze `?change primary` oder `?change secondary`."
        what_to_change = parts[1].lower()
        if what_to_change == "primary":
            return change_primary_embed(user_id)
        elif what_to_change == "secondary":
            return change_secondary_embed(user_id)
        else:
            return "Unbekannter Parameter. Benutze `?change primary` oder `?change secondary`."

    return "Du alter HUNDESOOOOOOOOOOHN schreib doch einfach `?` oder `?zufall`."


def create_and_store_random_embed(user_id: int) -> Embed:
    r = randomClass.RandomClass()
    perk1 = r.get_random_perk1()
    perk2 = r.get_random_perk2()
    perk3 = r.get_random_perk3()
    primary = r.get_random_primary(perk1)
    secondary = r.get_random_secondary(perk1)
    equipment = r.get_random_equipment()
    special_grenade = r.get_random_special_grenade()

    class_data = {
        "perk1": perk1,
        "perk2": perk2,
        "perk3": perk3,
        "primary": primary,
        "secondary": secondary,
        "equipment": equipment,
        "special_grenade": special_grenade
    }
    user_class_data[user_id] = class_data

    return create_random_embed_from_data(class_data, user_id)


def create_random_embed_from_data(class_data: dict, user_id: int) -> Embed:
    L = _labels(user_id)
    primary_text = _format_weapon(class_data["primary"], user_id)
    secondary_text = _format_weapon(class_data["secondary"], user_id)

    total_score = calculate_class_score(class_data)
    tier = get_score_tier(total_score)

    embed = Embed(title=tier["title"], color=tier["color"])
    embed.add_field(name=L["primary"], value=f'||{primary_text}||', inline=True)
    embed.add_field(name=L["secondary"], value=f'||{secondary_text}||', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)

    embed.add_field(name=L["equipment"], value=_de(class_data["equipment"], user_id), inline=True)
    embed.add_field(name=L["special_grenade"], value=_de(class_data["special_grenade"], user_id), inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)

    embed.add_field(name=L["perk1"], value=_de(class_data["perk1"], user_id), inline=True)
    embed.add_field(name=L["perk2"], value=_de(class_data["perk2"], user_id), inline=True)
    embed.add_field(name=L["perk3"], value=_de(class_data["perk3"], user_id), inline=True)

    score_bar = create_score_bar(total_score)
    bd = get_score_breakdown(class_data)

    def _sign(v):
        return f"+{v}" if v > 0 else str(v)

    breakdown_line = (
        f"⚔️ {_sign(bd['primary'])}  "
        f"🔫 {_sign(bd['secondary'])}  "
        f"💣 {_sign(bd['equipment'])}  "
        f"💨 {_sign(bd['special_grenade'])}  "
        f"🟩 {_sign(bd['perk1'])}  "
        f"🟦 {_sign(bd['perk2'])}  "
        f"🟨 {_sign(bd['perk3'])}"
    )

    embed.add_field(name=L["score"], value=f'**{total_score}** / 50\n{score_bar}\n`{breakdown_line}`', inline=False)

    if tier.get("footer"):
        embed.set_footer(text=tier["footer"])

    return embed


def change_primary_embed(user_id: int):
    if user_id not in user_class_data:
        return "Du hast noch keine Klasse generiert. Benutze zuerst `/random`."

    class_data = user_class_data[user_id]
    perk1 = class_data["perk1"]
    r = randomClass.RandomClass()
    new_primary = r.get_random_primary(perk1)
    class_data["primary"] = new_primary
    user_class_data[user_id] = class_data
    return create_random_embed_from_data(class_data, user_id)


def change_secondary_embed(user_id: int):
    if user_id not in user_class_data:
        return "Du hast noch keine Klasse generiert. Benutze zuerst `/random`."

    class_data = user_class_data[user_id]
    perk1 = class_data["perk1"]
    r = randomClass.RandomClass()
    new_secondary = r.get_random_secondary(perk1)
    class_data["secondary"] = new_secondary
    user_class_data[user_id] = class_data
    return create_random_embed_from_data(class_data, user_id)


def create_map_embed(user_id=None, available_maps=None):
    r = randomClass.RandomClass()
    map_ = r.get_random_map(available_maps=available_maps)
    hp = r.get_random_hp()
    team = r.get_random_team_damage()

    embed = Embed(title=f'🗺️ {map_}', color=0x3498db)
    embed.add_field(name='HP Regeneration', value=_de(hp, user_id), inline=True)
    embed.add_field(name='Team Damage', value=_de(team, user_id), inline=True)
    return embed, map_


def _stats_bar(count, max_count):
    """Creates a small visual bar for stats."""
    if max_count == 0:
        return ""
    ratio = count / max_count
    filled = round(ratio * 8)
    empty = 8 - filled
    return "▓" * filled + "░" * empty


def create_stats_embed():
    """
    Zeigt die gerollten Items sortiert nach Kategorie.
    Kompakte Tabelle mit Balken und Medaillen.
    """

    counts = randomClass.selection_counts_global

    rc = randomClass.RandomClass()

    PRIMARY_SET = set(rc.assault_rifle_weapons + rc.mp_weapons + rc.lmg_weapons + rc.sniper_weapons)
    SECONDARY_SET = set(rc.pistols_weapons + rc.auto_pistols_weapons + rc.shotgun_weapons + rc.launchers_weapons)
    EQUIPMENT_SET = set(rc.equipment)
    TACTICAL_SET = set(rc.tactical)
    PERK1_SET = set(rc.perk1)
    PERK2_SET = set(rc.perk2)
    PERK3_SET = set(rc.perk3)

    categories = {
        "⚔️ Primary": [],
        "🔫 Secondary": [],
        "💣 Equipment": [],
        "💨 Taktisch": [],
        "🟩 Perk 1": [],
        "🟦 Perk 2": [],
        "🟨 Perk 3": [],
    }

    for item, count in counts.items():
        if item in PRIMARY_SET:
            categories["⚔️ Primary"].append((item, count))
        elif item in SECONDARY_SET:
            categories["🔫 Secondary"].append((item, count))
        elif item in EQUIPMENT_SET:
            categories["💣 Equipment"].append((item, count))
        elif item in TACTICAL_SET:
            categories["💨 Taktisch"].append((item, count))
        elif item in PERK1_SET:
            categories["🟩 Perk 1"].append((item, count))
        elif item in PERK2_SET:
            categories["🟦 Perk 2"].append((item, count))
        elif item in PERK3_SET:
            categories["🟨 Perk 3"].append((item, count))

    # Gesamtzahl aller Rolls berechnen
    total_rolls = sum(counts.values())

    embed = Embed(
        title='📊 Roll-Statistiken',
        description=f'Insgesamt **{total_rolls}** Items gerollt.',
        color=0xF1C40F
    )

    medals = ["🥇", "🥈", "🥉"]

    for cat, items_in_cat in categories.items():
        if not items_in_cat:
            continue

        items_in_cat.sort(key=lambda x: x[1], reverse=True)
        max_count = items_in_cat[0][1] if items_in_cat else 1

        lines = []
        for i, (name, c) in enumerate(items_in_cat):
            bar = _stats_bar(c, max_count)
            medal = medals[i] if i < 3 else "⬜"
            if i < 3:
                line = f"{medal} `{bar}` **{name}** × {c}"
            else:
                line = f"{medal} `{bar}` {name} × {c}"
            lines.append(line)

        embed.add_field(name=cat, value="\n".join(lines), inline=False)

    if all(len(v) == 0 for v in categories.values()):
        embed.description = "Noch keine Daten vorhanden."

    embed.set_footer(text="Erstellt von Herr Herbert Zufallsklasse")

    return embed


def _format_player_block(label: str, stats: dict) -> str:
    """Format a stats block (session or historical) for the embed."""
    if stats["rolls"] == 0:
        return f"**{label}**\n*Keine Daten*"

    avg = round(stats["total_score"] / stats["rolls"], 1)
    worst = stats["worst_score"] if stats["worst_score"] != 999 else "—"

    # Top 3 Waffen
    weapons = sorted(stats["weapons"].items(), key=lambda x: x[1], reverse=True)[:3]
    top_weapons = ", ".join(f"{w} ({c}×)" for w, c in weapons) if weapons else "—"

    lines = [
        f"**{label}**",
        f"```",
        f"Rolls:        {stats['rolls']}",
        f"Avg Score:    {avg}",
        f"Best:         {stats['best_score']}",
        f"Worst:        {worst}",
        f"Legendary:    {stats['legendary_count']}",
        f"Trash:        {stats['trash_count']}",
        f"```",
        f"Top Waffen: {top_weapons}",
    ]
    return "\n".join(lines)


def create_player_stats_embed(user_id: int, display_name: str) -> Embed:
    """Creates an embed with personal player stats (session + historical)."""
    hist, sess = get_player_stats(user_id)

    embed = Embed(
        title=f"📈 Stats von {display_name}",
        color=0x9B59B6,
    )

    embed.add_field(
        name="🕹️ Session",
        value=_format_player_block("Aktuelle Session", sess),
        inline=False,
    )
    embed.add_field(
        name="📜 Historisch",
        value=_format_player_block("Alle Zeiten", hist),
        inline=False,
    )

    # Fun stats
    if hist["rolls"] > 0:
        legendary_rate = round(hist["legendary_count"] / hist["rolls"] * 100, 1)
        trash_rate = round(hist["trash_count"] / hist["rolls"] * 100, 1)
        embed.add_field(
            name="🎯 Fun Facts",
            value=(
                f"Legendary-Rate: **{legendary_rate}%**\n"
                f"Trash-Rate: **{trash_rate}%**"
            ),
            inline=False,
        )

    embed.set_footer(text="Erstellt von Herr Herbert Zufallsklasse")
    return embed
