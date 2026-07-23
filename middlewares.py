from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

import database as db
from config import ADMIN_ID
from utils import get_unsubscribed_channels
from keyboards import subscription_kb


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if user.id == ADMIN_ID:
            return await handler(event, data)

        # allow the "check subscription" callback itself to pass through
        if isinstance(event, CallbackQuery) and event.data == "check_sub":
            return await handler(event, data)

        # a completed payment must always be credited, regardless of subscription status
        if isinstance(event, Message) and event.successful_payment:
            return await handler(event, data)

        channels = await db.get_channels()
        if not channels:
            return await handler(event, data)

        bot = data.get("bot")
        unsub = await get_unsubscribed_channels(bot, user.id)
        if not unsub:
            return await handler(event, data)

        text = (
            "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, "
            "so'ng \"✅ Tekshirish\" tugmasini bosing:"
        )
        kb = subscription_kb(unsub)
        if isinstance(event, Message):
            await event.answer(text, reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer(text, reply_markup=kb)
        return  # block handler
