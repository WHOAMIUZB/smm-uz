from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_ID
from keyboards import (
    main_menu,
    cancel_kb,
    topup_method_kb,
    cards_choice_kb,
    topup_receipt_confirm_kb,
    BTN_TOPUP,
)
from states import TopupStates
from utils import format_money, not_reserved_text

router = Router()


@router.message(F.text == BTN_TOPUP)
async def topup_start(message: Message, state: FSMContext):
    await state.set_state(TopupStates.choosing_method)
    await message.answer(
        "💰 Hisobingizni qanday usulda to'ldirmoqchisiz?",
        reply_markup=topup_method_kb(),
    )


# ---------------- Card flow ----------------

@router.callback_query(F.data == "topup_card")
async def topup_choose_card(callback: CallbackQuery, state: FSMContext):
    cards = await db.get_cards()
    if not cards:
        await callback.answer(
            "❗️ Hozircha to'lov kartalari qo'shilmagan. Admin bilan bog'laning.", show_alert=True
        )
        return
    await state.set_state(TopupStates.choosing_card)
    await callback.message.edit_text(
        "💳 To'lov qilmoqchi bo'lgan kartani tanlang:", reply_markup=cards_choice_kb(cards)
    )
    await callback.answer()


@router.callback_query(F.data == "topup_back")
async def topup_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TopupStates.choosing_method)
    await callback.message.edit_text(
        "💰 Hisobingizni qanday usulda to'ldirmoqchisiz?", reply_markup=topup_method_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("card:"))
async def topup_card_selected(callback: CallbackQuery, state: FSMContext):
    card_id = int(callback.data.split(":")[1])
    card = await db.get_card(card_id)
    if not card:
        await callback.answer("Karta topilmadi.", show_alert=True)
        return
    await state.update_data(card_id=card_id)
    await state.set_state(TopupStates.entering_amount)
    await callback.message.edit_text(
        f"💳 Tanlangan karta:\n<code>{card['card_number']}</code>\n👤 {card['card_owner']}\n\n"
        f"Hisobingizni to'ldirmoqchi bo'lgan summani so'mda kiriting (masalan: 50000):",
        parse_mode="HTML",
    )
    await callback.message.answer("👇", reply_markup=cancel_kb())
    await callback.answer()


@router.message(TopupStates.entering_amount, not_reserved_text)
async def topup_amount(message: Message, state: FSMContext):
    text = (message.text or "").strip().replace(" ", "")
    if not text.isdigit() or int(text) < 1000:
        await message.answer("❗️ Iltimos, kamida 1000 so'm miqdorida to'g'ri raqam kiriting.")
        return
    amount = int(text)
    data = await state.get_data()
    card = await db.get_card(data["card_id"])
    if not card:
        await state.clear()
        await message.answer("❗️ Tanlangan karta o'chirilgan. Qaytadan urinib ko'ring.", reply_markup=main_menu())
        return

    await state.update_data(amount=amount)
    await state.set_state(TopupStates.waiting_receipt)

    await message.answer(
        f"💳 Quyidagi kartaga <b>{format_money(amount)}</b> o'tkazing:\n\n"
        f"<code>{card['card_number']}</code>\n👤 {card['card_owner']}\n\n"
        f"To'lovni amalga oshirgach, chek skrinshotini (rasm yoki fayl) shu yerga yuboring.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(TopupStates.waiting_receipt, F.photo | F.document)
async def topup_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount = data["amount"]
    card = await db.get_card(data["card_id"])
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    topup_id = await db.create_topup(
        message.from_user.id, amount, method="card", card_id=data["card_id"], receipt_file_id=file_id
    )
    await state.clear()

    await message.answer(
        "✅ Chek qabul qilindi. Admin tekshiruvidan so'ng hisobingiz to'ldiriladi.",
        reply_markup=main_menu(),
    )

    caption = (
        f"💰 <b>Yangi to'ldirish so'rovi #{topup_id}</b>\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"🔗 Username: @{message.from_user.username or '—'}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"💵 Summa: <b>{format_money(amount)}</b>\n"
        f"💳 Karta: {card['card_number']} ({card['card_owner']})" if card else "💳 Karta: —"
    )
    try:
        if message.photo:
            await bot.send_photo(
                ADMIN_ID, file_id, caption=caption, parse_mode="HTML",
                reply_markup=topup_receipt_confirm_kb(topup_id),
            )
        else:
            await bot.send_document(
                ADMIN_ID, file_id, caption=caption, parse_mode="HTML",
                reply_markup=topup_receipt_confirm_kb(topup_id),
            )
    except Exception:
        pass


@router.message(TopupStates.waiting_receipt, not_reserved_text)
async def topup_need_receipt(message: Message):
    await message.answer("❗️ Iltimos, chek skrinshotini rasm yoki fayl shaklida yuboring.")


@router.callback_query(F.data.startswith("topup_ok:"))
async def approve_topup(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        return
    topup_id = int(callback.data.split(":")[1])
    topup = await db.get_topup(topup_id)
    if not topup or topup["status"] != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.update_balance(topup["user_id"], topup["amount"])
    await db.set_topup_status(topup_id, "approved")

    new_caption = (callback.message.caption or callback.message.text or "") + "\n\n✅ Tasdiqlandi"
    try:
        if callback.message.caption is not None:
            await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
        else:
            await callback.message.edit_text(new_caption, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Tasdiqlandi ✅")

    try:
        await bot.send_message(
            topup["user_id"],
            f"✅ Hisobingiz {format_money(topup['amount'])} ga to'ldirildi!",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("topup_no:"))
async def reject_topup(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        return
    topup_id = int(callback.data.split(":")[1])
    topup = await db.get_topup(topup_id)
    if not topup or topup["status"] != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.set_topup_status(topup_id, "rejected")
    new_caption = (callback.message.caption or callback.message.text or "") + "\n\n❌ Rad etildi"
    try:
        if callback.message.caption is not None:
            await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
        else:
            await callback.message.edit_text(new_caption, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Rad etildi ❌")

    try:
        await bot.send_message(
            topup["user_id"],
            f"❌ To'ldirish so'rovingiz (#{topup_id}) rad etildi. "
            f"Savol bo'lsa, \"☎️ Murojaat qilish\" bo'limiga yozing.",
        )
    except Exception:
        pass


# ---------------- Telegram Stars flow (native, auto-credited) ----------------

@router.callback_query(F.data == "topup_stars")
async def topup_stars_start(callback: CallbackQuery, state: FSMContext):
    star_rate = int(await db.get_setting("star_rate"))
    await state.set_state(TopupStates.entering_stars_amount)
    await callback.message.edit_text(
        f"⭐️ 1 Star = {format_money(star_rate)}\n\n"
        f"Necha dona Stars sotib olmoqchisiz? Sonini kiriting (masalan: 50):"
    )
    await callback.message.answer("👇", reply_markup=cancel_kb())
    await callback.answer()


@router.message(TopupStates.entering_stars_amount, not_reserved_text)
async def topup_stars_amount(message: Message, state: FSMContext, bot: Bot):
    text = (message.text or "").strip().replace(" ", "")
    if not text.isdigit() or int(text) < 1:
        await message.answer("❗️ Iltimos, to'g'ri raqam kiriting (kamida 1).")
        return
    stars = int(text)
    star_rate = int(await db.get_setting("star_rate"))
    credited = stars * star_rate
    await state.clear()

    await message.answer(
        f"⭐️ {stars} Stars — hisobingizga {format_money(credited)} tushadi.\n"
        f"To'lovni yakunlash uchun quyidagi hisob-faktura orqali to'lang:",
        reply_markup=main_menu(),
    )

    await bot.send_invoice(
        chat_id=message.from_user.id,
        title="Hisobni Stars orqali to'ldirish",
        description=f"{stars} ta Telegram Stars — {format_money(credited)} hisobingizga tushadi.",
        payload=f"stars_topup:{message.from_user.id}:{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{stars} Stars", amount=stars)],
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    payment = message.successful_payment
    stars = payment.total_amount  # for XTR currency, total_amount is the star count directly
    star_rate = int(await db.get_setting("star_rate"))
    credited = stars * star_rate

    await db.update_balance(message.from_user.id, credited)
    await db.create_topup(
        message.from_user.id, credited, method="stars", card_id=None,
        receipt_file_id=None, status="approved",
    )

    await message.answer(
        f"✅ To'lov muvaffaqiyatli! Hisobingiz {format_money(credited)} ga to'ldirildi.",
        reply_markup=main_menu(),
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"⭐️ <b>Stars orqali to'ldirish</b>\n\n"
            f"👤 {message.from_user.full_name} (@{message.from_user.username or '—'})\n"
            f"🆔 ID: <code>{message.from_user.id}</code>\n"
            f"⭐️ {stars} Stars — {format_money(credited)}",
            parse_mode="HTML",
        )
    except Exception:
        pass
