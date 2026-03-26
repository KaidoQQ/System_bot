"""
parsing.py  —  Amazon price updater.

Run standalone:  python parsing.py
"""

import re
import time
import random
import sqlite3
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import PLN_TO_USD_RATE

logger = logging.getLogger("parser")

DB_PATH = "computers.db"

HEADERS = {
    "User-Agent":                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                                 "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language":           "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding":           "gzip, deflate, br",
    "Connection":                "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":            "document",
    "Sec-Fetch-Mode":            "navigate",
    "Sec-Fetch-Site":            "none",
    "Sec-Fetch-User":            "?1",
    "Cache-Control":             "max-age=0",
}

# Retry settings
MAX_RETRIES  = 3
RETRY_DELAY  = 5   # seconds between retries
SLEEP_RANGE  = (10, 15)  # seconds between items


def get_amazon_price(url: str, retries: int = MAX_RETRIES) -> Optional[int]:
    """
    Fetch a product price from Amazon.
    Returns price in USD (converts PLN if the URL is amazon.pl).
    Returns None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)

            if response.status_code != 200:
                logger.warning("  HTTP %d (attempt %d/%d)", response.status_code, attempt, retries)
                time.sleep(RETRY_DELAY)
                continue

            soup  = BeautifulSoup(response.text, "html.parser")
            price_el = soup.select_one(".a-price-whole")

            if not price_el:
                title = soup.title.text.strip() if soup.title else "No title"
                logger.warning("  ⚠️ Price element not found. Page title: '%s'", title)
                return None

            raw_price = re.sub(r"\D", "", price_el.get_text())
            price     = int(raw_price)

            # Convert PLN → USD if needed
            if "amazon.pl" in url:
                price = round(price / PLN_TO_USD_RATE)

            return price

        except requests.RequestException as e:
            logger.warning("  Network error (attempt %d/%d): %s", attempt, retries, e)
            time.sleep(RETRY_DELAY)

    logger.error("  ❌ Failed after %d attempts: %s", retries, url)
    return None


def update_prices() -> None:
    logger.info("🚀 Starting price update…")

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT component_name, average_price_dollar, component_url "
            "FROM components_price "
            "WHERE component_url IS NOT NULL AND component_url != ''",
        ).fetchall()

    updated = 0
    failed  = 0

    for name, old_price, url in rows:
        logger.info("Checking: %s", name)
        new_price = get_amazon_price(url)

        if new_price is None:
            logger.warning("  ⚠️ Could not fetch price for %s", name)
            failed += 1
        elif new_price == old_price:
            logger.info("  Price unchanged ($%d)", old_price)
        else:
            logger.info("  💰 New price: $%d → $%d", old_price, new_price)
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE components_price SET average_price_dollar = ? WHERE component_name = ?",
                    (new_price, name),
                )
                conn.commit()
            updated += 1

        time.sleep(random.randint(*SLEEP_RANGE))

    logger.info("🏁 Done. Updated: %d | Failed: %d | Total: %d", updated, failed, len(rows))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    update_prices()
