from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
import database as db
from keyboards import ALL_MENU_TEXTS

NOT_MEMBER_STATUSES = {"left", "kicked"}


def not_reserved_text(message: Message) -> bool:
    """True if the message is plain free-text input for an FSM state (i.e. NOT a
    main-menu button press or a slash command). Use as a filter on FSM-state
    handlers so menu buttons always work even while another flow is in progress."""
    text = message.text or ""
    if text.startswith("/"):
        return False
    if text in ALL_MENU_TEXTS:
        return False
    return True


async def get_unsubscribed_channels(bot: Bot, user_id: int):
    channels = await db.get_channels()
    unsubscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in NOT_MEMBER_STATUSES:
                unsubscribed.append(ch)
        except TelegramBadRequest:
            # bot can't check (e.g. removed from channel) - skip gracefully
            continue
    return unsubscribed


def format_money(amount) -> str:
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        amount = 0
    return f"{amount:,}".replace(",", " ") + " so'm"
