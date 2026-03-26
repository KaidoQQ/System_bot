import os
import logging
from dotenv import load_dotenv
import telebot
from google import genai

load_dotenv("tokens.env")

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("computer_bot")

# ── Credentials ────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BOT_TOKEN      = os.getenv("BOT_TOKEN")

# ── External rates (change here if PLN/USD rate changes) ───────────────────
PLN_TO_USD_RATE: float = 3.62

# ── Singletons ─────────────────────────────────────────────────────────────
bot    = telebot.TeleBot(BOT_TOKEN)
client = genai.Client(api_key=GOOGLE_API_KEY)
