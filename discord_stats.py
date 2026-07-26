import asyncio
import re

import discord

import config


class DiscordStatsError(Exception):
    pass


def _strip(text: str) -> str:
    return text.replace(",", "").strip()


def parse_money(text: str) -> int | None:
    plain = text

    labeled = [
        re.compile(r"(?:money|balance|bal)[:\s]*[\$]?\s*([\d,]+(?:\.\d+)?)", re.I),
        re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:money|coins?)", re.I),
    ]
    for pattern in labeled:
        match = pattern.search(plain)
        if match:
            try:
                return int(float(_strip(match.group(1))))
            except ValueError:
                pass

    numbers = re.findall(r"[\d,]+(?:\.\d+)?", plain)
    best: int | None = None
    for part in numbers:
        try:
            value = int(float(_strip(part)))
        except ValueError:
            continue
        if best is None or value > best:
            best = value
    return best


def _text_from_message(msg: discord.Message) -> str:
    parts: list[str] = []
    if msg.content:
        parts.append(msg.content)
    for embed in msg.embeds:
        if embed.title:
            parts.append(embed.title)
        if embed.description:
            parts.append(embed.description)
        for field in embed.fields:
            parts.append(f"{field.name} {field.value}")
    return "\n".join(parts)


async def fetch_player_money(bot: discord.Client) -> int:
    if not config.STATS_CHANNEL_ID:
        raise DiscordStatsError("STATS_CHANNEL_ID is not set")

    channel = bot.get_channel(config.STATS_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(config.STATS_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        raise DiscordStatsError(
            f"Channel {config.STATS_CHANNEL_ID} is not a text channel"
        )

    cmd = config.STATS_COMMAND
    sent_at = discord.utils.utcnow()
    await channel.send(cmd)

    def check(msg: discord.Message) -> bool:
        if msg.channel.id != config.STATS_CHANNEL_ID:
            return False
        if msg.author.id == bot.user.id:
            return False
        if msg.created_at < sent_at:
            return False
        return parse_money(_text_from_message(msg)) is not None

    try:
        msg = await bot.wait_for("message", check=check, timeout=10.0)
    except asyncio.TimeoutError as exc:
        raise DiscordStatsError(
            f"No stats response for `{cmd}` within 10s in #{channel.name}"
        ) from exc

    money = parse_money(_text_from_message(msg))
    if money is None:
        raise DiscordStatsError("Could not parse money from stats response")
    return money
