import os

from dotenv import load_dotenv

load_dotenv()

# Discord bot token — set DISCORD_TOKEN in Railway Variables (or in a local .env file)
TOKEN = os.getenv("DISCORD_TOKEN", "")
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not set. Add it in Railway → Variables, "
        "or create a .env file locally (see .env.example)."
    )

# Minecraft account that receives /pay
PAY_ACCOUNT = "develoger"

# Rate in USD per 1 million DonutSMP money (3.1 cents)
RATE_PER_MILLION_USD = 0.031

# Minimum sell amount in millions (100m)
MIN_AMOUNT_MILLIONS = 100

# Shop status shown on the panel
SHOP_STATUS = "Open"  # Open / Closed

# Discord user IDs allowed to post the panel / confirm orders
ADMINS = [
    889090864029257790,
]

# Optional: channel ID where completed sales are announced (0 = DM only / skip)
ANNOUNCE_CHANNEL_ID = 0

# Embed accent color (pinkish-red like the reference)
EMBED_COLOR = 0xE85D75

# Discord channel where !stats develoger is sent to check balance
STATS_CHANNEL_ID = int(os.getenv("STATS_CHANNEL_ID", "1530850630984405102"))
STATS_COMMAND = os.getenv("STATS_COMMAND", "!stats develoger")

AUTO_PAYMENT_ENABLED = os.getenv("AUTO_PAYMENT_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PAYMENT_POLL_SECONDS = int(os.getenv("PAYMENT_POLL_SECONDS", "5"))
