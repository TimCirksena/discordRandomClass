from random import choice, randint
from discord import Embed
import randomClass



def get_response(user_input: str)-> str:
    random_class: str = "?random"

    if user_input == random_class:
        return create_random_embed()
    elif user_input == "?map":
        return create_map_embed()
    else:
        return "I am not sure what you are asking for. Try `?random` or `?map`. Du Hurensohn."

def create_random_embed() -> str:
    random_class = randomClass.RandomClass()

    perk1 = random_class.get_random_perk1()
    perk2 = random_class.get_random_perk2()
    perk3 = random_class.get_random_perk3()
    primary = random_class.get_random_primary(perk1)
    primary = primary.replace('&', '\n&').replace('with', '\nwith')
    #primary_attachments = random_class.add_attachments_to_primary(primary, perk1)
    secondary = random_class.get_random_secondary(perk1)
    secondary = secondary.replace('&', '\n&').replace('with', '\nwith')
    equipment = random_class.get_random_equipment()
    special_grenade = random_class.get_random_special_grenade()

    embed = Embed(title='Zufällige Ausrüstung', color=0x3498db)  # Farbe: Blau
    embed.add_field(name='Primary', value=f'||{primary}||', inline=True)
    embed.add_field(name='Secondary', value=f'||{secondary}||', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)  # Platzhalter für die Trennung zwischen den Gruppen
    embed.add_field(name='Equipment', value=equipment, inline=True)
    embed.add_field(name='Special Grenade', value=special_grenade, inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=True)  # Platzhalter für die Trennung zwischen den Gruppen
    embed.add_field(name='Perk 1', value=perk1, inline=True)
    embed.add_field(name='Perk 2', value=perk2, inline=True)
    embed.add_field(name='Perk 3', value=perk3, inline=True)

    return embed

def create_map_embed() -> str:
    random_class = randomClass.RandomClass()
    map = random_class.get_random_map()
    hp = random_class.get_random_hp()
    team = random_class.get_random_team_damage()

    embed = Embed(title='Map Settings', color=0x3498db)  # Farbe: Blau
    embed.add_field(name='Map', value=map, inline=True)
    embed.add_field(name='HP Regeneration', value=f'||{hp}||', inline=True)
    embed.add_field(name='Team Damage', value=f'||{team}||', inline=True)

    return embed