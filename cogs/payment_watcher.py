import json
import logging
import os

import discord
from discord.ext import commands, tasks

import config
from discord_stats import DiscordStatsError, fetch_player_money
from order_flow import notify_payment_confirmed
from orders_store import find_awaiting_order_by_exact_pay

STATE_FILE = "watcher_state.json"
logger = logging.getLogger("payment_watcher")


def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


class PaymentWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_balance: int | None = None
        self._poll_warned = False

    async def cog_load(self) -> None:
        if config.STATS_CHANNEL_ID and config.AUTO_PAYMENT_ENABLED:
            state = _load_state()
            saved = state.get("last_balance")
            if saved is not None:
                self._last_balance = int(saved)
            self.check_payments.start()
            logger.info(
                "Payment watcher started (channel=%s, !stats %s, every %ss)",
                config.STATS_CHANNEL_ID,
                config.PAY_ACCOUNT,
                config.PAYMENT_POLL_SECONDS,
            )
        else:
            logger.warning(
                "Payment watcher disabled — set STATS_CHANNEL_ID and "
                "AUTO_PAYMENT_ENABLED=true"
            )

    async def cog_unload(self) -> None:
        self.check_payments.cancel()

    @tasks.loop(seconds=config.PAYMENT_POLL_SECONDS)
    async def check_payments(self) -> None:
        await self._poll_once()

    @check_payments.before_loop
    async def before_check_payments(self) -> None:
        await self.bot.wait_until_ready()

    async def _poll_once(self) -> None:
        try:
            balance = await fetch_player_money(self.bot)
        except DiscordStatsError as exc:
            if not self._poll_warned:
                logger.error("Stats poll failed: %s", exc)
                self._poll_warned = True
            return

        self._poll_warned = False

        if self._last_balance is None:
            self._last_balance = balance
            _save_state({"last_balance": balance})
            logger.info("Payment watcher baseline balance: %s", balance)
            return

        if balance <= self._last_balance:
            return

        delta = balance - self._last_balance
        self._last_balance = balance
        _save_state({"last_balance": balance})

        match = find_awaiting_order_by_exact_pay(delta)
        if match is None:
            logger.warning(
                "Received +%s on %s but no matching pending order",
                delta,
                config.PAY_ACCOUNT,
            )
            return

        order_id, order = match
        suffix = order.get("pay_suffix", delta % 100)
        ok = await notify_payment_confirmed(self.bot, order_id)
        if ok:
            logger.info(
                "Auto-confirmed order #%s (+%s, code %02d, %s)",
                order_id,
                delta,
                int(suffix),
                order.get("ign"),
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PaymentWatcher(bot))
