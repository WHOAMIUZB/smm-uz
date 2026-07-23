import aiosqlite
import time
from config import (
    DB_PATH,
    DEFAULT_EXCHANGE_RATE,
    DEFAULT_MARKUP_PERCENT,
    DEFAULT_REFERRAL_BONUS,
    DEFAULT_STAR_RATE,
)

_DEFAULT_SETTINGS = {
    "exchange_rate": DEFAULT_EXCHANGE_RATE,
    "markup_percent": DEFAULT_MARKUP_PERCENT,
    "referral_bonus": DEFAULT_REFERRAL_BONUS,
    "star_rate": DEFAULT_STAR_RATE,
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                referrer_id INTEGER,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                joined_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS services (
                service_id INTEGER PRIMARY KEY,
                category TEXT,
                name TEXT,
                type TEXT,
                api_rate REAL,
                min_qty INTEGER,
                max_qty INTEGER,
                price_per_1000 INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_id INTEGER,
                service_name TEXT,
                link TEXT,
                quantity INTEGER,
                charge_uzs INTEGER,
                api_order_id INTEGER,
                status TEXT DEFAULT 'Pending',
                created_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                method TEXT DEFAULT 'card',
                card_id INTEGER,
                receipt_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE,
                title TEXT,
                url TEXT,
                added_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS payment_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT,
                card_owner TEXT,
                added_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS catalog_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                title TEXT NOT NULL,
                node_type TEXT NOT NULL DEFAULT 'folder',
                service_id INTEGER,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        for k, v in _DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        await db.commit()


# ---------------- Settings ----------------

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else _DEFAULT_SETTINGS.get(key, "")


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def get_all_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT key, value FROM settings")
        rows = await cur.fetchall()
        return {k: v for k, v in rows}


# ---------------- Users ----------------

async def get_or_create_user(user_id: int, username: str, full_name: str, referrer_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id),
            )
            await db.commit()
            return False  # not new
        ref = referrer_id if (referrer_id and referrer_id != user_id) else None
        await db.execute(
            "INSERT INTO users (user_id, username, full_name, balance, referrer_id, joined_at) "
            "VALUES (?, ?, ?, 0, ?, ?)",
            (user_id, username, full_name, ref, int(time.time())),
        )
        await db.commit()
        return True  # new user


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def set_phone(user_id: int, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        await db.commit()


async def update_balance(user_id: int, delta: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?", (delta, user_id)
        )
        await db.commit()


async def get_balance(user_id: int) -> int:
    user = await get_user(user_id)
    return user["balance"] if user else 0


async def all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_blocked = 0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        today_start = int(time.time()) - (int(time.time()) % 86400)
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE joined_at >= ?", (today_start,)
        )
        today_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(charge_uzs),0) FROM orders")
        orders_row = await cur.fetchone()

        cur = await db.execute("SELECT COALESCE(SUM(balance),0) FROM users")
        total_balance = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "today_users": today_users,
            "total_orders": orders_row[0],
            "total_revenue": orders_row[1],
            "total_balance": total_balance,
        }


# ---------------- Categories ----------------

async def _get_or_create_category_id(db, name: str) -> int:
    cur = await db.execute("SELECT id FROM categories WHERE name = ?", (name,))
    row = await cur.fetchone()
    if row:
        return row[0]
    cur = await db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    return cur.lastrowid


async def get_category_name(category_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
        row = await cur.fetchone()
        return row[0] if row else None


async def get_category_id_by_name(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM categories WHERE name = ?", (name,))
        row = await cur.fetchone()
        return row[0] if row else None


async def get_categories():
    """Categories that currently have at least one ACTIVE service (for user-facing menu)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT DISTINCT c.id, c.name FROM categories c
            JOIN services s ON s.category = c.name
            WHERE s.is_active = 1
            ORDER BY c.name
            """
        )
        return await cur.fetchall()


async def get_categories_all():
    """All categories that have at least one service, active or not (for admin)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT DISTINCT c.id, c.name FROM categories c
            JOIN services s ON s.category = c.name
            ORDER BY c.name
            """
        )
        return await cur.fetchall()


# ---------------- Services ----------------

async def upsert_services(services: list):
    async with aiosqlite.connect(DB_PATH) as db:
        exchange_rate = float(await get_setting("exchange_rate"))
        markup = float(await get_setting("markup_percent"))
        for s in services:
            try:
                sid = int(s.get("service"))
                rate = float(s.get("rate", 0))
            except (TypeError, ValueError):
                continue
            category_name = (s.get("category") or "Boshqa").strip() or "Boshqa"
            await _get_or_create_category_id(db, category_name)
            price = round(rate * exchange_rate * (1 + markup / 100))
            cur = await db.execute(
                "SELECT price_per_1000 FROM services WHERE service_id = ?", (sid,)
            )
            existing = await cur.fetchone()
            custom_price = existing[0] if existing else price
            await db.execute(
                """
                INSERT INTO services (service_id, category, name, type, api_rate, min_qty, max_qty, price_per_1000, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(service_id) DO UPDATE SET
                    category = excluded.category,
                    name = excluded.name,
                    type = excluded.type,
                    api_rate = excluded.api_rate,
                    min_qty = excluded.min_qty,
                    max_qty = excluded.max_qty
                """,
                (
                    sid,
                    category_name,
                    s.get("name", f"Service {sid}"),
                    s.get("type", "Default"),
                    rate,
                    int(s.get("min", 0) or 0),
                    int(s.get("max", 0) or 0),
                    custom_price if existing else price,
                ),
            )
        await db.commit()


async def get_services_by_category(category: str):
    """Active services only (for user-facing service list)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM services WHERE category = ? AND is_active = 1 ORDER BY name",
            (category,),
        )
        return await cur.fetchall()


async def get_services_by_category_all(category: str):
    """Same as get_services_by_category but includes inactive services (for admin)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM services WHERE category = ? ORDER BY name", (category,)
        )
        return await cur.fetchall()


async def get_service(service_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM services WHERE service_id = ?", (service_id,))
        return await cur.fetchone()


async def set_service_price(service_id: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET price_per_1000 = ? WHERE service_id = ?", (price, service_id)
        )
        await db.commit()


async def toggle_service(service_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET is_active = 1 - is_active WHERE service_id = ?", (service_id,)
        )
        await db.commit()


async def services_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM services")
        return (await cur.fetchone())[0]


# ---------------- Orders ----------------

async def create_order(user_id, service_id, service_name, link, quantity, charge_uzs, api_order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO orders (user_id, service_id, service_name, link, quantity, charge_uzs, api_order_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
            """,
            (user_id, service_id, service_name, link, quantity, charge_uzs, api_order_id, int(time.time())),
        )
        await db.commit()
        return cur.lastrowid


async def get_user_orders(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
        )
        return await cur.fetchall()


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cur.fetchone()


async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()


# ---------------- Top-ups ----------------

async def create_topup(user_id: int, amount: int, method: str = "card", card_id: int = None, receipt_file_id: str = None, status: str = "pending"):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO topups (user_id, amount, method, card_id, receipt_file_id, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, amount, method, card_id, receipt_file_id, status, int(time.time())),
        )
        await db.commit()
        return cur.lastrowid


async def get_topup(topup_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM topups WHERE id = ?", (topup_id,))
        return await cur.fetchone()


async def set_topup_status(topup_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE topups SET status = ? WHERE id = ?", (status, topup_id))
        await db.commit()


# ---------------- Payment cards ----------------

async def add_card(card_number: str, card_owner: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payment_cards (card_number, card_owner, added_at) VALUES (?, ?, ?)",
            (card_number, card_owner, int(time.time())),
        )
        await db.commit()
        return cur.lastrowid


async def remove_card(card_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM payment_cards WHERE id = ?", (card_id,))
        await db.commit()


async def get_cards():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payment_cards ORDER BY id")
        return await cur.fetchall()


async def get_card(card_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payment_cards WHERE id = ?", (card_id,))
        return await cur.fetchone()


# ---------------- Channels (mandatory subscription) ----------------

async def add_channel(chat_id: int, title: str, url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO channels (chat_id, title, url, added_at) VALUES (?, ?, ?, ?)",
            (chat_id, title, url, int(time.time())),
        )
        await db.commit()


async def remove_channel(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def get_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM channels ORDER BY id")
        return await cur.fetchall()


# ---------------- Catalog (admin-defined nested ordering menu) ----------------
# node_type: 'folder' (a menu section, can contain children) or 'service' (a
# leaf pointing to a row in `services`, orderable by the user).

async def _next_sort_order(db, parent_id):
    if parent_id is None:
        cur = await db.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM catalog_nodes WHERE parent_id IS NULL"
        )
    else:
        cur = await db.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM catalog_nodes WHERE parent_id = ?",
            (parent_id,),
        )
    row = await cur.fetchone()
    return row[0] + 1


async def add_catalog_folder(parent_id, title: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        order = await _next_sort_order(db, parent_id)
        cur = await db.execute(
            "INSERT INTO catalog_nodes (parent_id, title, node_type, sort_order, created_at) "
            "VALUES (?, ?, 'folder', ?, ?)",
            (parent_id, title, order, int(time.time())),
        )
        await db.commit()
        return cur.lastrowid


async def add_catalog_service(parent_id, title: str, service_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        order = await _next_sort_order(db, parent_id)
        cur = await db.execute(
            "INSERT INTO catalog_nodes (parent_id, title, node_type, service_id, sort_order, created_at) "
            "VALUES (?, ?, 'service', ?, ?, ?)",
            (parent_id, title, service_id, order, int(time.time())),
        )
        await db.commit()
        return cur.lastrowid


async def get_catalog_children(parent_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if parent_id is None:
            cur = await db.execute(
                "SELECT * FROM catalog_nodes WHERE parent_id IS NULL ORDER BY sort_order, id"
            )
        else:
            cur = await db.execute(
                "SELECT * FROM catalog_nodes WHERE parent_id = ? ORDER BY sort_order, id",
                (parent_id,),
            )
        return await cur.fetchall()


async def get_catalog_node(node_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM catalog_nodes WHERE id = ?", (node_id,))
        return await cur.fetchone()


async def get_catalog_node_with_service(node_id: int):
    """Returns (catalog_node_row, service_row) for a 'service'-type node, or (node, None)."""
    node = await get_catalog_node(node_id)
    if not node:
        return None, None
    if node["node_type"] != "service" or not node["service_id"]:
        return node, None
    service = await get_service(node["service_id"])
    return node, service


async def rename_catalog_node(node_id: int, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE catalog_nodes SET title = ? WHERE id = ?", (title, node_id))
        await db.commit()


async def _delete_catalog_node_recursive(db, node_id: int):
    cur = await db.execute("SELECT id FROM catalog_nodes WHERE parent_id = ?", (node_id,))
    children = await cur.fetchall()
    for (child_id,) in children:
        await _delete_catalog_node_recursive(db, child_id)
    await db.execute("DELETE FROM catalog_nodes WHERE id = ?", (node_id,))


async def delete_catalog_node(node_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await _delete_catalog_node_recursive(db, node_id)
        await db.commit()


async def move_catalog_node(node_id: int, direction: str):
    """direction: 'up' or 'down' - swap sort_order with the adjacent sibling."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM catalog_nodes WHERE id = ?", (node_id,))
        node = await cur.fetchone()
        if not node:
            return
        if node["parent_id"] is None:
            cur = await db.execute(
                "SELECT * FROM catalog_nodes WHERE parent_id IS NULL ORDER BY sort_order, id"
            )
        else:
            cur = await db.execute(
                "SELECT * FROM catalog_nodes WHERE parent_id = ? ORDER BY sort_order, id",
                (node["parent_id"],),
            )
        siblings = await cur.fetchall()
        idx = next((i for i, s in enumerate(siblings) if s["id"] == node_id), None)
        if idx is None:
            return
        swap_idx = idx - 1 if direction == "up" else idx + 1
        if swap_idx < 0 or swap_idx >= len(siblings):
            return
        other = siblings[swap_idx]
        await db.execute(
            "UPDATE catalog_nodes SET sort_order = ? WHERE id = ?", (other["sort_order"], node_id)
        )
        await db.execute(
            "UPDATE catalog_nodes SET sort_order = ? WHERE id = ?", (node["sort_order"], other["id"])
        )
        await db.commit()


async def catalog_has_any() -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM catalog_nodes")
        return (await cur.fetchone())[0] > 0


async def catalog_service_ids() -> set:
    """Service IDs already assigned to at least one catalog leaf node."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT service_id FROM catalog_nodes WHERE node_type = 'service' AND service_id IS NOT NULL"
        )
        rows = await cur.fetchall()
        return {r[0] for r in rows}


async def seed_catalog_from_services():
    """Ensure every active service that isn't in ANY catalog folder yet gets placed
    under a root folder named after its API category, so the order menu is never
    empty after a sync. Admin is free to rename/reorganize/delete afterwards -
    already-placed services are never touched or duplicated."""
    already = await catalog_service_ids()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY category, name")
        services = await cur.fetchall()

        for s in services:
            if s["service_id"] in already:
                continue
            # find or create a root folder with this category's name
            cur2 = await db.execute(
                "SELECT id FROM catalog_nodes WHERE parent_id IS NULL AND node_type = 'folder' AND title = ?",
                (s["category"],),
            )
            row = await cur2.fetchone()
            if row:
                folder_id = row[0]
            else:
                order = await _next_sort_order(db, None)
                cur3 = await db.execute(
                    "INSERT INTO catalog_nodes (parent_id, title, node_type, sort_order, created_at) "
                    "VALUES (NULL, ?, 'folder', ?, ?)",
                    (s["category"], order, int(time.time())),
                )
                folder_id = cur3.lastrowid

            order = await _next_sort_order(db, folder_id)
            await db.execute(
                "INSERT INTO catalog_nodes (parent_id, title, node_type, service_id, sort_order, created_at) "
                "VALUES (?, ?, 'service', ?, ?, ?)",
                (folder_id, s["name"], s["service_id"], order, int(time.time())),
            )
            already.add(s["service_id"])

        await db.commit()

