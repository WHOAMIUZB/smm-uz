import os

# --- Telegram bot ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8678413684:AAHnoyOgk5AhKwF4kYbcu_11d5M5rpLgpw0")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7861165622"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "smm_uzb_robot")

# --- SMM panel API ---
SMM_API_URL = os.getenv("SMM_API_URL", "https://smmapi.safobuilder.uz/shox_smmbot/api/v2")
SMM_API_KEY = os.getenv("SMM_API_KEY", "236f1919d45a861fcf690b450d1b378b")

# --- Database ---
DB_PATH = os.getenv("DB_PATH", "smm_bot.db")

# --- Default settings (overridable from Admin panel -> stored in `settings` table) ---
DEFAULT_EXCHANGE_RATE = "13000"       # 1 USD -> so'm, used when syncing services from API (rates are in USD)
DEFAULT_MARKUP_PERCENT = "40"         # % markup added on top of api rate when computing sell price
DEFAULT_REFERRAL_BONUS = "1000"       # so'm credited to referrer once invited user joins
DEFAULT_STAR_RATE = "300"             # so'm per 1 Telegram Star, used to convert top-up amount -> stars

# --- Web server (Render.com health check) ---
PORT = int(os.getenv("PORT", "10000"))
