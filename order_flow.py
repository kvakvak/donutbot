import discord

import config
from orders_store import get_order, upsert_order
from views.autosell import PrivacyView, format_millions


async def notify_payment_confirmed(bot: discord.Client, order_id: int) -> bool:
    """Mark order paid and DM the seller. Returns True if the user was notified."""
    order = get_order(order_id)
    if order is None:
        return False
    if order.get("status") in {"paid", "completed"}:
        return False

    order["status"] = "paid"
    upsert_order(order_id, order)

    user = bot.get_user(order["discord_id"])
    if user is None:
        try:
            user = await bot.fetch_user(order["discord_id"])
        except discord.HTTPException:
            return False

    ltc_line = (
        f"**{order['ltc_amount']:.8f} LTC**"
        if order.get("ltc_amount")
        else f"**~${order['usd']:.2f} in LTC**"
    )
    try:
        await user.send(
            content=(
                f"✅ **Payment detected for Order #{order_id}!**\n"
                f"Payout of {ltc_line} is being sent to:\n`{order['ltc']}`\n\n"
                "Do you want this sale shown as **Public** or **Anonymous**?"
            ),
            view=PrivacyView(order_id=order_id),
        )
    except discord.HTTPException:
        return False

    for admin_id in config.ADMINS:
        admin = bot.get_user(admin_id)
        if admin is None:
            try:
                admin = await bot.fetch_user(admin_id)
            except discord.HTTPException:
                continue
        try:
            await admin.send(
                embed=discord.Embed(
                    title=f"✅ Auto-detected payment — Order #{order_id}",
                    description=(
                        f"**IGN:** `{order['ign']}`\n"
                        f"**Amount:** {format_millions(order['amount_m'])}\n"
                        f"**Exact pay:** `{order['exact_pay']}`\n"
                        f"**LTC:** `{order['ltc']}`\n"
                        f"**USD:** ${order['usd']:.2f}"
                    ),
                    colour=0x2ECC71,
                )
            )
        except discord.HTTPException:
            pass

    return True
