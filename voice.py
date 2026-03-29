import discord
import edge_tts
import asyncio
import os
import tempfile

# Deutsche Stimme (weiblich). Alternativen: "de-DE-ConradNeural" (männlich)
TTS_VOICE = "de-DE-KatjaNeural"


async def speak_in_channel(guild: discord.Guild, user: discord.Member, text: str):
    """Generiert TTS-Audio mit edge-tts, joint den Voice-Channel des Users und spielt es ab."""
    if not user.voice or not user.voice.channel:
        return

    channel = user.voice.channel

    # TTS-Audio generieren
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    try:
        communicate = edge_tts.Communicate(text, TTS_VOICE)
        await communicate.save(tmp.name)

        # Voice-Channel joinen
        voice_client = guild.voice_client
        if voice_client is None or not voice_client.is_connected():
            voice_client = await channel.connect(timeout=10.0, self_deaf=True)
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        # Audio abspielen und warten
        finished = asyncio.Event()
        voice_client.play(
            discord.FFmpegPCMAudio(tmp.name),
            after=lambda e: finished.set(),
        )
        await finished.wait()

        # Disconnect nach dem Abspielen
        await voice_client.disconnect()
    except Exception as e:
        print(f"[Voice TTS] Fehler: {e}")
        # Falls der Bot im Voice hängt, trotzdem disconnecten
        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception:
                pass
    finally:
        # Temp-Datei aufräumen
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
