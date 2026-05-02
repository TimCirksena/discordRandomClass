from typing import Final
from datetime import datetime
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
from playerstats import record_roll, reset_session, record_reroll
from voice import speak_in_channel
import config as app_config

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
ADMIN_ID: Final[int] = 424477646555185162
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


# ==================== REROLL VIEW + VOTE VIEW ====================

class VoteView(discord.ui.View):
    """Channel-Abstimmung nach Reroll: Opfer oder Gueltig."""

    def __init__(self, reroller_id: int, reroll_label: str):
        super().__init__(timeout=600)  # 10 Minuten
        self.reroller_id = reroller_id
        self.reroll_label = reroll_label
        self.votes_opfer: set[int] = set()
        self.votes_gueltig: set[int] = set()
        self.message: discord.Message | None = None

    def _compose(self, mention: str) -> str:
        opfer = len(self.votes_opfer)
        gueltig = len(self.votes_gueltig)
        return (
            f"{mention} hat **{self.reroll_label}** rerollt. Abstimmung:\n"
            f"> Opfer: **{opfer}** - Gültig: **{gueltig}**"
        )

    async def _register_vote(self, interaction: discord.Interaction, kind: str):
        uid = interaction.user.id
        if uid == self.reroller_id:
            await interaction.response.send_message(
                "Du kannst nicht über deinen eigenen Reroll abstimmen.", ephemeral=True
            )
            return
        if kind == "opfer":
            self.votes_gueltig.discard(uid)
            self.votes_opfer.add(uid)
        else:
            self.votes_opfer.discard(uid)
            self.votes_gueltig.add(uid)
        mention = f"<@{self.reroller_id}>"
        await interaction.response.edit_message(content=self._compose(mention), view=self)

    @discord.ui.button(label="Opfer", style=discord.ButtonStyle.danger)
    async def vote_opfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._register_vote(interaction, "opfer")

    @discord.ui.button(label="Gültig", style=discord.ButtonStyle.success)
    async def vote_gueltig(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._register_vote(interaction, "gueltig")

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ClassRollView(discord.ui.View):
    """Reroll-Buttons unter der gerollten Klasse. Pro /random nur ein Reroll."""

    def __init__(self, owner_id: int, owner_mention: str, owner_name: str, channel: discord.abc.Messageable, class_data: dict, parent_ts: str = "", initial_score: int = 0, spoilered: bool = True):
        super().__init__(timeout=300)  # 5 Minuten
        self.owner_id = owner_id
        self.owner_mention = owner_mention
        self.owner_name = owner_name
        self.channel = channel
        self.class_data = class_data
        self.rc = randomClass.RandomClass()
        self.message: discord.InteractionMessage | None = None
        self.parent_ts = parent_ts
        self.initial_score = initial_score
        self.spoilered = spoilered

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Nur wer die Klasse gerollt hat darf ändern.", ephemeral=True
            )
            return False
        return True

    async def _apply_reroll(self, interaction: discord.Interaction, reroll_label: str, reroll_type: str):
        """Zeigt die neue Klasse an, disabled alle Buttons und postet Vote-Message im Channel."""
        user_class_data[self.owner_id] = self.class_data
        total_score = calculate_class_score(self.class_data)
        embed = create_reveal_embed(self.class_data, 4, total_score, user_id=self.owner_id, spoilered=self.spoilered)
        existing = embed.footer.text if embed.footer and embed.footer.text else ""
        embed.set_footer(text=(existing + f"  -  rerollt: {reroll_label}").strip(" -"))
        # Alle Buttons disablen - ein Reroll pro /random
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
        # Reroll in Tages-Stats festhalten + Event in History schreiben
        record_reroll(
            self.owner_id,
            self.owner_name,
            reroll_type,
            class_data=dict(self.class_data),
            prev_score=self.initial_score,
            new_score=total_score,
            parent_ts=self.parent_ts,
        )
        # Vote-Message im Channel
        vote = VoteView(reroller_id=self.owner_id, reroll_label=reroll_label)
        try:
            msg = await self.channel.send(content=vote._compose(self.owner_mention), view=vote)
            vote.message = msg
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Primary würfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_primary(self, interaction: discord.Interaction, button: discord.ui.Button):
        perk1 = self.class_data.get("perk1", "")
        self.class_data["primary"] = self.rc.get_random_primary(perk1)
        await self._apply_reroll(interaction, "Primary", "primary")

    @discord.ui.button(label="Secondary würfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_secondary(self, interaction: discord.Interaction, button: discord.ui.Button):
        perk1 = self.class_data.get("perk1", "")
        self.class_data["secondary"] = self.rc.get_random_secondary(perk1)
        await self._apply_reroll(interaction, "Secondary", "secondary")

    @discord.ui.button(label="Perks würfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_perks(self, interaction: discord.Interaction, button: discord.ui.Button):
        old_perk1 = self.class_data.get("perk1", "")
        new_perk1 = self.rc.get_random_perk1()
        self.class_data["perk1"] = new_perk1
        self.class_data["perk2"] = self.rc.get_random_perk2()
        self.class_data["perk3"] = self.rc.get_random_perk3()
        if old_perk1 != new_perk1:
            self.class_data["primary"] = self.rc.get_random_primary(new_perk1)
            self.class_data["secondary"] = self.rc.get_random_secondary(new_perk1)
        await self._apply_reroll(interaction, "Perks", "perks")

    @discord.ui.button(label="Extras würfeln", style=discord.ButtonStyle.secondary, row=0)
    async def reroll_extras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.class_data["equipment"] = self.rc.get_random_equipment()
        self.class_data["special_grenade"] = self.rc.get_random_special_grenade()
        await self._apply_reroll(interaction, "Extras", "extras")

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

# ==================== SHARED CORE (Slash + Text) ====================

async def _announce_tier(user, channel, guild, total_score: int) -> None:
    """Tier-Announcement (Legendary/Trash) + Voice-TTS. Geteilt zwischen Slash- und Text-Commands."""
    legendary_min = app_config.get("legendary_min")
    trash_max = app_config.get("trash_max")
    display_name = getattr(user, "display_name", user.name)

    if total_score > legendary_min:
        await asyncio.sleep(0.5)
        await channel.send(
            f"# ⚡\U0001f525 LEGENDARY DROP! \U0001f525⚡\n"
            f">>> {user.mention} hat eine **OVERPOWERED** Klasse gezogen!\n"
            f"Score: **{total_score}** / 61 \U0001f608"
        )
        if guild:
            await speak_in_channel(
                guild, user,
                f"{display_name} hat eine OVERPOWERED Klasse gezogen amk! Score {total_score} von 61!"
            )
    elif total_score < trash_max:
        await asyncio.sleep(0.5)
        await channel.send(
            f"# \U0001f480 Trash Tier... \U0001f480\n"
            f">>> {user.mention} hat eine **MÜLL-KLASSE** gezogen, der huso!\n"
            f"Score: **{total_score}** / 61 \U0001f5d1️"
        )
        if guild:
            await speak_in_channel(
                guild, user,
                f"{display_name} hat eine Müll Klasse gezogen! Score {total_score} von 61!"
            )


# ==================== TEXT-COMMAND HANDLER (für Matrix-Bridge etc.) ====================
# Slash-Commands nutzen Discord-Interactions (ephemeral möglich). Wenn ein User /random aber
# als reine Textnachricht schickt (z.B. via mautrix-discord aus Element heraus), greifen
# diese Handler und antworten öffentlich im Channel.

async def _text_random(message: Message) -> None:
    user = message.author
    channel = message.channel
    guild = message.guild
    display_name = getattr(user, "display_name", user.name)

    class_data, total_score = generate_class_data(
        user.id,
        min_score=active_filters["min_score"],
        max_score=active_filters["max_score"],
        excluded_categories=active_filters["excluded"],
    )

    if class_data is None:
        await channel.send(
            f"{user.mention} Konnte keine Klasse finden, die den aktiven Filtern entspricht. "
            "Ein Admin muss die Filter anpassen!"
        )
        return

    record_roll(user.id, class_data, total_score, display_name=display_name)

    msg = await channel.send(embed=create_loading_embed(user.id))
    await asyncio.sleep(0.8)
    await msg.edit(embed=create_reveal_embed(class_data, 1, user_id=user.id))
    await asyncio.sleep(0.8)
    await msg.edit(embed=create_reveal_embed(class_data, 2, user_id=user.id))
    await asyncio.sleep(0.8)
    await msg.edit(embed=create_reveal_embed(class_data, 3, user_id=user.id))
    await asyncio.sleep(1.0)

    roll_ts = datetime.now().isoformat(timespec="seconds")
    view = ClassRollView(
        owner_id=user.id,
        owner_mention=user.mention,
        owner_name=display_name,
        channel=channel,
        class_data=class_data,
        parent_ts=roll_ts,
        initial_score=total_score,
    )
    await msg.edit(
        embed=create_reveal_embed(class_data, 4, total_score, user_id=user.id),
        view=view,
    )
    view.message = msg

    await _announce_tier(user, channel, guild, total_score)


async def _text_map(message: Message) -> None:
    channel = message.channel
    if not available_maps:
        await channel.send(
            f"{message.author.mention} Alle Maps wurden bereits gespielt! "
            "Ein Admin kann mit `/reset` den Map-Pool zurücksetzen."
        )
        return

    embed, map_name = create_map_embed(message.author.id, available_maps)
    if map_name and map_name in available_maps:
        available_maps.remove(map_name)

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
        await channel.send(embed=embed, file=file)
    else:
        await channel.send(embed=embed)


async def _text_stats(message: Message) -> None:
    await message.channel.send(embed=create_stats_embed())


async def _text_playerstats(message: Message) -> None:
    display_name = getattr(message.author, "display_name", message.author.name)
    embed = create_player_stats_embed(message.author.id, display_name)
    await message.channel.send(embed=embed)


async def _text_change(message: Message, what: str) -> None:
    user_id = message.author.id
    if what == "primary":
        result = change_primary_embed(user_id)
    else:
        result = change_secondary_embed(user_id)

    if isinstance(result, str):
        await message.channel.send(f"{message.author.mention} {result}")
    else:
        await message.channel.send(embed=result)


# ==================== SLASH COMMANDS (ephemeral) ====================

@tree.command(name="filter", description="[Admin] Setze Filter für alle /random Rolls")
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
    """Setzt globale Filter die für alle /random Rolls gelten."""
    user_id = interaction.user.id

    if user_id not in FILTER_IDS:
        await interaction.response.send_message("Du hast keine Berechtigung, Filter zu setzen!", ephemeral=True)
        return

    # Score-Filter nur für Admins
    if (min_score is not None or max_score is not None) and user_id != ADMIN_ID:
        await interaction.response.send_message(
            "Nur Admins dürfen Score-Filter setzen! Du kannst nur Waffenkategorien ausschließen.",
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

    # Bestätigungsnachricht bauen
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
        msg = "Filter gesetzt: Keine Einschränkungen (alles erlaubt)."

    await interaction.response.send_message(msg, ephemeral=False)

@tree.command(name="reset", description="[Admin] Setze Filter zurück")
async def reset_filter(interaction: discord.Interaction):
    """Setzt Filter zurück (Admins: alles, Filter-User: nur Waffenkategorien)."""
    user_id = interaction.user.id

    if user_id not in FILTER_IDS:
        await interaction.response.send_message("Du hast keine Berechtigung, Filter zurückzusetzen!", ephemeral=True)
        return

    if user_id == ADMIN_ID:
        active_filters["min_score"] = None
        active_filters["max_score"] = None
        active_filters["excluded"] = []
        available_maps.clear()
        available_maps.extend(_all_maps)
        await interaction.response.send_message(
            "Alle Filter und der Map-Pool wurden zurückgesetzt. /random und /map sind wieder uneingeschränkt.",
            ephemeral=False
        )
    else:
        active_filters["excluded"] = []
        await interaction.response.send_message("Waffenkategorie-Filter wurden zurückgesetzt.", ephemeral=False)

@tree.command(name="random", description="Generiere eine zufällige MW2 Klasse")
async def random_class(interaction: discord.Interaction):
    """Animated slot-machine reveal - nur für den User sichtbar."""
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
    await interaction.edit_original_response(embed=create_reveal_embed(class_data, 1, user_id=user_id, spoilered=False))
    await asyncio.sleep(0.8)

    # Step 2: Equipment & Grenade enthuellen
    await interaction.edit_original_response(embed=create_reveal_embed(class_data, 2, user_id=user_id, spoilered=False))
    await asyncio.sleep(0.8)

    # Step 3: Waffen enthuellen (ephemeral - kein Spoiler nötig, sieht eh nur der User)
    await interaction.edit_original_response(embed=create_reveal_embed(class_data, 3, user_id=user_id, spoilered=False))
    await asyncio.sleep(1.0)

    # Step 4: Finales Embed mit Score + Tier-Farbe + Reroll-Buttons
    # parent_ts verlinkt das Reroll-Event mit dem ursprünglichen Roll-Event in der History
    roll_ts = datetime.now().isoformat(timespec="seconds")
    view = ClassRollView(
        owner_id=user_id,
        owner_mention=interaction.user.mention,
        owner_name=interaction.user.display_name,
        channel=interaction.channel,
        class_data=class_data,
        parent_ts=roll_ts,
        initial_score=total_score,
        spoilered=False,
    )
    message = await interaction.edit_original_response(
        embed=create_reveal_embed(class_data, 4, total_score, user_id=user_id, spoilered=False),
        view=view,
    )
    view.message = message

    await _announce_tier(interaction.user, interaction.channel, interaction.guild, total_score)


@tree.command(name="map", description="Generiere zufällige Map-Settings")
async def random_map(interaction: discord.Interaction):
    if not available_maps:
        await interaction.response.send_message(
            "Alle Maps wurden bereits gespielt! Ein Admin kann mit `/reset` den Map-Pool zurücksetzen.",
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


@tree.command(name="threshold", description="[Admin] Setze Legendary/Trash Score-Schwellen")
@app_commands.describe(
    legendary="Score > diesem Wert = Legendary Tier (default 40)",
    trash="Score < diesem Wert = Trash Tier (default 18)",
)
async def set_threshold(
    interaction: discord.Interaction,
    legendary: int = None,
    trash: int = None,
):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("Nur Admins dürfen Schwellen setzen.", ephemeral=True)
        return

    changes = []
    if legendary is not None:
        app_config.set_value("legendary_min", legendary)
        changes.append(f"Legendary > **{legendary}**")
    if trash is not None:
        app_config.set_value("trash_max", trash)
        changes.append(f"Trash < **{trash}**")

    if not changes:
        current = (
            f"Aktuelle Schwellen:\n"
            f"- Legendary > **{app_config.get('legendary_min')}**\n"
            f"- Trash < **{app_config.get('trash_max')}**"
        )
        await interaction.response.send_message(current, ephemeral=True)
        return

    await interaction.response.send_message("Neue Schwellen:\n" + "\n".join(changes), ephemeral=False)


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

    content = (message.content or "").strip()
    lower = content.lower()
    parts = lower.split()
    cmd = parts[0] if parts else ""

    # Text-Trigger für /-Commands (z.B. via Matrix-Bridge, wo /random als reine Textnachricht ankommt).
    # Echte Discord-Slash-Commands laufen über interactions, nicht on_message - hier kollidiert nichts.
    # `!`-Prefix wird zusätzlich akzeptiert, falls jemand das gewohnt ist.
    if cmd in ("/random", "!random"):
        await _text_random(message)
        return
    if cmd in ("/map", "!map"):
        await _text_map(message)
        return
    if cmd in ("/stats", "!stats"):
        await _text_stats(message)
        return
    if cmd in ("/playerstats", "!playerstats"):
        await _text_playerstats(message)
        return
    if cmd in ("/change", "!change"):
        sub = parts[1] if len(parts) > 1 else ""
        if sub.startswith("primary"):
            await _text_change(message, "primary")
        elif sub.startswith("secondary"):
            await _text_change(message, "secondary")
        else:
            await message.channel.send(
                f"{message.author.mention} Benutze `/change primary` oder `/change secondary`."
            )
        return

    # Hinweis für alte ?-Prefix User
    if content in ["?random", "?zufall", "?", "?map", "?stats"] or content.startswith("?change"):
        await message.channel.send(
            f"{message.author.mention} Benutze jetzt Slash-Commands! "
            "Tippe `/random`, `/map`, `/stats` oder `/change`. du hond."
        )
        return

    # Insult für alles ohne /-Prefix - Bots/Webhooks (z.B. Bridge-Pingbacks) verschonen,
    # damit der Bot sich nicht selbst oder die Bridge in Schleifen beleidigt.
    if content and not content.startswith("/") and not message.author.bot:
        await message.channel.send(
            f"{message.author.mention} Halt die Fresse und benutz `/`-Commands, du Hund."
        )


def main() -> None:
    client.run(TOKEN)

if __name__ == "__main__":
    main()
