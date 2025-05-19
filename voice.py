import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} ist online!")

@bot.command(name="playmp3")
async def play_mp3(ctx):
    # 1. Prüfen, ob der Benutzer in einem Voice-Channel ist
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Du bist nicht in einem Voice-Kanal!")
        return

    channel = ctx.author.voice.channel

    # 2. Bot dem Kanal joinen lassen
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_connected():
        # Falls der Bot nicht schon im VoiceChannel ist
        voice_client = await channel.connect()
    else:
        # Falls der Bot noch in einem anderen Channel hängt:
        if voice_client.channel != channel:
            await voice_client.move_to(channel)

    # 3. Audio abspielen (z.B. MP3 namens "example.mp3")
    source = discord.FFmpegPCMAudio("example.mp3")
    voice_client.play(source)

    # 4. Warten, bis das Audio fertig gespielt ist
    while voice_client.is_playing():
        await asyncio.sleep(1)

    # 5. Nach Ende wieder leaven (optional)
    await voice_client.disconnect()

# Bot starten
bot.run("DEIN_DISCORD_TOKEN")
