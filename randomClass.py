# randomClass.py

from random import choice
from collections import defaultdict

# --- Globaler Zähler für ALLE Items (Waffen, Attachments, Perks, etc.) ---
selection_counts_global = defaultdict(int)

class RandomClass:
    def __init__(self):
        # Primärwaffen
        self.assault_rifle_weapons = [
            "FAMAS", "M4A1", "SCAR-H", "TAR-21", "FAL", "M16A4", "ACR", "F2000", "AK-47",
        ]
        self.mp_weapons = [
            "MP5K", "UMP45", "Vector", "P90", "Mini-Uzi",
        ]
        self.lmg_weapons = [
            "L86 LSW", "RPD", "MG4", "AUG HBAR", "M240",
        ]
        self.sniper_weapons = [
            "WA2000", "M21 EBR", "Barrett .50cal", "Intervention",
        ]

        # Sekundärwaffen
        self.pistols_weapons = [
            "USP .45", "M9", "DESERT EAGLE", ".44 MAGNUM",
        ]
        self.auto_pistols_weapons = [
            "PP2000", "G18", "M93 Raffica", "TMP",
        ]
        self.shotgun_weapons = [
            "SPAS-12", "AA-12", "STRIKER", "RANGER", "M1014", "MODEL 1887",
        ]
        self.launchers_weapons = [
            "RPG-7", "AT4-HS", "STINGER", "JAVELIN", "THUMPER",
        ]

        # Aufsätze kategorisiert
        self.assault_rifle_attachments = {
            "No Attachment": "None",
            "Grenade Launcher": "Launcher",
            "Red Dot Sight": "Sight",
            "Silencer": "Silencer",
            "ACOG Scope": "Sight",
            "FMJ": "Ammo",
            "Shotgun": "Shotgun",
            "Holographic Sight": "Sight",
            "Heartbeat Sensor": "Sensor",
            "Thermal": "Sight",  # Von "Sensor" zu "Sight" geändert
            "Extended Mags": "Ammo",
        }

        self.sniper_attachments = {
            "No Attachment": "None",
            "Silencer": "Silencer",
            "ACOG Scope": "Sight",
            "FMJ": "Ammo",
            "Heartbeat Sensor": "Sensor",
            "Thermal": "Sight",  # Von "Sensor" zu "Sight" geändert
            "Extended Mags": "Ammo",
        }

        self.lmg_attachments = {
            "No Attachment": "None",
            "Grip": "Grip",
            "Red Dot Sight": "Sight",
            "Silencer": "Silencer",
            "ACOG Scope": "Sight",
            "FMJ": "Ammo",
            "Holographic Sight": "Sight",
            "Heartbeat Sensor": "Sensor",
            "Thermal": "Sight",  # Von "Sensor" zu "Sight" geändert
            "Extended Mags": "Ammo",
        }

        self.mg_attachments = {
            "No Attachment": "None",
            "Extended Mags": "Ammo",
            "Rapid Fire": "Fire Rate",
            "Red Dot Sight": "Sight",
            "Silencer": "Silencer",
            "ACOG Scope": "Sight",
            "FMJ": "Ammo",
            "Akimbo": "Dual Wield",
            "Holographic Sight": "Sight",
            "Thermal Scope": "Sight",  # Von "Sensor" zu "Sight" geändert
        }

        self.pistols_attachments = {
            "No Attachment": "None",
            "Akimbo": "Dual Wield",
            "Tactical Knife": "Melee",
            "Silencer": "Silencer",
            "FMJ": "Ammo",
        }

        self.auto_pistols_attachments = {
            "No Attachment": "None",
            "Red Dot Sight": "Sight",
            "Akimbo": "Dual Wield",
            "Silencer": "Silencer",
            "FMJ": "Ammo",
            "Extended Mags": "Ammo",
            "Holographic Sight": "Sight",
        }

        self.shotgun_attachments = {
            "No Attachment": "None",
            "Grip": "Grip",
            "Red Dot Sight": "Sight",
            "Silencer": "Silencer",
            "FMJ": "Ammo",
            "Extended Mags": "Ammo",
            "Holographic Sight": "Sight",
        }

        self.shotgun_attachments_akimbo = {
            "Akimbo": "Dual Wield",
            "FMJ": "Ammo",
        }

        # Liste der Sights zur Vereinfachung
        self.sights = ["Holographic Sight", "Red Dot Sight", "ACOG Scope", "Thermal"]

        # Inkompatibilitätsregeln für Aufsätze
        self.incompatible_attachments = {
            "Holographic Sight": ["Akimbo", "Red Dot Sight", "ACOG Scope", "Thermal"],
            "Red Dot Sight": ["Holographic Sight", "ACOG Scope", "Thermal"],
            "Akimbo": ["Holographic Sight", "Red Dot Sight"],
            "Tactical Knife": ["Akimbo"],
            # Weitere Inkompatibilitäten können hier hinzugefügt werden
        }

        # Equipment und Tactical
        self.equipment = [
            "Frag", "Semtex", "Throwing Knife", "Tactical Insertion", "Blast Shield",
            "Claymore", "C4",
        ]

        self.tactical = [
            "Flash Grenade", "Stun Grenade", "Smoke Grenade",
        ]

        # Perks
        self.perk1 = [
            "Marathon", "Sleight of Hand", "Scavenger", "Bling"
        ]
        self.perk2 = [
            "Stopping Power", "Lightweight", "Hardline", "Cold-Blooded", "Danger Close",
        ]
        self.perk3 = [
            "Commando", "Ninja", "SitRep", "Steady Aim", "Last Stand", "Scrambler",
        ]

        # Karten
        self.maps = [
            "Afghan",
            "Derail",
            "Estate",
            "Favela",
            "Highrise",
            "Invasion",
            "Karachi",
            "Quarry",
            "Rundown", 
            "Scrapyard",
            "Skidrow",
            "Sub Base",
            "Terminal",
            "Underpass",
            "Wasteland",
        ]

        # Gesundheitsregeneration
        self.hp_regenration = [
            "Normal",
            "Normal",
            "Normal",
            "Normal",
            "Fast",
            "Fast",
            "Fast",
            "Fast",
            "Slow",
            "Slow",
            "Slow",
            "Slow",
            "None",
        ]

        # Team Damage
        self.team_damage = [
            "Enabled",
            "Reflective",
            "Shared",
            "Without",
        ]

        # (Kein lokaler self.selection_counts mehr nötig, da wir global zählen.)

    # ----------------------------------------------------------------------------------
    # ------------------------------ RANDOM PRIMARY -------------------------------------
    # ----------------------------------------------------------------------------------
    def get_random_primary(self, perk1) -> str:
        weapon_type = choice(["Assault Rifle", "Submachine Gun", "Light Machine Gun", "Sniper Rifle"])

        def select_two_attachments_with_incompatibility(attachment_dict, weapon_type):
            possible_attachments = [att for att in attachment_dict if att != "No Attachment"]
            if not possible_attachments:
                return "No Attachment"

            attempts = 0
            max_attempts = 100

            while attempts < max_attempts:
                first_attachment = choice(possible_attachments)
                first_incompatibles = self.incompatible_attachments.get(first_attachment, [])

                # Waffentyp-spezifische Einschränkungen
                if weapon_type == "Assault Rifle":
                    if first_attachment in self.sights:
                        # Zweites Attachment darf kein weiteres Sight sein
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                            and att not in self.sights
                            and att not in ["Shotgun", "Grenade Launcher"]
                        ]
                        # Zusätzlich darf entweder Grenade Launcher oder Shotgun gewählt werden
                        additional_attachments = [
                            att for att in possible_attachments if att in ["Grenade Launcher", "Shotgun"]
                        ]
                        available_attachments += additional_attachments
                    elif first_attachment == "Grenade Launcher":
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                            and att != "Shotgun"
                        ]
                    elif first_attachment == "Shotgun":
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                            and att != "Grenade Launcher"
                        ]
                    else:
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                        ]

                elif weapon_type == "Submachine Gun":
                    if first_attachment in self.sights:
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                            and att not in self.sights
                            and att != "Akimbo"
                        ]
                    elif first_attachment == "Akimbo":
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                            and att not in self.sights
                        ]
                    else:
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                        ]

                elif weapon_type == "Light Machine Gun":
                    if first_attachment in self.sights:
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                            and att not in self.sights
                        ]
                    else:
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                        ]

                elif weapon_type == "Sniper Rifle":
                    if first_attachment in self.sights:
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                            and att not in self.sights
                        ]
                    else:
                        available_attachments = [
                            att for att in possible_attachments
                            if att != first_attachment
                            and att not in first_incompatibles
                        ]
                else:
                    available_attachments = [
                        att for att in possible_attachments
                        if att != first_attachment
                        and att not in first_incompatibles
                    ]

                if not available_attachments:
                    attempts += 1
                    continue

                second_attachment = choice(available_attachments)

                # Überprüfe einige zusätzliche Regeln
                if first_attachment in self.sights and second_attachment in self.sights:
                    attempts += 1
                    continue
                if (first_attachment in self.sights and second_attachment == "Akimbo") or \
                   (second_attachment in self.sights and first_attachment == "Akimbo"):
                    attempts += 1
                    continue
                if (first_attachment == "Grenade Launcher" and second_attachment == "Shotgun") or \
                   (second_attachment == "Grenade Launcher" and first_attachment == "Shotgun"):
                    attempts += 1
                    continue

                return f"{first_attachment} & {second_attachment}"

            # Fallback
            return first_attachment

        def select_single_attachment(attachment_dict):
            return choice(list(attachment_dict.keys()))

        if weapon_type == "Assault Rifle":
            weapon = choice(self.assault_rifle_weapons)
            attachment_dict = self.assault_rifle_attachments
        elif weapon_type == "Submachine Gun":
            weapon = choice(self.mp_weapons)
            attachment_dict = self.mg_attachments
        elif weapon_type == "Light Machine Gun":
            weapon = choice(self.lmg_weapons)
            attachment_dict = self.lmg_attachments
        elif weapon_type == "Sniper Rifle":
            weapon = choice(self.sniper_weapons)
            attachment_dict = self.sniper_attachments
        else:
            weapon = "Unknown Weapon"
            attachment_dict = {}

        # --- Waffe im globalen Zähler erfassen ---
        if weapon != "Unknown Weapon":
            selection_counts_global[weapon] += 1

        if perk1 == "Bling":
            attachments = select_two_attachments_with_incompatibility(attachment_dict, weapon_type)
            # Jedes Attachment im globalen Zähler erfassen
            for att in attachments.split(" & "):
                selection_counts_global[att.strip()] += 1
            return f"{weapon} with {attachments}"
        else:
            attachment = select_single_attachment(attachment_dict)
            selection_counts_global[attachment] += 1
            return f"{weapon} with {attachment}"

    # ----------------------------------------------------------------------------------
    # ------------------------------ RANDOM SECONDARY -----------------------------------
    # ----------------------------------------------------------------------------------
    def get_random_secondary(self, perk1) -> str:

        def select_two_attachments_secondary(attachment_dict):
            possible_attachments = [att for att in attachment_dict if att != "No Attachment"]
            if not possible_attachments:
                return "No Attachment"

            attempts = 0
            max_attempts = 100

            while attempts < max_attempts:
                first_attachment = choice(possible_attachments)
                first_incompatibles = self.incompatible_attachments.get(first_attachment, [])

                available_attachments = [
                    att for att in possible_attachments
                    if att != first_attachment and att not in first_incompatibles
                ]

                if not available_attachments:
                    attempts += 1
                    continue

                second_attachment = choice(available_attachments)

                # Beispiel: keine Kombination von Sights und Akimbo
                if (first_attachment in self.sights and second_attachment == "Akimbo") or \
                   (second_attachment in self.sights and first_attachment == "Akimbo"):
                    attempts += 1
                    continue

                return f"{first_attachment} & {second_attachment}"

            return first_attachment

        def select_single_attachment_secondary(attachment_dict):
            return choice(list(attachment_dict.keys()))

        weapon_type = choice(["Pistol", "Machine Pistol", "Shotgun", "Launcher"])

        if weapon_type == "Pistol":
            weapon = choice(self.pistols_weapons)
            if weapon == "DESERT EAGLE":
                attachment_dict = {
                    "No Attachment": "None",
                    "Akimbo": "Dual Wield",
                    "Tactical Knife": "Melee",
                    "Silencer": "Silencer",
                    "FMJ": "Ammo",
                }
            elif weapon == ".44 MAGNUM":
                attachment_dict = {
                    "Akimbo": "Dual Wield",
                    "Tactical Knife": "Melee",
                    "FMJ": "Ammo",
                }
            else:
                attachment_dict = self.pistols_attachments
        elif weapon_type == "Machine Pistol":
            weapon = choice(self.auto_pistols_weapons)
            if weapon == "TMP":
                attachment_dict = {
                    "Red Dot Sight": "Sight",
                    "Holographic Sight": "Sight",
                    "Thermal": "Sight",
                    "ACOG": "Sight",
                }
            else:
                attachment_dict = self.auto_pistols_attachments
        elif weapon_type == "Shotgun":
            weapon = choice(self.shotgun_weapons)
            if weapon in ["MODEL 1887", "RANGER"]:
                attachment_dict = self.shotgun_attachments_akimbo
            else:
                attachment_dict = self.shotgun_attachments
        elif weapon_type == "Launcher":
            weapon = choice(self.launchers_weapons)
            # Launcher haben keine Aufsätze -> direkt global zählen + Rückgabe
            selection_counts_global[weapon] += 1
            return weapon
        else:
            weapon = "Unknown Weapon"
            attachment_dict = {}

        # --- Sekundärwaffe im globalen Zähler erfassen ---
        if weapon != "Unknown Weapon":
            selection_counts_global[weapon] += 1

        if weapon_type != "Launcher":
            if perk1 == "Bling":
                attachments = select_two_attachments_secondary(attachment_dict)
                for att in attachments.split(" & "):
                    selection_counts_global[att.strip()] += 1
                return f"{weapon} with {attachments}"
            else:
                attachment = select_single_attachment_secondary(attachment_dict)
                selection_counts_global[attachment] += 1
                return f"{weapon} with {attachment}"
        else:
            return weapon

    # ----------------------------------------------------------------------------------
    # -------------------------- RANDOM EQUIPMENT ETC. ----------------------------------
    # ----------------------------------------------------------------------------------
    def get_random_equipment(self) -> str:
        eq = choice(self.equipment)
        selection_counts_global[eq] += 1
        return eq

    def get_random_special_grenade(self) -> str:
        tac = choice(self.tactical)
        selection_counts_global[tac] += 1
        return tac

    def get_random_perk1(self) -> str:
        p = choice(self.perk1)
        selection_counts_global[p] += 1
        return p

    def get_random_perk2(self) -> str:
        p = choice(self.perk2)
        selection_counts_global[p] += 1
        return p

    def get_random_perk3(self) -> str:
        p = choice(self.perk3)
        selection_counts_global[p] += 1
        return p

    # ----------------------------------------------------------------------------------
    # -------------------------------- RANDOM MAP ---------------------------------------
    # ----------------------------------------------------------------------------------
    def get_random_map(self) -> str:
        m = choice(self.maps)
        selection_counts_global[m] += 1
        return m

    # ----------------------------------------------------------------------------------
    # ------------------------------ RANDOM HP/TEAM DAMAGE ------------------------------
    # ----------------------------------------------------------------------------------
    def get_random_hp(self) -> str:
        hp = choice(self.hp_regenration)
        selection_counts_global[hp] += 1
        return hp

    def get_random_team_damage(self) -> str:
        td = choice(self.team_damage)
        selection_counts_global[td] += 1
        return td

    # ----------------------------------------------------------------------------------
    # ------------------------------ GET RANDOM CLASS -----------------------------------
    # ----------------------------------------------------------------------------------
    def get_random_class(self) -> str:
        perk1 = self.get_random_perk1()
        perk2 = self.get_random_perk2()
        perk3 = self.get_random_perk3()
        primary = self.get_random_primary(perk1)
        secondary = self.get_random_secondary(perk1)
        equipment = self.get_random_equipment()
        special_grenade = self.get_random_special_grenade()
        hp = self.get_random_hp()
        team_damage = self.get_random_team_damage()

        return (
            f"**Primary:** {primary}\n"
            f"**Secondary:** {secondary}\n"
            f"**Equipment:** {equipment}\n"
            f"**Special Grenade:** {special_grenade}\n"
            f"**HP Regeneration:** {hp}\n"
            f"**Team Damage:** {team_damage}\n"
            f"**Perk 1:** {perk1}\n"
            f"**Perk 2:** {perk2}\n"
            f"**Perk 3:** {perk3}"
        )
