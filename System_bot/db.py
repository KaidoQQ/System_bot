"""
db.py  —  database layer + in-memory user cache.

All SQLite access lives here so the rest of the code never touches
sqlite3 directly.
"""

import json
import sqlite3
import csv
import atexit
from datetime import datetime
from typing import Optional

from config import logger

DB_PATH = "computers.db"

# ── In-memory cache: user_id → user_dict ───────────────────────────────────
_cache: dict[int, dict] = {}


# ══════════════════════════════════════════════════════════════════════════════
# Low-level helpers
# ══════════════════════════════════════════════════════════════════════════════

def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ══════════════════════════════════════════════════════════════════════════════
# Schema
# ══════════════════════════════════════════════════════════════════════════════

def init_database() -> None:
    with _connect() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id          INTEGER PRIMARY KEY,
                current_computer INTEGER,
                computers_data   TEXT,
                last_update      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS components_price (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                component_type      TEXT,
                component_name      TEXT UNIQUE,
                average_price_dollar INTEGER,
                category            TEXT,
                component_url       TEXT
            )
        ''')
        conn.commit()
    logger.info("✅ Database initialised")


# ══════════════════════════════════════════════════════════════════════════════
# CSV import
# ══════════════════════════════════════════════════════════════════════════════

def import_prices_from_csv(path: str = "components.csv") -> None:
    logger.info("📂 Checking CSV for new items…")
    try:
        with _connect() as conn, open(path, encoding="utf-8", errors="replace") as f:
            added = 0
            for row in csv.reader(f, delimiter=";"):
                if not row or "component_type" in row[0]:
                    continue
                if len(row) < 4:
                    continue
                try:
                    comp_type  = row[0].strip()
                    comp_name  = row[1].strip()
                    raw_price  = row[2].strip()
                    price      = int(raw_price) if raw_price else 0
                    category   = row[3].strip()
                    url        = row[4].strip() if len(row) >= 5 else None

                    conn.execute(
                        "INSERT OR IGNORE INTO components_price "
                        "(component_type, component_name, average_price_dollar, category, component_url) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (comp_type, comp_name, price, category, url),
                    )
                    if conn.execute("SELECT changes()").fetchone()[0]:
                        added += 1
                except Exception as e:
                    logger.warning("CSV row error: %s", e)
            conn.commit()
        logger.info("✅ CSV import done. Added: %d", added)
    except FileNotFoundError:
        logger.error("❌ '%s' not found", path)
    except Exception as e:
        logger.error("❌ CSV global error: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# Users
# ══════════════════════════════════════════════════════════════════════════════

def save_user_to_db(user_id: int, user_data: dict) -> bool:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO users (user_id, current_computer, computers_data) "
                "VALUES (?, ?, ?)",
                (user_id, user_data["current_computer"], json.dumps(user_data["computers"], default=str)),
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error("❌ Failed to save user %d: %s", user_id, e)
        return False


def load_user_from_db(user_id: int) -> Optional[dict]:
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT current_computer, computers_data FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        computers = []
        if row[1]:
            computers = json.loads(row[1])
            for c in computers:
                if isinstance(c.get("created_at"), str):
                    c["created_at"] = datetime.fromisoformat(c["created_at"])

        return {"current_computer": row[0], "computers": computers, "awaiting_input": None}
    except Exception as e:
        logger.error("❌ Failed to load user %d: %s", user_id, e)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Components
# ══════════════════════════════════════════════════════════════════════════════

def product_link(component_name: str) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT component_url FROM components_price WHERE component_name = ?",
            (component_name,),
        ).fetchone()
    return row[0] if row and row[0] else None


def search_component_price(search_query: str, component_type: Optional[str] = None) -> list[dict]:
    """
    Returns a list of component dicts sorted by relevance score (highest first).
    Tries AND match first, falls back to OR if nothing found.
    """
    from utils import score_relevance  # local import to avoid circular

    words = [w for w in search_query.lower().split() if len(w) > 2]
    if not words:
        return []

    def _run_query(operator: str) -> list:
        placeholders = f" {operator} ".join(["component_name LIKE ?"] * len(words))
        sql = f"SELECT * FROM components_price WHERE {placeholders}"
        params = [f"%{w}%" for w in words]
        with _connect() as conn:
            return conn.execute(sql, params).fetchall()

    rows = _run_query("AND")
    if not rows:
        rows = _run_query("OR")

    results = []
    for row in rows:
        results.append({
            "id":       row[0],
            "type":     row[1],
            "name":     row[2],
            "price":    row[3],
            "category": row[4],
            "score":    score_relevance(words, row[2]),
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


# ══════════════════════════════════════════════════════════════════════════════
# Cache helpers (used throughout the app)
# ══════════════════════════════════════════════════════════════════════════════

def get_user_data(user_id: int) -> dict:
    if user_id not in _cache:
        db_data = load_user_from_db(user_id)
        if db_data:
            _cache[user_id] = db_data
            logger.info("Loaded user %d from DB", user_id)
        else:
            _cache[user_id] = {"current_computer": None, "computers": [], "awaiting_input": None}
            save_user_to_db(user_id, _cache[user_id])
            logger.info("Created new user %d", user_id)
    return _cache[user_id]


def auto_save(user_id: int) -> None:
    """Persist user data and recalculate total price for current build."""
    from utils import count_total_price, get_current_computer  # avoid circular

    if user_id in _cache:
        computer = get_current_computer(user_id)
        if computer:
            count_total_price(computer)
        ok = save_user_to_db(user_id, _cache[user_id])
        if ok:
            logger.debug("💾 Auto-saved user %d", user_id)
        else:
            logger.warning("❌ Failed to auto-save user %d", user_id)


def _save_all_on_exit() -> None:
    logger.info("💾 Saving all users before exit…")
    for uid, data in _cache.items():
        save_user_to_db(uid, data)
    logger.info("✅ All users saved")


atexit.register(_save_all_on_exit)
