from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ---------------- Main menu ----------------

BTN_ORDER = "🧾 Buyurtma berish"
BTN_ORDERS = "📊 Buyurtmalar"
BTN_BALANCE = "💳 Mening hisobim"
BTN_REFERRAL = "🎙 Referal tizimi"
BTN_TOPUP = "💰 Hisob to'ldirish"
BTN_SUPPORT = "☎️ Murojaat qilish"
BTN_GUIDES = "📚 Qo'llanmalar"

ALL_MENU_TEXTS = {
    BTN_ORDER,
    BTN_ORDERS,
    BTN_BALANCE,
    BTN_REFERRAL,
    BTN_TOPUP,
    BTN_SUPPORT,
    BTN_GUIDES,
    "⬅️ Bekor qilish",
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ORDER), KeyboardButton(text=BTN_BALANCE)],
            [KeyboardButton(text=BTN_ORDERS), KeyboardButton(text=BTN_TOPUP)],
            [KeyboardButton(text=BTN_REFERRAL), KeyboardButton(text=BTN_SUPPORT)],
            [KeyboardButton(text=BTN_GUIDES)],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Bekor qilish")]],
        resize_keyboard=True,
    )


# ---------------- Category emojis (matches reference bot's two-tone style) ----------------

_CATEGORY_STYLES = [
    ("telegram", "🤍 TELEGRAM 💙"),
    ("instagram", "❤️ INSTAGRAM 🤍"),
    ("tiktok", "🖤 TikTok ❤️"),
    ("youtube", "❤️ YouTube 🖤"),
    ("star", "⭐️ Stars"),
    ("premium", "⭐️ Premium"),
    ("whatsapp", "💬 WhatsApp"),
    ("facebook", "🌐 Facebook 🔵"),
    ("twitter", "🟤 Twitter"),
    ("twitch", "🔔 Twitch"),
    ("vk", "🛩 VK"),
    ("thread", "🍃 Threads"),
    ("gift", "🎁 Gift"),
]


def category_label(category: str) -> str:
    """Best-effort two-tone label matching the reference bot's visual style;
    falls back to a generic package emoji + the raw category name from the API."""
    low = (category or "").lower()
    for key, styled in _CATEGORY_STYLES:
        if key in low:
            return styled
    return f"📦 {category}"


def categories_kb(categories) -> InlineKeyboardMarkup:
    """categories: list of rows with .id and .name (from db.get_categories())."""
    buttons = []
    row = []
    for c in categories:
        label = category_label(c["name"])
        if len(label) > 40:
            label = label[:37] + "..."
        row.append(InlineKeyboardButton(text=label, callback_data=f"cat:{c['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def services_kb(services, page: int, category_id: int) -> InlineKeyboardMarkup:
    per_page = 8
    start = page * per_page
    chunk = services[start:start + per_page]
    buttons = []
    for s in chunk:
        price = f"{s['price_per_1000']:,}".replace(",", " ")
        name = s["name"] if len(s["name"]) <= 35 else s["name"][:32] + "..."
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{name} — {price} so'm/1000",
                    callback_data=f"svc:{s['service_id']}",
                )
            ]
        )
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"pg:{category_id}:{page-1}"))
    if start + per_page < len(services):
        nav.append(InlineKeyboardButton(text="Oldinga ➡️", callback_data=f"pg:{category_id}:{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="back_cats")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="order_confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order_cancel"),
            ]
        ]
    )


def subscription_kb(channels) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=f"📢 {c['title']}", url=c["url"])] for c in channels]
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------- Top-up: method + card selection ----------------

def topup_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Karta orqali", callback_data="topup_card")],
            [InlineKeyboardButton(text="⭐️ Stars orqali", callback_data="topup_stars")],
        ]
    )


def cards_choice_kb(cards) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"💳 {c['card_owner']} — {c['card_number']}", callback_data=f"card:{c['id']}")]
        for c in cards
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="topup_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def topup_receipt_confirm_kb(topup_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"topup_ok:{topup_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"topup_no:{topup_id}"),
            ]
        ]
    )


# ---------------- Admin ----------------

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats")],
            [InlineKeyboardButton(text="📣 Xabar yuborish", callback_data="adm_broadcast")],
            [InlineKeyboardButton(text="🗂 Katalog (buyurtma menyu)", callback_data="admfold:0")],
            [InlineKeyboardButton(text="💵 Narxlarni boshqarish", callback_data="adm_prices")],
            [InlineKeyboardButton(text="🔄 Xizmatlarni yangilash", callback_data="adm_sync")],
            [InlineKeyboardButton(text="📢 Majburiy obuna kanallar", callback_data="adm_channels")],
            [InlineKeyboardButton(text="💳 To'lov kartalari", callback_data="adm_cards")],
            [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="adm_settings")],
        ]
    )


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin menyu", callback_data="adm_back")]]
    )


def admin_categories_kb(categories) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for c in categories:
        label = c["name"] if len(c["name"]) <= 30 else c["name"][:27] + "..."
        row.append(InlineKeyboardButton(text=label, callback_data=f"admcat:{c['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Admin menyu", callback_data="adm_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_services_kb(services, page: int, category_id: int) -> InlineKeyboardMarkup:
    per_page = 8
    start = page * per_page
    chunk = services[start:start + per_page]
    buttons = []
    for s in chunk:
        state = "🟢" if s["is_active"] else "🔴"
        price = f"{s['price_per_1000']:,}".replace(",", " ")
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{state} {s['name'][:28]} — {price}",
                    callback_data=f"admsvc:{s['service_id']}",
                )
            ]
        )
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admpg:{category_id}:{page-1}"))
    if start + per_page < len(services):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admpg:{category_id}:{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="adm_prices")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_service_detail_kb(service_id: int, category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Narxni o'zgartirish", callback_data=f"admprice:{service_id}")],
            [InlineKeyboardButton(text="🔄 Yoqish/O'chirish", callback_data=f"admtoggle:{service_id}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admcat:{category_id}")],
        ]
    )


def admin_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💱 Kurs (USD->so'm)", callback_data="admset:exchange_rate")],
            [InlineKeyboardButton(text="📈 Ustama foiz (%)", callback_data="admset:markup_percent")],
            [InlineKeyboardButton(text="🎁 Referal bonus", callback_data="admset:referral_bonus")],
            [InlineKeyboardButton(text="⭐️ 1 Star narxi (so'm)", callback_data="admset:star_rate")],
            [InlineKeyboardButton(text="🔙 Admin menyu", callback_data="adm_back")],
        ]
    )


def admin_channels_kb(channels) -> InlineKeyboardMarkup:
    buttons = []
    for c in channels:
        buttons.append(
            [InlineKeyboardButton(text=f"❌ {c['title']}", callback_data=f"admdelch:{c['chat_id']}")]
        )
    buttons.append([InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admaddch")])
    buttons.append([InlineKeyboardButton(text="🔙 Admin menyu", callback_data="adm_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_cards_kb(cards) -> InlineKeyboardMarkup:
    buttons = []
    for c in cards:
        buttons.append(
            [InlineKeyboardButton(
                text=f"❌ {c['card_owner']} — {c['card_number']}",
                callback_data=f"admdelcard:{c['id']}",
            )]
        )
    buttons.append([InlineKeyboardButton(text="➕ Karta qo'shish", callback_data="admaddcard")])
    buttons.append([InlineKeyboardButton(text="🔙 Admin menyu", callback_data="adm_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------- Catalog: user-facing navigation ----------------

def _node_display(node) -> str:
    if node["node_type"] == "folder":
        return f"📁 {node['title']}"
    return node["title"]


def catalog_kb(nodes, parent_id, is_root: bool) -> InlineKeyboardMarkup:
    buttons = []
    if is_root:
        row = []
        for n in nodes:
            label = _node_display(n)
            if len(label) > 40:
                label = label[:37] + "..."
            row.append(InlineKeyboardButton(text=label, callback_data=f"cnav:{n['id']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
    else:
        for n in nodes:
            label = _node_display(n)
            if len(label) > 64:
                label = label[:61] + "..."
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"cnav:{n['id']}")])
        parent_target = parent_id if parent_id is not None else 0
        buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"cback:{parent_target}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------- Catalog: admin management ----------------

def admin_catalog_kb(nodes, node_id: int, parent_id) -> InlineKeyboardMarkup:
    buttons = []
    for n in nodes:
        icon = "📁" if n["node_type"] == "folder" else "🔗"
        label = f"{icon} {n['title']}"
        if len(label) > 45:
            label = label[:42] + "..."
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"admnode:{n['id']}")])
    buttons.append(
        [
            InlineKeyboardButton(text="➕ Bo'lim", callback_data=f"admaddfolder:{node_id}"),
            InlineKeyboardButton(text="➕ Xizmat", callback_data=f"admaddsvc:{node_id}"),
        ]
    )
    if node_id != 0:
        parent_target = parent_id if parent_id is not None else 0
        buttons.append([InlineKeyboardButton(text="⬅️ Yuqoriga", callback_data=f"admfold:{parent_target}")])
    buttons.append([InlineKeyboardButton(text="🔙 Admin menyu", callback_data="adm_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_node_detail_kb(node) -> InlineKeyboardMarkup:
    buttons = []
    if node["node_type"] == "folder":
        buttons.append([InlineKeyboardButton(text="📂 Ichiga kirish", callback_data=f"admfold:{node['id']}")])
    buttons.append([InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"admrename:{node['id']}")])
    buttons.append(
        [
            InlineKeyboardButton(text="⬆️ Yuqoriga", callback_data=f"admup:{node['id']}"),
            InlineKeyboardButton(text="⬇️ Pastga", callback_data=f"admdown:{node['id']}"),
        ]
    )
    buttons.append([InlineKeyboardButton(text="❌ O'chirish", callback_data=f"admdelnode:{node['id']}")])
    parent_target = node["parent_id"] if node["parent_id"] is not None else 0
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admfold:{parent_target}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_delete_confirm_kb(node_id: int, parent_id) -> InlineKeyboardMarkup:
    parent_target = parent_id if parent_id is not None else 0
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"admdelnodeok:{node_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admfold:{parent_target}"),
            ]
        ]
    )
