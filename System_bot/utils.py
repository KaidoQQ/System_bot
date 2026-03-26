"""
utils.py  —  component config, AI analysis, build helpers.

COMPONENT_CONFIG is the single source of truth for all component metadata.
Adding a new component type only requires adding one entry here.
"""

from datetime import datetime
from config import client, logger


# ══════════════════════════════════════════════════════════════════════════════
# Component config  (single source of truth)
# ══════════════════════════════════════════════════════════════════════════════
#
# Keys used throughout the app:
#   key        – field name in the computer dict   (e.g. 'cpu')
#   price_key  – price field in the computer dict  (e.g. 'cpu_price')
#   emoji      – button/message emoji
#   label      – human-readable name
#   select_cb  – prefix for inline button callback_data when picking from list
#   manual_cb  – callback_data for "Enter manually" button
#
COMPONENT_CONFIG: dict[str, dict] = {
    "cpu": {
        "key":       "cpu",
        "price_key": "cpu_price",
        "emoji":     "🔧",
        "label":     "CPU",
        "select_cb": "select_cpu",
        "manual_cb": "enter_price_cpu",
    },
    "ram": {
        "key":       "ram",
        "price_key": "ram_price",
        "emoji":     "💾",
        "label":     "RAM",
        "select_cb": "select_ram",
        "manual_cb": "enter_price_ram",
    },
    "gpu": {
        "key":       "gpu",
        "price_key": "gpu_price",
        "emoji":     "🖳",
        "label":     "GPU",
        "select_cb": "select_gpu",
        "manual_cb": "enter_price_gpu",
    },
    "storage": {
        "key":       "storage",
        "price_key": "storage_price",
        "emoji":     "📦",
        "label":     "Storage",
        "select_cb": "select_stor",
        "manual_cb": "enter_price_stor",
    },
    "motherboard": {
        "key":       "motherboard",
        "price_key": "motherboard_price",
        "emoji":     "📁",
        "label":     "Motherboard",
        "select_cb": "select_mam",
        "manual_cb": "enter_price_mam",
    },
}

# Map awaiting_input states → component type  (covers both add & change flows)
STATE_TO_COMP: dict[str, str] = {
    "cpu":          "cpu",
    "ram":          "ram",
    "gpu":          "gpu",
    "storage":      "storage",
    "motherboard":  "motherboard",
    "change_cpu":   "cpu",
    "change_ram":   "ram",
    "change_gpu":   "gpu",
    "change_stor":  "storage",
    "change_mam":   "motherboard",
}

# ── select_* callback prefix → component type ─────────────────────────────
SELECT_CB_TO_COMP: dict[str, str] = {
    cfg["select_cb"]: comp_type
    for comp_type, cfg in COMPONENT_CONFIG.items()
}


# ══════════════════════════════════════════════════════════════════════════════
# Build helpers
# ══════════════════════════════════════════════════════════════════════════════

def create_computer_dict(computer_id: int, name: str) -> dict:
    return {
        "id":                computer_id,
        "name":              name,
        "cpu":               None,
        "cpu_price":         None,
        "ram":               None,
        "ram_price":         None,
        "gpu":               None,
        "gpu_price":         None,
        "storage":           None,
        "storage_price":     None,
        "motherboard":       None,
        "motherboard_price": None,
        "total_price":       None,
        "created_at":        datetime.now(),
    }


def is_build_complete(computer: dict) -> bool:
    return all(computer.get(cfg["key"]) for cfg in COMPONENT_CONFIG.values())


def get_build_progress(computer: dict) -> str:
    filled = sum(1 for cfg in COMPONENT_CONFIG.values() if computer.get(cfg["key"]))
    total  = len(COMPONENT_CONFIG)
    return f"🚧 Build progress: {filled}/{total} components"


def count_total_price(computer: dict) -> None:
    """Recalculate and store total_price in the computer dict (mutates in place)."""
    computer["total_price"] = sum(
        int(computer[cfg["price_key"]])
        for cfg in COMPONENT_CONFIG.values()
        if computer.get(cfg["price_key"])
    )


def get_current_computer(user_id: int) -> dict | None:
    from db import get_user_data  # local import to avoid circular
    ud = get_user_data(user_id)
    current_id = ud["current_computer"]

    if current_id is None and ud["computers"]:
        ud["current_computer"] = ud["computers"][0]["id"]
        return ud["computers"][0]

    for computer in ud["computers"]:
        if computer["id"] == current_id:
            return computer
    return None


def create_new_computer(user_id: int, computer_name: str | None = None) -> None:
    from db import get_user_data, auto_save  # local import
    ud = get_user_data(user_id)

    # FIX: use max(existing ids) + 1 instead of len() so IDs stay unique
    # after deletions.
    existing_ids = [c["id"] for c in ud["computers"]]
    computer_id  = max(existing_ids, default=0) + 1

    if not computer_name:
        computer_name = f"My computer #{computer_id}"

    ud["computers"].append(create_computer_dict(computer_id, computer_name))
    ud["current_computer"] = computer_id
    auto_save(user_id)


# ══════════════════════════════════════════════════════════════════════════════
# Search scoring
# ══════════════════════════════════════════════════════════════════════════════

def score_relevance(search_words: list[str], component_name: str) -> int:
    """
    Returns a higher score when search words appear earlier in component_name.
    Exact match at position 0 → +100, position 1 → +90, …
    """
    name_words = component_name.lower().split()
    score = 0
    for word in search_words:
        for pos, name_word in enumerate(name_words):
            if word == name_word:
                score += max(100 - pos * 10, 0)
    return score


# ══════════════════════════════════════════════════════════════════════════════
# AI
# ══════════════════════════════════════════════════════════════════════════════

def analyze_build_with_ai(computer: dict) -> str:
    prompt = (
        "You are an expert in assembling computers. Evaluate the build below: "
        "check component compatibility, give 5 improvement tips, and rate it 1–10.\n\n"
        f"CPU:         {computer['cpu']}\n"
        f"RAM:         {computer['ram']}\n"
        f"GPU:         {computer['gpu']}\n"
        f"Storage:     {computer['storage']}\n"
        f"Motherboard: {computer['motherboard']}\n"
        f"Total price: ${computer['total_price']}\n\n"
        "Write plain text without any Markdown symbols (* _ ` #) so Telegram displays it correctly."
    )
    try:
        response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
        return response.text
    except Exception as e:
        logger.error("AI error: %s", e)
        return "Failed to analyse the build. Please try again later."
