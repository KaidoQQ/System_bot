"""
handlers.py  —  all Telegram bot handlers.

Key improvements over the original:
  • Unified _handle_component_input() replaces 10 nearly-identical elif blocks.
  • Unified delete_option() replaces 5 identical handlers with a data map.
  • Unified show_buttons_with_components() uses COMPONENT_CONFIG — no more typos.
  • All bugs fixed (found_links, key typos, computer_id, etc.).
"""

from telebot import types

from config import bot, logger
from db import get_user_data, auto_save, search_component_price, product_link
from utils import (
    COMPONENT_CONFIG,
    STATE_TO_COMP,
    SELECT_CB_TO_COMP,
    get_current_computer,
    create_new_computer,
    is_build_complete,
    get_build_progress,
    analyze_build_with_ai,
)


# ══════════════════════════════════════════════════════════════════════════════
# Shared markup builders
# ══════════════════════════════════════════════════════════════════════════════

def _back_btn() -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton("⬅️ Back to menu", callback_data="back_menu")


def _main_menu_markup(user_id: int) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🖥️ Create new system",  callback_data="tab1"))
    markup.row(
        types.InlineKeyboardButton("👾 View all systems",   callback_data="tab2"),
        types.InlineKeyboardButton("🔄 Upgrade system",     callback_data="tab3"),
    )
    markup.row(
        types.InlineKeyboardButton("📚 View tutorials",     callback_data="tab4"),
        types.InlineKeyboardButton("📊 Web Dashboard",      url=f"http://127.0.0.1:5000/user/{user_id}"),
    )
    return markup


def _after_component_markup(is_change: bool, computer: dict) -> types.InlineKeyboardMarkup:
    """Buttons shown after a component is successfully added or changed."""
    markup = types.InlineKeyboardMarkup()
    if is_build_complete(computer):
        markup.row(types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete"))
    if is_change:
        markup.row(types.InlineKeyboardButton("🔄 Change next component", callback_data="ch_component"))
    else:
        markup.row(types.InlineKeyboardButton("🔧 Add next component", callback_data="add_next_component"))
    markup.row(_back_btn())
    return markup


def _component_menu_markup(prefix: str) -> types.InlineKeyboardMarkup:
    """Generic component-choice keyboard (Add / Change / Delete menus share the same layout)."""
    labels = {
        "add_":    ("Add",    "add_cpu",    "add_ram",    "add_gpu",    "add_stor",    "add_mb"),
        "change_": ("Change", "change_cpu", "change_ram", "change_gpu", "change_stor", "change_mam"),
        "delete_": ("Delete", "delete_cpu", "delete_ram", "delete_gpu", "delete_stor", "delete_mam"),
    }
    verb, cb_cpu, cb_ram, cb_gpu, cb_stor, cb_mb = labels[prefix]
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"🔧 {verb} CPU",         callback_data=cb_cpu))
    markup.row(
        types.InlineKeyboardButton(f"💾 {verb} RAM",        callback_data=cb_ram),
        types.InlineKeyboardButton(f"🖳 {verb} GPU",        callback_data=cb_gpu),
    )
    markup.row(
        types.InlineKeyboardButton(f"📦 {verb} Storage",    callback_data=cb_stor),
        types.InlineKeyboardButton(f"📁 {verb} Motherboard",callback_data=cb_mb),
    )
    markup.row(_back_btn())
    return markup


# ══════════════════════════════════════════════════════════════════════════════
# /start
# ══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    get_user_data(user_id)  # ensures user exists in cache & DB
    bot.send_message(
        message.chat.id,
        "✨ Welcome to the Computer Builder Bot! ✨",
        reply_markup=_main_menu_markup(user_id),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Back to menu
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "back_menu")
def back_menu(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="✨ Welcome to the Telegram bot where you can create and test your system ✨",
        reply_markup=_main_menu_markup(call.from_user.id),
    )
    bot.answer_callback_query(call.id)


# ══════════════════════════════════════════════════════════════════════════════
# Tabs
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data.startswith("tab"))
def handle_tabs(call):
    tab = call.data.replace("tab", "")
    markup = types.InlineKeyboardMarkup()

    texts = {
        "1": "🖥️ Create new system\n\nWhat do you want to do first:",
        "2": "👾 View all systems\n\nChoose the system:",
        "3": "🔄 Upgrade system\n\nChoose the system:",
        "4": "📚 View tutorials\n\nChoose the tutorial:",
    }

    if tab == "1":
        markup.row(
            types.InlineKeyboardButton("💻 Create new computer",        callback_data="new_comp"),
            types.InlineKeyboardButton("🔧 Add components",              callback_data="new_components"),
        )
        markup.row(_back_btn())

    elif tab == "2":
        markup.row(types.InlineKeyboardButton("💻 Check all computers", callback_data="choose_comp"))
        markup.row(_back_btn())

    elif tab == "3":
        markup.row(types.InlineKeyboardButton("💻 Choose the computer", callback_data="choose_comp"))
        markup.row(_back_btn())

    elif tab == "4":
        tutorial_links = [
            ("What is CPU",         "https://www.arm.com/glossary/cpu"),
            ("What is RAM",         "https://www.intel.com/content/www/us/en/tech-tips-and-tricks/computer-ram.html"),
            ("What is GPU",         "https://www.intel.com/content/www/us/en/products/docs/processors/what-is-a-gpu.html"),
            ("What is Storage",     "https://www.intel.com/content/www/us/en/search.html#q=storage"),
            ("What is Motherboard", "https://www.intel.com/content/www/us/en/gaming/resources/how-to-choose-a-motherboard.html"),
        ]
        for text, url in tutorial_links:
            markup.add(types.InlineKeyboardButton(text, url=url))
        markup.add(_back_btn())

    else:
        markup.add(_back_btn())

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=texts.get(tab, "Unknown tab"),
        reply_markup=markup,
    )
    bot.answer_callback_query(call.id)


# ══════════════════════════════════════════════════════════════════════════════
# Computer creation
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "new_comp")
def create_new_comp(call):
    ud = get_user_data(call.from_user.id)
    ud["awaiting_input"] = "computer_name"
    bot.send_message(call.message.chat.id, "💻 Enter a name for your computer:")


@bot.callback_query_handler(func=lambda call: call.data == "new_components")
def show_components_menu(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👽 Choose what you want to add:",
        reply_markup=_component_menu_markup("add_"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Add component triggers (sets awaiting_input)
# ══════════════════════════════════════════════════════════════════════════════

_ADD_CB_TO_COMP = {
    "add_cpu":  "cpu",
    "add_ram":  "ram",
    "add_gpu":  "gpu",
    "add_stor": "storage",
    "add_mb":   "motherboard",
}

@bot.callback_query_handler(func=lambda call: call.data in _ADD_CB_TO_COMP or call.data == "add_next_component")
def choose_option_to_add(call):
    user_id = call.from_user.id
    ud = get_user_data(user_id)

    if not get_current_computer(user_id):
        bot.send_message(call.message.chat.id, "❌ You don't have any computers yet!")
        return

    if call.data == "add_next_component":
        bot.send_message(
            call.message.chat.id,
            "Choose what you want to add:",
            reply_markup=_component_menu_markup("add_"),
        )
        return

    comp_type = _ADD_CB_TO_COMP[call.data]
    cfg = COMPONENT_CONFIG[comp_type]
    ud["awaiting_input"] = comp_type
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, f"{cfg['emoji']} Enter {cfg['label']} model:")


# ══════════════════════════════════════════════════════════════════════════════
# Change component triggers
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "ch_component")
def change_component(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🧐 Choose component to change:",
        reply_markup=_component_menu_markup("change_"),
    )

_CHANGE_CB_TO_STATE = {
    "change_cpu":  ("change_cpu",  "cpu"),
    "change_ram":  ("change_ram",  "ram"),
    "change_gpu":  ("change_gpu",  "gpu"),
    "change_stor": ("change_stor", "storage"),
    "change_mam":  ("change_mam",  "motherboard"),
}

@bot.callback_query_handler(func=lambda call: call.data in _CHANGE_CB_TO_STATE)
def change_option(call):
    user_id = call.from_user.id
    ud = get_user_data(user_id)
    computer = get_current_computer(user_id)

    state, comp_type = _CHANGE_CB_TO_STATE[call.data]
    cfg = COMPONENT_CONFIG[comp_type]

    ud["awaiting_input"] = state
    current = computer.get(cfg["key"]) or "Not set"
    bot.send_message(
        call.message.chat.id,
        f"{cfg['emoji']} Change {cfg['label']}\nCurrent: {current}\n\nEnter new {cfg['label']} model:",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Delete component  (unified — was 5 separate handlers)
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "del_component")
def show_delete_menu(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🗑️ Choose component to delete:",
        reply_markup=_component_menu_markup("delete_"),
    )

_DELETE_CB_MAP = {
    "delete_cpu":  "cpu",
    "delete_ram":  "ram",
    "delete_gpu":  "gpu",
    "delete_stor": "storage",
    "delete_mam":  "motherboard",
}

@bot.callback_query_handler(func=lambda call: call.data in _DELETE_CB_MAP)
def delete_option(call):
    user_id = call.from_user.id
    computer = get_current_computer(user_id)

    comp_type = _DELETE_CB_MAP[call.data]
    cfg = COMPONENT_CONFIG[comp_type]

    computer[cfg["key"]]       = None
    computer[cfg["price_key"]] = None
    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🗑️ Delete next component", callback_data="del_component"))
    markup.row(_back_btn())

    bot.send_message(
        call.message.chat.id,
        f"💔 {cfg['emoji']} {cfg['label']} deleted\n\nComponent removed from {computer['name']}",
        reply_markup=markup,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Select component from search results  (unified — was 5 separate handlers)
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] in SELECT_CB_TO_COMP)
def show_buttons_with_components(call):
    user_id = call.from_user.id
    computer = get_current_computer(user_id)

    parts = call.data.split(":")
    cb_prefix      = parts[0]
    component_name = parts[2]
    component_price = int(parts[3])

    comp_type = SELECT_CB_TO_COMP[cb_prefix]
    cfg = COMPONENT_CONFIG[comp_type]

    computer[cfg["key"]]       = component_name
    computer[cfg["price_key"]] = component_price
    auto_save(user_id)

    progress = get_build_progress(computer)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ {cfg['label']} selected: '{component_name}' — ${component_price}\n{progress}",
        reply_markup=_after_component_markup(is_change=False, computer=computer),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Manual price entry
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_price_"))
def manually_price_enter(call):
    ud = get_user_data(call.from_user.id)
    comp_type = call.data.replace("enter_price_", "")
    ud["awaiting_input"] = f"manual_name_{comp_type}"
    bot.send_message(call.message.chat.id, f"✍️ Enter name of: {comp_type.upper()}:")
    bot.answer_callback_query(call.id)


# ══════════════════════════════════════════════════════════════════════════════
# View components
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "view_components")
def view_components(call):
    computer = get_current_computer(call.from_user.id)
    if not computer:
        bot.send_message(call.message.chat.id, "❌ No computer found!")
        return

    created = computer["created_at"]
    date_str = created.strftime("%d.%m.%Y") if hasattr(created, "strftime") else str(created)

    lines = [f"🖥️ **Computer Components:**\n", f"📅 Created: {date_str}\n\n**Components:**"]
    for cfg in COMPONENT_CONFIG.values():
        val = computer.get(cfg["key"]) or "❌ Not set"
        lines.append(f"{cfg['emoji']} **{cfg['label']}:** {val}")
    total = computer.get("total_price") or "❌ Not calculated"
    lines.append(f"💰 **Total price: {total}$**")

    markup = types.InlineKeyboardMarkup()
    markup.row(_back_btn())

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="\n".join(lines),
        reply_markup=markup,
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Choose / switch computer
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "choose_comp")
def choose_comp(call):
    user_id = call.from_user.id
    ud = get_user_data(user_id)
    computers = ud["computers"]
    markup = types.InlineKeyboardMarkup()

    if not computers:
        markup.row(_back_btn())
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ You need to create your first computer",
            reply_markup=markup,
        )
        return

    for c in computers:
        markup.add(types.InlineKeyboardButton(f"💻 {c['name']}", callback_data=f"comp_{c['id']}"))
    markup.add(_back_btn())

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👾 Choose your computer:",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("comp_"))
def option_with_computers(call):
    user_id = call.from_user.id
    ud = get_user_data(user_id)
    computer_id = int(call.data.replace("comp_", ""))
    ud["current_computer"] = computer_id

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🤖 AI Check",          callback_data="ai_check"),
        types.InlineKeyboardButton("🛒 Buy products",       callback_data="buy_component"),
    )
    markup.row(
        types.InlineKeyboardButton("👀 View components",    callback_data="view_components"),
        types.InlineKeyboardButton("🗑️ Delete component",   callback_data="del_component"),
        types.InlineKeyboardButton("🆙 Change component",   callback_data="ch_component"),
    )
    markup.row(_back_btn())

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🦾 Choose an option:",
        reply_markup=markup,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Build complete
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "build_complete")
def build_complete(call):
    computer = get_current_computer(call.from_user.id)

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("👀 View Components",      callback_data="view_components"),
        types.InlineKeyboardButton("🔄 Upgrade system",       callback_data="ch_component"),
    )
    markup.row(
        types.InlineKeyboardButton("🛒 Buy products",          callback_data="buy_component"),
        types.InlineKeyboardButton("🖥️ Create New",            callback_data="new_comp"),
        types.InlineKeyboardButton("🤖 AI Check",              callback_data="ai_check"),
    )
    markup.row(_back_btn())

    lines = [
        f"🎉 Build Complete! 🎉\n",
        f"🖥️ {computer['name']} is ready!\n",
        "All components:",
    ]
    for cfg in COMPONENT_CONFIG.values():
        lines.append(f"{cfg['emoji']} {computer.get(cfg['key']) or 'Not set'}")
    lines.append(f"💰 ${computer.get('total_price') or 0}\n")
    lines.append("Your dream computer is assembled!")

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="\n".join(lines),
        reply_markup=markup,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Buy products
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "buy_component")
def buy_component(call):
    computer = get_current_computer(call.from_user.id)
    markup = types.InlineKeyboardMarkup()
    found_links = False  # FIX: was used before assignment → UnboundLocalError

    for cfg in COMPONENT_CONFIG.values():
        name = computer.get(cfg["key"])
        if name:
            link = product_link(name)
            if link:
                found_links = True
                markup.add(types.InlineKeyboardButton(f"🛒 Buy {cfg['label']}: {name}", url=link))

    markup.add(types.InlineKeyboardButton("⬅️ Back to Build", callback_data="build_complete"))

    msg = (
        "🛒 **Shopping List**\nHere are the links to buy your components:"
        if found_links else
        "😕 **No links found.**\nWe couldn't find shop links for these components in our database."
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=msg,
        reply_markup=markup,
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# AI check
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data == "ai_check")
def ai_check(call):
    computer = get_current_computer(call.from_user.id)
    response = analyze_build_with_ai(computer)

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🔄 Upgrade system", callback_data="ch_component"),
        types.InlineKeyboardButton("🖥️ Create New",     callback_data="new_comp"),
    )
    markup.row(_back_btn())

    lines = [f"🖥️ **{computer['name']}**\n", "Components:"]
    for cfg in COMPONENT_CONFIG.values():
        lines.append(f"{cfg['emoji']} {computer.get(cfg['key']) or 'Not set'}")
    lines.append(f"💰 ${computer.get('total_price') or 0}\n")
    lines.append("**What AI thinks about your build:**\n")
    lines.append(response)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="\n".join(lines),
        reply_markup=markup,
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Unified text input handler
# ══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda message: True)
def handle_text_input(message):
    user_id = message.from_user.id
    ud = get_user_data(user_id)
    state = ud.get("awaiting_input")

    if state == "computer_name":
        _handle_computer_name(message, user_id, ud)

    elif state and state.startswith("manual_name_"):
        _handle_manual_name(message, user_id, ud, state)

    elif state and state.startswith("manual_price_"):
        _handle_manual_price(message, user_id, ud, state)

    elif state in STATE_TO_COMP:
        is_change = state.startswith("change_")
        _handle_component_input(message, user_id, ud, STATE_TO_COMP[state], is_change)


# ── Sub-handlers ──────────────────────────────────────────────────────────────

def _handle_computer_name(message, user_id: int, ud: dict) -> None:
    name = message.text
    create_new_computer(user_id, name)
    ud["awaiting_input"] = None

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔧 Add components", callback_data="new_components"))
    markup.row(_back_btn())

    bot.send_message(
        message.chat.id,
        f"✅ Computer '{name}' created! Now add components.",
        reply_markup=markup,
    )


def _handle_manual_name(message, user_id: int, ud: dict, state: str) -> None:
    comp_type = state.split("_", 2)[-1]  # 'manual_name_cpu' → 'cpu'
    ud["temp_manual_name"] = message.text
    ud["awaiting_input"]   = f"manual_price_{comp_type}"
    bot.send_message(message.chat.id, f"💰 Now enter the price for '{message.text}' (in $):")


def _handle_manual_price(message, user_id: int, ud: dict, state: str) -> None:
    comp_type = state.split("_", 2)[-1]
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid number (e.g., 250).")
        return

    comp_name = ud.pop("temp_manual_name", "Unknown")
    computer  = get_current_computer(user_id)
    cfg       = COMPONENT_CONFIG.get(comp_type, {})

    if cfg:
        computer[cfg["key"]]       = comp_name
        computer[cfg["price_key"]] = price
    ud["awaiting_input"] = None
    auto_save(user_id)

    progress = get_build_progress(computer)
    markup = _after_component_markup(is_change=False, computer=computer)
    bot.send_message(
        message.chat.id,
        f"✅ Manual entry: '{comp_name}' — ${price} saved!\n{progress}",
        reply_markup=markup,
    )


def _handle_component_input(message, user_id: int, ud: dict, comp_type: str, is_change: bool) -> None:
    """
    Single function handling both 'add' and 'change' flows for all 5 component types.
    Replaces 10 near-identical elif blocks from the original file.
    """
    cfg       = COMPONENT_CONFIG[comp_type]
    query     = message.text
    similar   = search_component_price(query, comp_type)

    if not similar:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🔧 Add next component", callback_data="add_next_component"),
            types.InlineKeyboardButton("💸 Enter manually",     callback_data=cfg["manual_cb"]),
        )
        markup.row(_back_btn())
        bot.send_message(
            message.chat.id,
            "❌ No price found for this component. You can enter the price manually.",
            reply_markup=markup,
        )
        return

    if len(similar) > 1:
        markup = types.InlineKeyboardMarkup()
        for comp in similar[:4]:
            markup.add(types.InlineKeyboardButton(
                f"{cfg['emoji']} {comp['name']} — ${comp['price']}",
                callback_data=f"{cfg['select_cb']}:{comp['id']}:{comp['name']}:{comp['price']}",
            ))
        markup.row(
            types.InlineKeyboardButton("🔧 Add next component", callback_data="add_next_component"),
            types.InlineKeyboardButton("💸 Enter manually",     callback_data=cfg["manual_cb"]),
        )
        markup.row(_back_btn())
        bot.send_message(message.chat.id, "🔍 Found several options. Choose one:", reply_markup=markup)
        return

    # Exactly one result
    comp_name  = similar[0]["name"]
    comp_price = similar[0]["price"]

    computer = get_current_computer(user_id)
    computer[cfg["key"]]       = comp_name
    computer[cfg["price_key"]] = comp_price  # FIX: change flow was missing price update

    ud["awaiting_input"] = None
    auto_save(user_id)

    progress = get_build_progress(computer)
    action   = "changed" if is_change else "added"
    bot.send_message(
        message.chat.id,
        f"✅ {cfg['label']} {action}: '{comp_name}' — ${comp_price}\n{progress}",
        reply_markup=_after_component_markup(is_change=is_change, computer=computer),
    )
