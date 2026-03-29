# Herr Herbert Zufallsklasse - MW2 Random Class Discord Bot

Ein Discord-Bot, der zufaellige MW2-Klassen (Modern Warfare 2, 2009) generiert, inklusive animierter Reveal-Embeds, Voice-TTS-Ansagen, Scoring-System und Spielerstatistiken.

## Features

- `/random` - Generiert eine zufaellige MW2-Klasse mit animiertem Reveal
- `/map` - Wuerfelt eine zufaellige Map mit HP-Regeneration und Team-Damage-Settings
- `/change primary|secondary` - Tauscht Primary oder Secondary deiner letzten Klasse
- `/filter` - Setzt globale Filter (Score-Range, Waffenkategorien ausschliessen)
- `/reset` - Setzt Filter und Map-Pool zurueck
- `/stats` - Zeigt Session-Statistiken aller gerollten Items
- `/playerstats` - Zeigt persoenliche Roll-Statistiken (Session + historisch)
- `/tts` - Testet die Voice-TTS-Ansage
- Scoring-System (0-61 Punkte) mit Tier-Einstufungen (Legendary / Normal / Trash)
- Voice-TTS-Ansagen bei Legendary- oder Trash-Klassen (Bot joint Voice-Channel)
- Deutsche Uebersetzungen fuer ausgewaehlte User

## Voraussetzungen

- **Python 3.11+**
- **ffmpeg** muss installiert und im PATH sein (wird fuer Voice/TTS benoetigt)
- Ein **Discord Bot Token**

## Setup

### 1. Repository klonen

```bash
git clone https://github.com/TimCirksena/discordRandomClass.git
cd discordRandomClass
```

### 2. Python-Abhaengigkeiten installieren

```bash
pip install discord.py python-dotenv edge-tts
```

Benoetigte Pakete:
| Paket | Zweck |
|---|---|
| `discord.py` | Discord API (inkl. Voice-Support) |
| `python-dotenv` | Laedt `.env`-Datei fuer den Bot-Token |
| `edge-tts` | Text-to-Speech ueber Microsoft Edge (kostenlos, kein API-Key noetig) |

> **Hinweis:** `discord.py` muss mit Voice-Support installiert sein. Falls Voice nicht funktioniert:
> ```bash
> pip install discord.py[voice]
> ```

### 3. ffmpeg installieren

ffmpeg wird benoetigt, damit der Bot Audio im Voice-Channel abspielen kann.

**Windows:**
- Lade ffmpeg von https://ffmpeg.org/download.html herunter
- Entpacke das Archiv
- Fuege den `bin`-Ordner (der `ffmpeg.exe` enthaelt) zu deiner **PATH**-Umgebungsvariable hinzu
- Teste mit: `ffmpeg -version`

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### 4. Discord Bot erstellen

1. Gehe zu https://discord.com/developers/applications
2. Klicke auf **New Application** und gib einen Namen ein
3. Gehe zu **Bot** im Seitenmenue
4. Klicke auf **Reset Token** und kopiere den Token
5. Aktiviere unter **Privileged Gateway Intents**:
   - **Message Content Intent**
   - **Server Members Intent** (optional)
6. Gehe zu **OAuth2 > URL Generator**
7. Waehle folgende Scopes: `bot`, `applications.commands`
8. Waehle folgende Bot Permissions:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Attach Files
   - Connect (Voice)
   - Speak (Voice)
9. Kopiere die generierte URL und oeffne sie im Browser, um den Bot auf deinen Server einzuladen

### 5. `.env`-Datei erstellen

Erstelle eine Datei namens `.env` im Projektordner:

```
DISCORD_TOKEN=dein_bot_token_hier
```

### 6. Admin- und Filter-IDs anpassen

In [main.py](main.py) sind Admin- und Filter-berechtigte User-IDs hardcoded. Passe sie an deine Discord-User-IDs an:

```python
ADMIN_ID: Final[int] = 424477646555185162  # Deine Discord User-ID
FILTER_IDS: Final[set] = {
    ADMIN_ID,
    695156653770932274,  # Weitere berechtigte User
    530847300407263233,
}
```

Um deine Discord-User-ID zu finden: Aktiviere den Entwicklermodus in Discord (Einstellungen > Erweitert > Entwicklermodus), dann Rechtsklick auf deinen Namen > ID kopieren.

### 7. Deutsche Uebersetzungen (optional)

In [responses.py](responses.py) kannst du User-IDs hinzufuegen, die deutsche Uebersetzungen fuer Perks, Attachments etc. sehen sollen:

```python
GERMAN_USER_IDS = {
    695156653770932274,
    530847300407263233,
}
```

### 8. Map-Bilder (optional)

Erstelle einen Ordner `maps/` und lege dort Bilder der Maps ab (z.B. `Terminal.png`, `Highrise.webp`). Der Dateiname muss exakt dem Map-Namen entsprechen. Unterstuetzte Formate: `.png`, `.jpg`, `.jpeg`, `.webp`.

### 9. Bot starten

```bash
python main.py
```

Der Bot loggt sich ein und synchronisiert die Slash-Commands automatisch. Die erste Synchronisierung kann bis zu einer Stunde dauern, bis die Commands auf allen Servern sichtbar sind.

## Projektstruktur

```
discordRandomClass/
├── main.py            # Bot-Einstiegspunkt, Slash-Commands, Events
├── randomClass.py     # Zufallsgenerator fuer Waffen, Perks, Equipment etc.
├── scoringmodel.py    # Scoring-Daten und Score-Berechnung
├── responses.py       # Embed-Erstellung, Uebersetzungen, Animations-Logik
├── playerstats.py     # Persistente + Session-Spielerstatistiken
├── voice.py           # Voice-TTS mit edge-tts und ffmpeg
├── maps/              # (Optional) Map-Bilder
├── stats/             # (Auto-generiert) Taegliche Statistik-Dateien
└── .env               # Bot-Token (nicht committen!)
```

## Scoring-System

Jede generierte Klasse bekommt einen Score (0-61), der sich zusammensetzt aus:
- Primaerwaffe (Basiswert + Attachment-Modifier)
- Sekundaerwaffe (Basiswert + Attachment-Modifier)
- Equipment und Spezialgranate
- Perks (abhaengig von der Primaerwaffen-Kategorie)

| Score | Tier |
|---|---|
| > 40 | Legendary (Gold) |
| 18-40 | Normal (Blau) |
| < 18 | Trash (Grau) |

Bei Legendary- und Trash-Klassen gibt der Bot eine Ansage im Voice-Channel ab (falls der User in einem Voice-Channel ist).
