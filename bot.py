import logging
import os
import sys

import discord
from discord.ext import commands

import config
from views.autosell import SellMoneyButton


class AutosellBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix="!",
            case_insensitive=True,
            intents=intents,
            allowed_mentions=discord.AllowedMentions(
                roles=False, everyone=False, users=True
            ),
        )
        self.logger = logging.getLogger("bot")
        self.admins = list(config.ADMINS)

    async def setup_hook(self) -> None:
        self.add_view(SellMoneyButton())
        await self.load_cogs()
        synced = await self.tree.sync()
        self.logger.info("Synced %d global slash command(s)", len(synced))
        for command in synced:
            self.logger.info("  /%s", command.name)

    async def on_ready(self):
        self.logger.info("Logged in as %s (%s)", self.user, self.user and self.user.id)

    @staticmethod
    def setup_logging() -> None:
        logging.getLogger("discord").setLevel(logging.INFO)
        logging.getLogger("discord.http").setLevel(logging.WARNING)
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s | %(asctime)s | %(name)s | %(message)s",
            stream=sys.stdout,
        )

    async def load_cogs(self, directory: str = "./cogs") -> None:
        for file in os.listdir(directory):
            path = os.path.join(directory, file)
            if file.endswith(".py") and not file.startswith("_"):
                # Skip legacy phishing-related cogs if still present
                if file in {"my_cog.py"}:
                    continue
                ext = f"{directory[2:].replace('/', '.')}.{file[:-3]}"
                await self.load_extension(ext)
                self.logger.info("Loaded: %s", file[:-3])
            elif os.path.isdir(path) and file not in {"__pycache__"} and not file.startswith("_"):
                await self.load_cogs(path)


if __name__ == "__main__":
    bot = AutosellBot()
    bot.remove_command("help")
    bot.setup_logging()
    bot.run(config.TOKEN, log_handler=None)
