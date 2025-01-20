# response.py

from discord import Embed
import randomClass

# Wir brauchen Zugriff auf randomClass.selection_counts_global
# => import randomClass
# => counts = randomClass.selection_counts_global

# Globale Nutzerdaten existieren hier ggf. schon, 
# falls du `user_class_data` hast (siehe altes Beispiel).
user_class_data = {}

def get_response(user_input: str, user_id: int):
    if user_input in ["?random", "?zufall", "?"]:
        return create_and_store_random_embed(user_id)
    elif user_input == "?map":
        return create_map_embed()

    # Neue Funktion: ?stats
    if user_input == "?stats":
        return create_stats_embed()

    if user_input.startswith("?change"):
        # ... (existing logic für !change primary / !change secondary)
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

    return "I am not sure what you are asking for. Try `?random` or `?map`. Du Hurensohn."

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

    return create_random_embed_from_data(class_data)

def create_random_embed_from_data(class_data: dict) -> Embed:
    primary_text = class_data["primary"].replace('&', '\n&').replace('with', '\nwith')
    secondary_text = class_data["secondary"].replace('&', '\n&').replace('with', '\nwith')

    embed = Embed(title='Zufällige Ausrüstung', color=0x3498db)
    embed.add_field(name='Primary', value=f'||{primary_text}||', inline=True)
    embed.add_field(name='Secondary', value=f'||{secondary_text}||', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)

    embed.add_field(name='Equipment', value=class_data["equipment"], inline=True)
    embed.add_field(name='Special Grenade', value=class_data["special_grenade"], inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)

    embed.add_field(name='Perk 1', value=class_data["perk1"], inline=True)
    embed.add_field(name='Perk 2', value=class_data["perk2"], inline=True)
    embed.add_field(name='Perk 3', value=class_data["perk3"], inline=True)

    return embed

def change_primary_embed(user_id: int):
    if user_id not in user_class_data:
        return "Du hast noch keine Klasse generiert. Benutze zuerst `?random`."

    class_data = user_class_data[user_id]
    perk1 = class_data["perk1"]
    r = randomClass.RandomClass()
    new_primary = r.get_random_primary(perk1)
    class_data["primary"] = new_primary
    user_class_data[user_id] = class_data
    return create_random_embed_from_data(class_data)

def change_secondary_embed(user_id: int):
    if user_id not in user_class_data:
        return "Du hast noch keine Klasse generiert. Benutze zuerst `?random`."

    class_data = user_class_data[user_id]
    perk1 = class_data["perk1"]
    r = randomClass.RandomClass()
    new_secondary = r.get_random_secondary(perk1)
    class_data["secondary"] = new_secondary
    user_class_data[user_id] = class_data
    return create_random_embed_from_data(class_data)

def create_map_embed() -> Embed:
    r = randomClass.RandomClass()
    map_ = r.get_random_map()
    hp = r.get_random_hp()
    team = r.get_random_team_damage()

    embed = Embed(title='Map Settings', color=0x3498db)
    embed.add_field(name='Map', value=map_, inline=True)
    embed.add_field(name='HP Regeneration', value=f'||{hp}||', inline=True)
    embed.add_field(name='Team Damage', value=f'||{team}||', inline=True)
    return embed

from discord import Embed
import randomClass

def create_stats_embed():
    """
    Zeigt die gerollten Items sortiert nach Kategorie (Primary, Secondary, etc.).
    Innerhalb jeder Kategorie werden die Items nach Häufigkeit absteigend gelistet.
    Die Top 3 jeder Kategorie werden farblich hervorgehoben.
    """

    counts = randomClass.selection_counts_global

    # Instanz erstellen, um an die Listen/Arrays von RandomClass zu kommen:
    rc = randomClass.RandomClass()

    # Kategorien als Sets (für schnelles "in"-Prüfen)
    PRIMARY_SET = set(rc.assault_rifle_weapons + rc.mp_weapons + rc.lmg_weapons + rc.sniper_weapons)
    SECONDARY_SET = set(rc.pistols_weapons + rc.auto_pistols_weapons + rc.shotgun_weapons + rc.launchers_weapons)
    EQUIPMENT_SET = set(rc.equipment)
    TACTICAL_SET = set(rc.tactical)
    PERK1_SET = set(rc.perk1)
    PERK2_SET = set(rc.perk2)
    PERK3_SET = set(rc.perk3)

    # Dictionary zum Sammeln nach Kategorie
    categories = {
        "Primary": [],
        "Secondary": [],
        "Equipment": [],
        "Special Grenade": [],
        "Perk 1": [],
        "Perk 2": [],
        "Perk 3": [],
        "Misc": []
    }

    # Zuordnung jedes Items in die passende Kategorie
    for item, count in counts.items():
        if item in PRIMARY_SET:
            categories["Primary"].append((item, count))
        elif item in SECONDARY_SET:
            categories["Secondary"].append((item, count))
        elif item in EQUIPMENT_SET:
            categories["Equipment"].append((item, count))
        elif item in TACTICAL_SET:
            categories["Special Grenade"].append((item, count))
        elif item in PERK1_SET:
            categories["Perk 1"].append((item, count))
        elif item in PERK2_SET:
            categories["Perk 2"].append((item, count))
        elif item in PERK3_SET:
            categories["Perk 3"].append((item, count))
        else:
            categories["Misc"].append((item, count))

    # Reihenfolge der Kategorien
    category_order = [
        "Primary",
        "Secondary",
        "Equipment",
        "Special Grenade",
        "Perk 1",
        "Perk 2",
        "Perk 3",
        "Misc"
    ]

    # Erstelle das Embed mit einer goldenen Farbe
    embed = Embed(
        title='Statistiken (gerollte Items)',
        description='Hier siehst du, welche Items am häufigsten gerollt wurden.',
        color=0xF1C40F  # Gold
    )

    # Optional: Thumbnail oder Author hinzufügen
    # embed.set_thumbnail(url="https://example.com/ein_schickes_Bild.png")
    # embed.set_author(name="Dein Bot", icon_url="https://example.com/bot_icon.png")

    # Kategorien durchgehen und sortierte Items einfügen
    for cat in category_order:
        items_in_cat = categories[cat]
        if not items_in_cat:
            # Keine Items in dieser Kategorie -> überspringen
            continue

        # Sortieren nach Häufigkeit absteigend
        items_in_cat.sort(key=lambda x: x[1], reverse=True)

        lines = []
        for i, (name, c) in enumerate(items_in_cat, start=1):
            # Top 3 mit Pokal-Emojis hervorheben
            if i == 1:
                line = f":first_place: **{name}** - {c}×"
            elif i == 2:
                line = f":second_place: **{name}** - {c}×"
            elif i == 3:
                line = f":third_place: **{name}** - {c}×"
            else:
                line = f"{i}. {name} - {c}×"
            lines.append(line)

        # Feld hinzufügen
        embed.add_field(name=cat, value="\n".join(lines), inline=False)

    # Falls ALLE Kategorien leer sind
    if all(len(categories[cat]) == 0 for cat in category_order):
        embed.description = "Noch keine Daten vorhanden."

    # Footer für kleine Extra-Info
    embed.set_footer(text="Erstellt von deinem Herr Herbert Zufallsklasse")

    return embed
