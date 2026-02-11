from __future__ import annotations

import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv

from commands import QuestCommands
from database import GuildDatabase, SheetsClient
from deadline_manager import DeadlineManager
from invite_manager import InviteManager
from logger import setup_logger
from party_commands import PartyCommands
from utils import load_config


async def main() -> None:
    load_dotenv()
    config = load_config()
    logger = setup_logger("guild-bot", config.log_level)

    intents = discord.Intents.default()
    intents.members = True

    bot = commands.Bot(command_prefix=config.command_prefix, intents=intents)

    sheets = SheetsClient(config.google_sheets_id, config.google_credentials_file)
    db = GuildDatabase(sheets, config)

    bot.config = config
    bot.logger = logger
    bot.db = db

    invite_manager = InviteManager(bot)
    deadline_manager = DeadlineManager(bot)

    await bot.add_cog(QuestCommands(bot))
    await bot.add_cog(PartyCommands(bot, invite_manager))

    @bot.event
    async def on_ready() -> None:
        logger.info("Logged in as %s", bot.user)
        try:
            await bot.tree.sync()
        except Exception as exc:
            logger.exception("Command sync failed: %s", exc)
        # Start background loops after the bot is ready.
        invite_manager.start()
        deadline_manager.start()
        await bot.change_presence(activity=discord.Game(name=config.bot_status))

    await bot.start(config.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
