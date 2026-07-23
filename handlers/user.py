from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID, BOT_USERNAME
from keyboards import main_menu, BTN_BALANCE, BTN_REFERRAL, BTN_GUIDES, BTN_SUPPORT, subscription_kb
from states import SupportStates
from utils import format_money, get_unsubscribed_channels

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split(maxsplit=1)
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            referrer_id = int(args[1].replace("ref", ""))
        except ValueError:
            referrer_id = None

    is_new = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
        referrer_id,
    )

    if is_new and referrer_id:
        bonus = int(await db.get_setting("referral_bonus"))
        await db.update_balance(referrer_id, bonus)
        try:
            await message.bot.send_message(
                referrer_id,
                f"🎉 Sizning taklifingiz bilan yangi foydalanuvchi qo'shildi!\n"
                f"Hisobingizga {format_money(bonus)} qo'shildi.",
            )
        except Exception:
            pass

    await message.answer(
        "👋 Assalomu alaykum! SMM xizmatlar botiga xush kelibsiz.\n\n"
        "Bu yerda siz Instagram, TikTok, Telegram, YouTube va boshqa ijtimoiy tarmoqlar uchun "
        "nakrutka xizmatlaridan foydalanishingiz mumkin.\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang 👇",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    unsub = await get_unsubscribed_channels(bot, callback.from_user.id)
    if unsub:
        await callback.answer("❗️ Siz hali barcha kanallarga obuna bo'lmagansiz.", show_alert=True)
        return
    await callback.message.delete()
    await callback.message.answer(
        "✅ Rahmat! Endi botdan to'liq foydalanishingiz mumkin.", reply_markup=main_menu()
    )


@router.message(F.text == BTN_BALANCE)
async def show_balance(message: Message):
    user = await db.get_user(message.from_user.id)
    balance = user["balance"] if user else 0
    ref_count = await db.referral_count(message.from_user.id)
    orders = await db.get_user_orders(message.from_user.id, limit=1000)
    await message.answer(
        "💳 <b>Mening hisobim</b>\n\n"
        f"👤 ID: <code>{message.from_user.id}</code>\n"
        f"💰 Balans: <b>{format_money(balance)}</b>\n"
        f"🧾 Jami buyurtmalar: {len(orders)}\n"
        f"👥 Takliflar soni: {ref_count}",
        parse_mode="HTML",
    )


@router.message(F.text == BTN_REFERRAL)
async def show_referral(message: Message):
    bonus = await db.get_setting("referral_bonus")
    ref_count = await db.referral_count(message.from_user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref{message.from_user.id}"
    await message.answer(
        "🎙 <b>Referal tizimi</b>\n\n"
        f"Do'stlaringizni taklif qiling va har bir yangi foydalanuvchi uchun "
        f"<b>{format_money(bonus)}</b> bonus oling!\n\n"
        f"🔗 Sizning havolangiz:\n<code>{link}</code>\n\n"
        f"👥 Siz taklif qilgan foydalanuvchilar: <b>{ref_count}</b> ta",
        parse_mode="HTML",
    )


@router.message(F.text == BTN_GUIDES)
async def show_guides(message: Message):
    await message.answer(
        "📚 <b>Qo'llanmalar</b>\n\n"
        "1️⃣ <b>Buyurtma berish</b> — kerakli xizmat turini tanlang, havola va miqdorni kiriting.\n"
        "2️⃣ <b>Hisob to'ldirish</b> — karta yoki Telegram Stars orqali to'ldirishingiz mumkin.\n"
        "3️⃣ <b>Link qanday olinadi?</b> — postingiz yoki profilingiz sahifasini oching va "
        "havolani nusxalang.\n"
        "4️⃣ <b>Profil yopiq bo'lmasligi kerak</b> — Instagram/TikTok profilingiz ochiq (public) "
        "bo'lishi shart.\n"
        "5️⃣ <b>Buyurtma bekor qilinmaydi</b> — xizmat boshlanganidan so'ng buyurtmani "
        "bekor qilib bo'lmaydi.\n\n"
        "❓ Savollaringiz bo'lsa \"☎️ Murojaat qilish\" bo'limi orqali yozing.",
        parse_mode="HTML",
    )


@router.message(F.text == "⬅️ Bekor qilish")
async def cancel_flow(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu())


@router.message(F.text == BTN_SUPPORT)
async def support_start(message: Message, state: FSMContext):
    await message.answer(
        "✍️ Murojaatingizni (savol, taklif yoki shikoyat) yozib yuboring. "
        "Admin tez orada javob beradi."
    )
    await state.set_state(SupportStates.waiting_message)


@router.message(SupportStates.waiting_message)
async def support_forward(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user = message.from_user
    header = f"📩 <b>Yangi murojaat</b>\n👤 {user.full_name} (@{user.username or '—'})\nID: <code>{user.id}</code>\n\n"
    try:
        await bot.send_message(ADMIN_ID, header, parse_mode="HTML")
        await message.copy_to(ADMIN_ID)
    except Exception:
        pass
    await message.answer("✅ Murojaatingiz yuborildi. Tez orada javob beriladi.", reply_markup=main_menu())


# admin replying to a user: /reply <user_id> <text>
@router.message(Command("reply"))
async def admin_reply(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Foydalanish: /reply <user_id> <matn>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("user_id noto'g'ri.")
        return
    try:
        await bot.send_message(uid, f"💬 Admin javobi:\n\n{parts[2]}")
        await message.answer("✅ Yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
