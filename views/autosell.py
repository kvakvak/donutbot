import aiohttp
import discord
from discord import ui

import config
from orders_store import (
    allocate_pay_suffix,
    build_exact_pay,
    get_order,
    next_order_id,
    upsert_order,
)


async def fetch_ltc_usd() -> float | None:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return float(data["litecoin"]["usd"])
    except Exception:
        return None


def format_millions(amount_m: float) -> str:
    if amount_m >= 1000 and amount_m % 1000 == 0:
        return f"{amount_m / 1000:g}b"
    if amount_m == int(amount_m):
        return f"{int(amount_m)}m"
    return f"{amount_m:g}m"


def parse_amount_millions(raw: str) -> float | None:
    text = raw.strip().lower().replace(",", "").replace(" ", "")
    multiplier = 1.0
    if text.endswith("b"):
        multiplier = 1000.0
        text = text[:-1]
    elif text.endswith("m"):
        text = text[:-1]
    try:
        value = float(text) * multiplier
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def payout_usd(amount_m: float) -> float:
    return amount_m * config.RATE_PER_MILLION_USD


def format_rate() -> str:
    cents = config.RATE_PER_MILLION_USD * 100
    return f"**{cents:g} cents** / 1m"


def build_panel_embed() -> discord.Embed:
    min_m = config.MIN_AMOUNT_MILLIONS
    status = config.SHOP_STATUS
    status_emoji = "🟢" if status.lower() == "open" else "🔴"
    cents = config.RATE_PER_MILLION_USD * 100

    embed = discord.Embed(
        title="🍩 DonutSMP Autosell",
        description=(
            "Sell your **DonutSMP money** and get paid instantly in **Litecoin**.\n\n"
            f"💵 **Rate: {cents:g} cents per million** (${config.RATE_PER_MILLION_USD:g} / 1m)"
        ),
        colour=config.EMBED_COLOR,
    )
    embed.add_field(name="💵 Rate", value=format_rate(), inline=True)
    embed.add_field(name=f"{status_emoji} Status", value=f"**{status}**", inline=True)
    embed.add_field(name="📊 Limits", value=f"**{min_m}m** minimum", inline=True)
    embed.add_field(
        name="How it works",
        value=(
            "1️⃣ Click **Sell Money** and enter your IGN + LTC address.\n"
            f"2️⃣ Enter how much you want to sell (**min {min_m}m**).\n"
            "3️⃣ Pay the **exact** amount in-game with `/pay`.\n"
            "4️⃣ You get your LTC as soon as the payment is confirmed (you'll receive a DM)."
        ),
        inline=False,
    )
    embed.set_footer(text=f"Minimum order: {min_m}m · Click the button to start")
    return embed


class SellMoneyButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Sell Money",
        style=discord.ButtonStyle.success,
        emoji="💰",
        custom_id="donut:sell_money",
    )
    async def sell_money(self, interaction: discord.Interaction, button: ui.Button):
        if config.SHOP_STATUS.lower() != "open":
            return await interaction.response.send_message(
                "❌ Autosell is currently **closed**. Please try again later.",
                ephemeral=True,
            )
        await interaction.response.send_modal(SellDetailsModal())


class SellDetailsModal(ui.Modal, title="Sell DonutSMP Money"):
    ign = ui.TextInput(
        label="Minecraft IGN",
        placeholder="Your in-game username",
        min_length=3,
        max_length=16,
        required=True,
    )
    ltc = ui.TextInput(
        label="Litecoin (LTC) Address",
        placeholder="Your LTC address for payout",
        min_length=10,
        max_length=120,
        required=True,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        ign = self.ign.value.strip()
        ltc = self.ltc.value.strip()
        await interaction.response.send_message(
            content=(
                f"✅ **Saved.**\n"
                f"**IGN:** {ign}\n"
                f"**LTC:** `{ltc}`\n"
                f"Click **Continue** to enter how much you want to sell."
            ),
            view=ContinueView(ign=ign, ltc=ltc),
            ephemeral=True,
        )


class ContinueView(ui.View):
    def __init__(self, ign: str, ltc: str):
        super().__init__(timeout=300)
        self.ign = ign
        self.ltc = ltc

    @ui.button(label="Continue", style=discord.ButtonStyle.primary, emoji="➡️")
    async def continue_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            AmountModal(ign=self.ign, ltc=self.ltc)
        )


class AmountModal(ui.Modal, title="How much do you want to sell?"):
    amount = ui.TextInput(
        label="Amount (e.g. 100m or 1b)",
        placeholder=f"Minimum {config.MIN_AMOUNT_MILLIONS}m",
        required=True,
        max_length=20,
    )

    def __init__(self, ign: str, ltc: str):
        super().__init__()
        self.ign = ign
        self.ltc = ltc

    async def on_submit(self, interaction: discord.Interaction) -> None:
        amount_m = parse_amount_millions(self.amount.value)
        if amount_m is None:
            return await interaction.response.send_message(
                "❌ Invalid amount. Use something like `100m` or `1b`.",
                ephemeral=True,
            )
        if amount_m < config.MIN_AMOUNT_MILLIONS:
            return await interaction.response.send_message(
                f"❌ Minimum order is **{config.MIN_AMOUNT_MILLIONS}m**.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        pay_suffix = allocate_pay_suffix()
        if pay_suffix is None:
            return await interaction.followup.send(
                "❌ All payment codes are in use right now. Please try again in a few minutes.",
                ephemeral=True,
            )

        order_id = next_order_id()
        base_money = int(round(amount_m * 1_000_000))
        exact_pay = build_exact_pay(base_money, pay_suffix)
        usd = payout_usd(amount_m)

        ltc_price = await fetch_ltc_usd()
        if ltc_price and ltc_price > 0:
            ltc_amount = usd / ltc_price
            payout_line = (
                f"**{ltc_amount:.8f} LTC** (~${usd:.2f}) for your {format_millions(amount_m)}."
            )
        else:
            ltc_amount = None
            payout_line = f"**~${usd:.2f}** in LTC for your {format_millions(amount_m)}."

        upsert_order(
            order_id,
            {
                "order_id": order_id,
                "discord_id": interaction.user.id,
                "discord_name": str(interaction.user),
                "ign": self.ign,
                "ltc": self.ltc,
                "amount_m": amount_m,
                "base_money": (base_money // 100) * 100,
                "pay_suffix": pay_suffix,
                "exact_pay": exact_pay,
                "usd": usd,
                "ltc_amount": ltc_amount,
                "status": "awaiting_payment",
                "privacy": None,
            },
        )

        embed = discord.Embed(
            title="💰 Send Your Money",
            description=(
                "Pay your money in-game to the account below using this **EXACT** amount:"
            ),
            colour=config.EMBED_COLOR,
        )
        embed.add_field(
            name="Command",
            value=f"```/pay {config.PAY_ACCOUNT} {exact_pay}```",
            inline=False,
        )
        embed.add_field(
            name="\u200b",
            value=(
                f"⚠️ Pay **exactly {exact_pay}** — the last digits identify your order.\n\n"
                f"You'll receive your Litecoin payout as soon as the payment arrives.\n"
                f"**Estimated payout:** {payout_line}\n\n"
                "After the payment I'll ask if you want the sale shown as "
                "🌐 **Public** or 🕵️ **Anonymous**."
            ),
            inline=False,
        )
        embed.set_footer(text=f"Order #{order_id}")

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )


class PrivacyView(ui.View):
    def __init__(self, order_id: int):
        super().__init__(timeout=300)
        self.order_id = order_id

    @ui.button(label="Public", style=discord.ButtonStyle.success, emoji="🌐")
    async def public(self, interaction: discord.Interaction, button: ui.Button):
        await self._choose(interaction, "public")

    @ui.button(label="Anonymous", style=discord.ButtonStyle.secondary, emoji="🕵️")
    async def anonymous(self, interaction: discord.Interaction, button: ui.Button):
        await self._choose(interaction, "anonymous")

    async def _choose(self, interaction: discord.Interaction, privacy: str) -> None:
        order = get_order(self.order_id)
        if order is None:
            return await interaction.response.send_message(
                "❌ Order not found.", ephemeral=True
            )
        if order.get("discord_id") != interaction.user.id:
            return await interaction.response.send_message(
                "❌ This isn't your order.", ephemeral=True
            )

        order["privacy"] = privacy
        order["status"] = "completed"
        upsert_order(self.order_id, order)

        seller = (
            f"**{order['ign']}**"
            if privacy == "public"
            else "🕵️ **Anonymous**"
        )
        announce = discord.Embed(
            title="🍩 Sale Completed",
            description=(
                f"{seller} sold **{format_millions(order['amount_m'])}** "
                f"for **${order['usd']:.2f}** in LTC"
            ),
            colour=0x2ECC71,
        )
        announce.set_footer(text=f"Order #{self.order_id}")

        if config.ANNOUNCE_CHANNEL_ID:
            channel = interaction.client.get_channel(config.ANNOUNCE_CHANNEL_ID)
            if channel is not None:
                try:
                    await channel.send(embed=announce)
                except discord.HTTPException:
                    pass

        await interaction.response.send_message(
            f"✅ Preference saved as **{privacy}**. Thanks for selling!",
            ephemeral=True,
        )
        self.stop()
