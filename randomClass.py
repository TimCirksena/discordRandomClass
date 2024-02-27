from random import choice


class RandomClass:
    def __init__(self):
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
        
        self.assault_rifle_attachments = [
            "No Attachment", "Grenade Launcher", "Red Dot Sight", "Silencer",
            "ACOG Scope", "FMJ", "Shotgun", "Holographic Sight",
            "Heartbeat Sensor", "Thermal", "Extended Mags",
        ]
        
        self.sniper_attachments = [
            "No Attachment", "Silencer", "ACOG Scope", "FMJ",
            "Heartbeat Sensor", "Thermal", "Extended Mags",
        ]
        
        self.lmg_attachments = [
            "No Attachment", "Grip", "Red Dot Sight", "Silencer", "ACOG Scope",
            "FMJ", "Holographic Sight", "Heartbeat Sensor", "Thermal",
            "Extended Mags",
        ]
        
        self.mg_attachments = [
            "No Attachment", "Extended Mags", "Rapid Fire", "Red Dot Sight", "Silencer",
            "ACOG Scope", "FMJ", "Akimbo", "Holographic Sight",
            "Thermal Scope", "Extended Magazines",
        ]
        
        self.pistols_weapons = [
            "USP .45", "M9", "DESERT EAGLE", ".44 MAGNUM",
        ]

        self.pistols_attachments = [
            "No Attachment", "Akimbo", "Tactical Knife", "Silencer", "FMJ",
            "Extended Mags",
        ]
        
        self.auto_pistols_weapons = [
            "PP2000", "G18", "M93 Raffica", "TMP",
        ]

        self.auto_pistols_attachments = [
            "No Attachment", "Red Dot Sight", "Akimbo", "Silencer", "FMJ",
            "Extended Mags", "Holographic Sight",
        ]
        
        self.shotgun_weapons = [
            "SPAS-12", "AA-12", "STRIKER", "RANGER", "M1014", "MODEL 1887",
        ]

        self.shotgun_attachments = [
            "No Attachment", "Grip", "Red Dot Sight", "Silencer", "FMJ",
            "Extended Mags", "holographic Sight",
        ]

        self.shotgun_attachments_akimbo = [
            "Akimbo", "FMJ",
        ]   
        
        self.launchers_weapons = [
            "RPG-7", "AT4-HS", "STINGER", "JAVELIN", "THUMPER", "M203",
        ]
        
        self.equipment = [
            "Frag", "Semtex", "Throwing Knife", "Tactical Insertion", "Blast Shield",
            "Claymore", "C4",
        ]
        
        self.tactical = [
            "Flash Grenade", "Stun Grenade", "Smoke Grenade",
        ]
        
        self.perk1 = [
            "Marathon", "Sleight of Hand", "Scavenger", "Bling", "One Man Army",
        ]
        
        self.perk2 = [
            "Stopping Power", "Lightweight", "Hardline", "Cold-Blooded", "Danger Close",
        ]
        
        self.perk3 = [
            "Commando", "Ninja", "SitRep", "Steady Aim", "Last Stand", "Scrambler",
        ]

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

        self.team_damage = [
        "Enabled",
        "Refelctive",
        "Shared",
        "Without",
        ]

    def get_random_primary(self, perk1) -> str:
        weapon_type = choice(["Assault Rifle", "Submachine Gun", "Light Machine Gun", "Sniper Rifle"])
        
        def get_unique_attachment(attachment_list, previous_attachment):
            attachment = choice(attachment_list)
            while attachment == previous_attachment:
                attachment = choice(attachment_list)
            return attachment
        
        if weapon_type == "Assault Rifle":
            weapon = choice(self.assault_rifle_weapons)
            attachment = choice(self.assault_rifle_attachments)
            if perk1 == "Bling":
                attachment2 = get_unique_attachment(self.assault_rifle_attachments, attachment)
                return f"{weapon} with {attachment} & {attachment2}"
            return f"{weapon} with {attachment}"
        
        elif weapon_type == "Submachine Gun":
            weapon = choice(self.mp_weapons)
            attachment = choice(self.mg_attachments)
            if perk1 == "Bling":
                attachment2 = get_unique_attachment(self.mg_attachments, attachment)                
                return f"{weapon} with {attachment} & {attachment2}"
            
            return f"{weapon} with {attachment}"
        
        elif weapon_type == "Light Machine Gun":
            weapon = choice(self.lmg_weapons)
            attachment = choice(self.lmg_attachments)
            if perk1 == "Bling":
               attachment2 = get_unique_attachment(self.lmg_attachments, attachment)
               return f"{weapon} with {attachment} & {attachment2}"
            return f"{weapon} with {attachment}"
        
        elif weapon_type == "Sniper Rifle":
            weapon = choice(self.sniper_weapons)
            attachment = choice(self.sniper_attachments)
            if perk1 == "Bling":
                attachment2 = get_unique_attachment(self.sniper_attachments, attachment)
                return f"{weapon} with {attachment} & {attachment2}"
            return f"{weapon} with {attachment}"
        
    def get_random_secondary(self, perk1) -> str:

        if perk1 == "One Man Army":
            return "No Secondary"
        
        def get_unique_attachment(attachment_list, previous_attachment):
            attachment = choice(attachment_list)
            while attachment == previous_attachment:
                attachment = choice(attachment_list)
            return attachment
        
        weapon_type = choice(["Pistol", "Machine Pistol", "Shotgun", "Launcher"])

        if weapon_type == "Pistol":
            weapon = choice(self.pistols_weapons)
            attachment = choice(self.pistols_attachments)
            if perk1 == "Bling":
                attachment2 = get_unique_attachment(self.pistols_attachments, attachment)
                return f"{weapon} with {attachment} & {attachment2}"
            return f"{weapon} with {attachment}"
        
        elif weapon_type == "Machine Pistol":
            weapon = choice(self.auto_pistols_weapons)
            attachment = choice(self.auto_pistols_attachments)
            if perk1 == "Bling":
                attachment2 = get_unique_attachment(self.auto_pistols_attachments, attachment)
                return f"{weapon} with {attachment} & {attachment2}"
            return f"{weapon} with {attachment}"
        
        elif weapon_type == "Shotgun":
            weapon = choice(self.shotgun_weapons)
            if weapon == "MODEL 1887" or weapon == "RANGER":
                attachment = choice(self.shotgun_attachments_akimbo)
            else:
                attachment = choice(self.shotgun_attachments)
            if perk1 == "Bling":
                if weapon == "MODEL 1887" or weapon == "RANGER":
                    attachment2 = choice(self.shotgun_attachments_akimbo)
                    return f"{weapon} with {attachment} & {attachment2}"
                else:
                    attachment2 = get_unique_attachment(self.shotgun_attachments, attachment)
                    return f"{weapon} with {attachment} & {attachment2}"
            return f"{weapon} with {attachment}"
        
        elif weapon_type == "Launcher":
            weapon = choice(self.launchers_weapons)
            return weapon
        
    def get_random_equipment(self) -> str:
        return choice(self.equipment)
    
    def get_random_special_grenade(self) -> str:
        return choice(self.tactical)
    
    def get_random_perk1(self) -> str:
        return choice(self.perk1)
    
    def get_random_perk2(self) -> str:
        return choice(self.perk2)
    
    def get_random_perk3(self) -> str:
        return choice(self.perk3)
    
    def get_random_map(self) -> str:
        return choice(self.maps)
    def get_random_hp(self) -> str:
        return choice(self.hp_regenration)
    def get_random_team_damage(self) -> str:
        return choice(self.team_damage)

    def get_random_class(self) -> str:
        perk1 = self.get_random_perk1()
        perk2 = self.get_random_perk2()
        perk3 = self.get_random_perk3()
        primary = self.get_random_primary(perk1)
        #primary_attachments = self.add_attachments_to_primary(primary, perk1)
        secondary = self.get_random_secondary()
        equipment = self.get_random_equipment()
        special_grenade = self.get_random_special_grenade()
       
        
        return f"Primary: {primary}\nSecondary: {secondary}\nEquipment: {equipment}\nSpecial Grenade: {special_grenade}\nPerk 1: {perk1}\nPerk 2: {perk2}\nPerk 3: {perk3}"