"""
JARVIS V2 - Discord OpenClaw Remote Interface
Allows Setty to remotely command Jarvis from his phone with strict user authorization.
"""
import os
import asyncio
import discord
from core.config import config
from core.schemas import ChatMessage, MessageRole
from security.authentication import auth_manager
from core.orchestrator import orchestrator

class DiscordAgent:
    def __init__(self):
        self.token = config.DISCORD_BOT_TOKEN
        self.allowed_users = config.DISCORD_ALLOWED_USER_IDS

    def start(self):
        if not self.token or "your_" in self.token:
            print("📱 [Discord OpenClaw: No valid token in .env. Remote phone access disabled.]")
            return

        class JarvisDiscordClient(discord.Client):
            async def on_ready(self):
                print(f"📱 [Discord OpenClaw: Online as {self.user} - Listening for authorized commands]")

            async def on_message(self, message):
                if message.author == self.user:
                    return

                # Check channel type (DM, mention, or starts with 'jarvis')
                is_dm = isinstance(message.channel, discord.DMChannel)
                is_mention = self.user in message.mentions
                is_named = message.content.lower().startswith('jarvis')

                if not (is_dm or is_mention or is_named):
                    return

                # Security Check: Verify User ID against Whitelist
                if not auth_manager.verify_discord_user(message.author.id):
                    await message.channel.send("⚠️ Unauthorized user. Access to local PC control is restricted to the owner.")
                    return

                # Clean prompt
                clean_text = message.content.replace(f'<@{self.user.id}>', '').strip()
                if clean_text.lower().startswith('jarvis'):
                    clean_text = clean_text[6:].strip()

                print(f"📱 [Discord Command from {message.author}]: {clean_text}")

                async with message.channel.typing():
                    # Execute turn via Orchestrator
                    loop = asyncio.get_event_loop()
                    def _run_orch():
                        tokens = []
                        for t in orchestrator.execute_turn(clean_text, history=[], user_id=str(message.author.id), channel="discord"):
                            tokens.append(t)
                        return "".join(tokens)

                    reply = await loop.run_in_executor(None, _run_orch)

                # Discord 2000 character message limit handling
                if len(reply) > 1900:
                    for i in range(0, len(reply), 1900):
                        await message.channel.send(reply[i:i+1900])
                else:
                    await message.channel.send(reply or "Command executed, sir.")

        intents = discord.Intents.default()
        intents.message_content = True
        client = JarvisDiscordClient(intents=intents)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(client.start(self.token))
        except Exception as e:
            print(f"📱 [Discord OpenClaw Error]: {e}")

# Global Discord Agent Singleton
discord_agent = DiscordAgent()
