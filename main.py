from typing import Final
import os
import asyncio
from dotenv import load_dotenv
import discord
from discord import Intents, Client, Message, app_commands
from responses import (
    generate_class_data, create_loading_embed, create_reveal_embed,
    get_score_tier, create_map_embed, create_stats_embed,
    change_primary_embed, change_secondary_embed, create_player_stats_embed,
    user_class_data,
)
from scoringmodel import calculate_class_score
import randomClass
from playerstats import record_roll, reset_session
from voice import speak_in_channel

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
ADMIN_ID: Final[int] = 424477646555185162
ROAST_TARGET_ID: Final[int] = 683097369440813056
FILTER_IDS: Final[set] = {
    ADMIN_ID,
    695156653770932274,
    530847300407263233,
}

intents: Intents = Intents.default()
intents.message_content = True
intents.voice_states = True
client: Client = Client(intents=intents)
tree = app_commands.CommandTree(client)


# ==================== REROLL VIEW ====================

class ClassRollView(discord.ui.View):
    def __init__(self, owner_id: int, class_data: dict):
        super().__init__(timeout=300)  # 5 Minuten
        self.owner_id = owner_id
        self.class_data = class_data
        self.rc = randomClass.RandomClass()
        self.message: discord.InteractionMessage | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Nur wer die Klasse gerollt hat darf aendern.", ephemeral=True
            )
            return False
        return True

    async def _refresh(self, interaction: discord.Interaction):
        user_class_data[self.owner_id] = self.class_data
        total_score = calculate_class_score(self.class_data)
        embed = create_reveal_embed(self.class_data, 4, total_score, user_id=self.owner_id)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Primary wuerfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_primary(self, interaction: discord.Interaction, button: discord.ui.Button):
        perk1 = self.class_data.get("perk1", "")
        self.class_data["primary"] = self.rc.get_random_primary(perk1)
        await self._refresh(interaction)

    @discord.ui.button(label="Secondary wuerfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_secondary(self, interaction: discord.Interaction, button: discord.ui.Button):
        perk1 = self.class_data.get("perk1", "")
        self.class_data["secondary"] = self.rc.get_random_secondary(perk1)
        await self._refresh(interaction)

    @discord.ui.button(label="Perks wuerfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_perks(self, interaction: discord.Interaction, button: discord.ui.Button):
        old_perk1 = self.class_data.get("perk1", "")
        new_perk1 = self.rc.get_random_perk1()
        self.class_data["perk1"] = new_perk1
        self.class_data["perk2"] = self.rc.get_random_perk2()
        self.class_data["perk3"] = self.rc.get_random_perk3()
        # Perk1 steuert Bling (zwei Attachments) -> Waffen neu, falls geaendert
        if old_perk1 != new_perk1:
            self.class_data["primary"] = self.rc.get_random_primary(new_perk1)
            self.class_data["secondary"] = self.rc.get_random_secondary(new_perk1)
        await self._refresh(interaction)

    @discord.ui.button(label="Extras wuerfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_extras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.class_data["equipment"] = self.rc.get_random_equipment()
        self.class_data["special_grenade"] = self.rc.get_random_special_grenade()
        await self._refresh(interaction)

    @discord.ui.button(label="Bleibt so", style=discord.ButtonStyle.success, row=0)
    async def lock_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        total_score = calculate_class_score(self.class_data)
        embed = create_reveal_embed(self.class_data, 4, total_score, user_id=self.owner_id)
        existing = embed.footer.text if embed.footer and embed.footer.text else ""
        embed.set_footer(text=(existing + "  -  LOCKED").strip(" -"))
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

# ==================== GLOBALE FILTER (vom Admin gesetzt) ====================

active_filters = {
    "min_score": None,
    "max_score": None,
    "excluded": [],
}

# Map-Pool: Maps werden nach dem Rollen entfernt, /reset stellt alle wieder her
import randomClass as _rc
_all_maps = list(_rc.RandomClass().maps)
available_maps = list(_all_maps)

MAPS_DIR = os.path.join(os.path.dirname(__file__), "maps")

# ==================== SLASH COMMANDS (ephemeral) ====================

@tree.command(name="filter", description="[Admin] Setze Filter fuer alle /random Rolls")
@app_commands.describe(
    min_score="Minimaler Klassen-Score (0-61, z.B. 18)",
    max_score="Maximaler Klassen-Score (0-61, z.B. 35)",
    no_ar="Assault Rifles ausschließen",
    no_smg="SMGs ausschließen",
    no_lmg="LMGs ausschließen",
    no_sniper="Sniper ausschließen",
    no_riot_shield="Riot Shield ausschließen",
)
async def set_filter(
    interaction: discord.Interaction,
    min_score: int = None,
    max_score: int = None,
    no_ar: bool = False,
    no_smg: bool = False,
    no_lmg: bool = False,
    no_sniper: bool = False,
    no_riot_shield: bool = False,
):
    """Setzt globale Filter die fuer alle /random Rolls gelten."""
    user_id = interaction.user.id

    if user_id not in FILTER_IDS:
        await interaction.response.send_message("Du hast keine Berechtigung, Filter zu setzen!", ephemeral=True)
        return

    # Score-Filter nur fuer Admins
    if (min_score is not None or max_score is not None) and user_id != ADMIN_ID:
        await interaction.response.send_message(
            "Nur Admins duerfen Score-Filter setzen! Du kannst nur Waffenkategorien ausschliessen.",
            ephemeral=True
        )
        return

    excluded = []
    if no_ar: excluded.append("ar")
    if no_smg: excluded.append("smg")
    if no_lmg: excluded.append("lmg")
    if no_sniper: excluded.append("sniper")
    if no_riot_shield: excluded.append("riot_shield")

    if user_id == ADMIN_ID:
        active_filters["min_score"] = min_score
        active_filters["max_score"] = max_score
    active_filters["excluded"] = excluded

    # Bestaetigungsnachricht bauen
    parts = []
    if min_score is not None:
        parts.append(f"Min Score: **{min_score}**")
    if max_score is not None:
        parts.append(f"Max Score: **{max_score}**")
    if excluded:
        label_map = {"ar": "Assault Rifles", "smg": "SMGs", "lmg": "LMGs", "sniper": "Sniper", "riot_shield": "Riot Shield"}
        names = [label_map.get(e, e) for e in excluded]
        parts.append(f"Ausgeschlossen: **{', '.join(names)}**")

    if parts:
        msg = "Filter gesetzt:\n" + "\n".join(parts)
    else:
        msg = "Filter gesetzt: Keine Einschraenkungen (alles erlaubt)."

    await interaction.response.send_message(msg, ephemeral=False)

@tree.command(name="reset", description="[Admin] Setze Filter zurueck")
async def reset_filter(interaction: discord.Interaction):
    """Setzt Filter zurueck (Admins: alles, Filter-User: nur Waffenkategorien)."""
    user_id = interaction.user.id

    if user_id not in FILTER_IDS:
        await interaction.response.send_message("Du hast keine Berechtigung, Filter zurueckzusetzen!", ephemeral=True)
        return

    if user_id == ADMIN_ID:
        active_filters["min_score"] = None
        active_filters["max_score"] = None
        active_filters["excluded"] = []
        available_maps.clear()
        available_maps.extend(_all_maps)
        await interaction.response.send_message(
            "Alle Filter und der Map-Pool wurden zurueckgesetzt. /random und /map sind wieder uneingeschraenkt.",
            ephemeral=False
        )
    else:
        active_filters["excluded"] = []
        await interaction.response.send_message("Waffenkategorie-Filter wurden zurueckgesetzt.", ephemeral=False)

@tree.command(name="random", description="Generiere eine zufällige MW2 Klasse")
async def random_class(interaction: discord.Interaction):
    """Animated slot-machine reveal - nur fuer den User sichtbar."""
    user_id = interaction.user.id

    class_data, total_score = generate_class_data(
        user_id,
        min_score=active_filters["min_score"],
        max_score=active_filters["max_score"],
        excluded_categories=active_filters["excluded"],
    )

    if class_data is None:
        await interaction.response.send_message(
            "Konnte keine Klasse finden, die den aktiven Filtern entspricht. Ein Admin muss die Filter anpassen!",
            ephemeral=True
        )
        return

    # Stats tracken
    record_roll(user_id, class_data, total_score, display_name=interaction.user.display_name)

    # Step 0: Loading embed mit ???
    loading = create_loading_embed(user_id)
    await interaction.response.send_message(embed=loading, ephemeral=True)
    await asyncio.sleep(0.8)

    # Step 1: Perks enthuellen
    await interaction.edit_original_response(embed=create_reveal_embed(class_data, 1, user_id=user_id))
    await asyncio.sleep(0.8)

    # Step 2: Equipment & Grenade enthuellen
    await interaction.edit_original_response(embed=create_reveal_embed(class_data, 2, user_id=user_id))
    await asyncio.sleep(0.8)

    # Step 3: Waffen enthuellen (spoilered)
    await interaction.edit_original_response(embed=create_reveal_embed(class_data, 3, user_id=user_id))
    await asyncio.sleep(1.0)

    # Step 4: Finales Embed mit Score + Tier-Farbe + Reroll-Buttons
    view = ClassRollView(owner_id=user_id, class_data=class_data)
    message = await interaction.edit_original_response(
        embed=create_reveal_embed(class_data, 4, total_score, user_id=user_id),
        view=view,
    )
    view.message = message

    is_roast_target = user_id == ROAST_TARGET_ID

    # Bonus-Effekte je nach Tier (Channel-Nachricht + Voice-TTS)
    if total_score > 45:
        await asyncio.sleep(0.5)
        if is_roast_target:
            await interaction.channel.send(
                f"# \U0001f921 Ausgerechnet DU? \U0001f921\n"
                f">>> {interaction.user.mention} hat ne Legendary gezogen... verschwendet an den grössten Bot auf dem Server.\n"
                f"Score: **{total_score}** / 61 - du wirst trotzdem 1/20 gehen, du Opfer."
            )
            await speak_in_channel(
                interaction.guild, interaction.user,
                f"{interaction.user.display_name} hat ne Legendary gezogen, aber mal ehrlich - der wird die Klasse trotzdem versauen! Pure Glückssache amk!"
            )
        else:
            await interaction.channel.send(
                f"# \u26a1\U0001f525 LEGENDARY DROP! \U0001f525\u26a1\n"
                f">>> {interaction.user.mention} hat eine **OVERPOWERED** Klasse gezogen!\n"
                f"Score: **{total_score}** / 61 \U0001f608"
            )
            await speak_in_channel(
                interaction.guild, interaction.user,
                f"{interaction.user.display_name} hat eine OVERPOWERED Klasse gezogen amk! Score {total_score} von 61!"
            )
    elif total_score < 18:
        await asyncio.sleep(0.5)
        if is_roast_target:
            await interaction.channel.send(
                f"# \U0001f480 PERFECT MATCH \U0001f480\n"
                f">>> {interaction.user.mention} MÜLL-Klasse für den MÜLL-Spieler! Du Schmock.\n"
                f"Score: **{total_score}** / 61 - endlich mal ne Klasse die zu deinem Skill passt!"
            )
            await speak_in_channel(
                interaction.guild, interaction.user,
                f"{interaction.user.display_name} hat ne Müll Klasse gezogen - perfekt für dich du Opfer! Score {total_score} von 61. Bleib lieber in der Lobby du Behindi!"
            )
        else:
            await interaction.channel.send(
                f"# \U0001f480 Trash Tier... \U0001f480\n"
                f">>> {interaction.user.mention} hat eine **MÜLL-KLASSE** gezogen, der huso!\n"
                f"Score: **{total_score}** / 61 \U0001f5d1\ufe0f"
            )
            await speak_in_channel(
                interaction.guild, interaction.user,
                f"{interaction.user.display_name} hat eine Müll Klasse gezogen! Score {total_score} von 61!"
            )

    # Extra-Beleidigung fuer Roast-Target bei JEDEM /random (zusaetzlich zum Tier-Effekt)
    if is_roast_target:
        await asyncio.sleep(0.3)
        await interaction.channel.send(
            f"Übrigens {interaction.user.mention}: egal was du rollst, du bleibst trotzdem der schlechteste Spieler hier du Hund."
        )


@tree.command(name="map", description="Generiere zufällige Map-Settings")
async def random_map(interaction: discord.Interaction):
    if not available_maps:
        await interaction.response.send_message(
            "Alle Maps wurden bereits gespielt! Ein Admin kann mit `/reset` den Map-Pool zuruecksetzen.",
            ephemeral=True
        )
        return

    embed, map_name = create_map_embed(interaction.user.id, available_maps)
    if map_name and map_name in available_maps:
        available_maps.remove(map_name)

    # Map-Bild anhängen falls vorhanden
    file = None
    if map_name:
        for ext in ("png", "jpg", "jpeg", "webp"):
            img_path = os.path.join(MAPS_DIR, f"{map_name}.{ext}")
            if os.path.exists(img_path):
                file = discord.File(img_path, filename=f"map.{ext}")
                embed.set_image(url=f"attachment://map.{ext}")
                break

    remaining = len(available_maps)
    embed.set_footer(text=f"Noch {remaining}/{len(_all_maps)} Maps verfuegbar")

    if file:
        await interaction.response.send_message(embed=embed, file=file, ephemeral=False)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=False)


@tree.command(name="stats", description="Zeige Statistiken der gerollten Items")
async def stats(interaction: discord.Interaction):
    embed = create_stats_embed()
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="playerstats", description="Zeige deine persoenlichen Roll-Statistiken")
async def player_stats(interaction: discord.Interaction):
    embed = create_player_stats_embed(interaction.user.id, interaction.user.display_name)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="change", description="Aendere Primary oder Secondary deiner Klasse")
@app_commands.choices(what=[
    app_commands.Choice(name="Primary", value="primary"),
    app_commands.Choice(name="Secondary", value="secondary"),
])
async def change(interaction: discord.Interaction, what: app_commands.Choice[str]):
    user_id = interaction.user.id
    if what.value == "primary":
        result = change_primary_embed(user_id)
    else:
        result = change_secondary_embed(user_id)

    if isinstance(result, str):
        await interaction.response.send_message(result, ephemeral=True)
    else:
        await interaction.response.send_message(embed=result, ephemeral=True)


@tree.command(name="tts", description="Teste die Voice-TTS Ansage")
@app_commands.describe(text="Text der vorgelesen werden soll")
async def tts_test(interaction: discord.Interaction, text: str = "Das ist ein Test der Sprachausgabe!"):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Du musst in einem Voice-Channel sein!", ephemeral=True)
        return
    await interaction.response.send_message(f"Sage: *{text}*", ephemeral=True)
    await speak_in_channel(interaction.guild, interaction.user, text)


# ==================== EVENTS ====================

@client.event
async def on_ready() -> None:
    reset_session()
    await tree.sync()
    print(f'{client.user} has connected to Discord! Slash-Commands synced. Session stats reset.')


@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return

    # Hinweis fuer alte ?-Prefix User
    if message.content in ["?random", "?zufall", "?", "?map", "?stats"] or message.content.startswith("?change"):
        await message.channel.send(
            f"{message.author.mention} Benutze jetzt Slash-Commands! "
            "Tippe `/random`, `/map`, `/stats` oder `/change`. du hond."
        )
        return

    # Auf alle anderen Nachrichten reagieren
    if message.content and not message.content.startswith("/"):
        await message.channel.send(
            f"{message.author.mention} Halt die Fresse und benutz `/`-Commands, du Hund."
        )


def main() -> None:
    client.run(TOKEN)

if __name__ == "__main__":
    main()
