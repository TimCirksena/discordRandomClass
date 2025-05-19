from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message
from responses import get_response

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

intents: Intents = Intents.default()
intents.message_content = True
client: Client = Client(intents=intents)

async def send_message(message: Message, user_message: str) -> None:
    if not user_message:
        print('User message is empty')
        return
    try:
        # Hier übergeben wir zusätzlich message.author.id
        response = get_response(user_message, message.author.id)
        print(message.author.id)
        
        # Prüfe, ob response ein Embed-Objekt oder ein String ist
        if isinstance(response, str):
            await message.channel.send(f'{message.author.mention} {response}')
        else:
            # Falls es ein Embed ist
            await message.channel.send(f'{message.author.mention}', embed=response)

    except Exception as e:
        print(f"An error occurred: {e}")

# START UP
@client.event
async def on_ready() -> None:
    print(f'{client.user} has connected to Discord!')

# MESSAGE HANDLING
@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    username: str = str(message.author)
    user_message: str = message.content
    channel: str = str(message.channel)
    print(f'[{channel}] {username}: "{user_message}"')

    await send_message(message, user_message)


def main() -> None:
    client.run(TOKEN)

if __name__ == "__main__":
    main()
