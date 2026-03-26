"""
main.py  —  entry point.

Run:  python main.py
"""

import config          # sets up logging, bot, client
import handlers        # registers all @bot handlers  # noqa: F401
from db import init_database
from config import bot, logger, GOOGLE_API_KEY, BOT_TOKEN


def main() -> None:
    logger.info("🔐 Loading configuration…")
    logger.info("✅ Google API Key: %s", "yes" if GOOGLE_API_KEY else "NO — check tokens.env")
    logger.info("✅ Bot Token:      %s", "yes" if BOT_TOKEN      else "NO — check tokens.env")

    init_database()

    # Uncomment once to seed the database from components.csv:
    # from db import import_prices_from_csv
    # import_prices_from_csv()

    logger.info("🖥️ Computer Builder Bot is running…")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
