import discord
from discord import app_commands
from discord.ext import commands

import config
from order_flow import notify_payment_confirmed
from orders_store import get_order
from views.autosell import (
    SellMoneyButton,
    build_panel_embed,
    format_millions,
)


class Autosell(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_admin(self, user_id: int) -> bool:
        return user_id in config.ADMINS or user_id in getattr(self.bot, "admins", [])

    @app_commands.command(
        name="setupautosell",
        description="Post the DonutSMP Autosell panel in this channel",
    )
    async def setupautosell(self, interaction: discord.Interaction):
        if not self._is_admin(interaction.user.id):
            return await interaction.response.send_message(
                "❌ You don't have permission to do that.", ephemeral=True
            )
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ Run this in a text channel.", ephemeral=True
            )

        await interaction.response.send_message(
            "✅ Panel posted.", ephemeral=True
        )
        await interaction.channel.send(
            embed=build_panel_embed(),
            view=SellMoneyButton(),
        )

    @app_commands.command(
        name="confirmorder",
        description="Confirm an order payment and notify the seller",
    )
    @app_commands.describe(order_id="The order number to confirm")
    async def confirmorder(self, interaction: discord.Interaction, order_id: int):
        if not self._is_admin(interaction.user.id):
            return await interaction.response.send_message(
                "❌ You don't have permission to do that.", ephemeral=True
            )

        order = get_order(order_id)
        if order is None:
            return await interaction.response.send_message(
                f"❌ Order #{order_id} not found.", ephemeral=True
            )
        if order.get("status") == "completed":
            return await interaction.response.send_message(
                f"ℹ️ Order #{order_id} is already completed.", ephemeral=True
            )

        ok = await notify_payment_confirmed(self.bot, order_id)
        if not ok:
            return await interaction.response.send_message(
                f"⚠️ Order #{order_id} marked paid, but I couldn't DM the user.",
                ephemeral=True,
            )

        order = get_order(order_id) or order
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Order Confirmed",
                description=(
                    f"**Order #{order_id}** marked as paid.\n"
                    f"**IGN:** `{order['ign']}`\n"
                    f"**Amount:** {format_millions(order['amount_m'])}\n"
                    f"**Exact pay:** `{order['exact_pay']}`\n"
                    f"**LTC address:** `{order['ltc']}`"
                ),
                colour=0x2ECC71,
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="orderinfo",
        description="Look up an autosell order",
    )
    @app_commands.describe(order_id="The order number")
    async def orderinfo(self, interaction: discord.Interaction, order_id: int):
        if not self._is_admin(interaction.user.id):
            return await interaction.response.send_message(
                "❌ You don't have permission to do that.", ephemeral=True
            )
        order = get_order(order_id)
        if order is None:
            return await interaction.response.send_message(
                f"❌ Order #{order_id} not found.", ephemeral=True
            )

        embed = discord.Embed(
            title=f"Order #{order_id}",
            colour=config.EMBED_COLOR,
        )
        for key, value in order.items():
            embed.add_field(name=str(key), value=f"`{value}`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="setstatus",
        description="Set autosell status (Open / Closed)",
    )
    @app_commands.describe(status="Open or Closed")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Open", value="Open"),
            app_commands.Choice(name="Closed", value="Closed"),
        ]
    )
    async def setstatus(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        if not self._is_admin(interaction.user.id):
            return await interaction.response.send_message(
                "❌ You don't have permission to do that.", ephemeral=True
            )
        config.SHOP_STATUS = status.value
        await interaction.response.send_message(
            f"✅ Shop status set to **{status.value}**. Re-run `/setupautosell` to refresh the panel embed.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Autosell(bot))
