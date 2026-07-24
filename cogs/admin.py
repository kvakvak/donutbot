import discord
from discord import app_commands
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reload")
    async def reload(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id not in self.bot.admins:
            return
        await self.bot.reload_extension(cog)
        return await interaction.response.send_message(
            embed=discord.Embed(
                title="Reloaded Cogs",
                description=cog,
            )
        )

    @reload.autocomplete(name="cog")
    async def autocomplete_callback(
        self, interaction: discord.Interaction, current: str
    ):
        options = [cog for cog in self.bot.extensions.keys()]
        return [
            app_commands.Choice(name=option, value=option)
            for option in options
            if current.lower() in option.lower()
        ]

    @commands.group(invoke_without_command=True)
    async def sync(self, ctx: commands.Context) -> None:
        """Sync global slash commands (use !sync guild for instant guild-only sync)."""
        if ctx.author.id not in self.bot.admins:
            return await ctx.send("❌ You don't have permission to do that.")
        synced = await self.bot.tree.sync()
        names = ", ".join(f"/{c.name}" for c in synced) or "none"
        await ctx.send(
            f"✅ Successfully synced **{len(synced)}** global command(s): {names}"
        )

    @sync.command(name="guild")
    async def sync_guild(self, ctx: commands.Context) -> None:
        """Instant guild sync (copies global commands into this server)."""
        if ctx.author.id not in self.bot.admins:
            return await ctx.send("❌ You don't have permission to do that.")
        if ctx.guild is None:
            return await ctx.send("❌ Run this in a server, not DMs.")
        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)
        names = ", ".join(f"/{c.name}" for c in synced) or "none"
        await ctx.send(
            f"✅ Guild sync: **{len(synced)}** command(s) in this server: {names}"
        )

    @sync.command(name="global")
    async def sync_global(self, ctx: commands.Context):
        if ctx.author.id not in self.bot.admins:
            return await ctx.send("❌ You don't have permission to do that.")
        synced = await self.bot.tree.sync()
        names = ", ".join(f"/{c.name}" for c in synced) or "none"
        await ctx.send(
            f"✅ Successfully synced **{len(synced)}** global command(s): {names}"
        )

    @sync.command(name="duplicate")
    async def sync_clear_duplicates(self, ctx: commands.Context):
        if ctx.author.id not in self.bot.admins:
            return
        for guild in self.bot.guilds:
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)
        await ctx.send(f"Successfully cleared duplicates")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
