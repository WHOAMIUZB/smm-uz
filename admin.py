import asyncio
import random
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, MessageOriginChannel
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

import database as db
import smm_api
from config import ADMIN_ID
from keyboards import (
    admin_menu_kb,
    admin_back_kb,
    admin_categories_kb,
    admin_services_kb,
    admin_service_detail_kb,
    admin_settings_kb,
    admin_channels_kb,
    admin_cards_kb,
    admin_catalog_kb,
    admin_node_detail_kb,
    admin_delete_confirm_kb,
)
from states import AdminStates
from utils import format_money, not_reserved_text

router = Router()


def admin_only(message_or_cb) -> bool:
    return message_or_cb.from_user.id == ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not admin_only(message):
        return
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "adm_back")
async def adm_back(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.clear()
    await callback.message.edit_text("🛠 <b>Admin panel</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ---------------- Statistics ----------------

@router.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if not admin_only(callback):
        return
    s = await db.stats()
    svc_count = await db.services_count()
    try:
        panel_balance = await smm_api.get_balance()
        panel_bal_text = f"{panel_balance.get('balance')} {panel_balance.get('currency')}"
    except Exception:
        panel_bal_text = "—"

    await callback.message.edit_text(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: {s['total_users']}\n"
        f"🆕 Bugungi yangi: {s['today_users']}\n"
        f"🧾 Jami buyurtmalar: {s['total_orders']}\n"
        f"💵 Jami tushum: {format_money(s['total_revenue'])}\n"
        f"💳 Foydalanuvchilar balansi (jami): {format_money(s['total_balance'])}\n"
        f"📦 Xizmatlar soni: {svc_count}\n"
        f"🏦 SMM panel balansi: {panel_bal_text}",
        reply_markup=admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------- Broadcast ----------------

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.set_state(AdminStates.broadcast_waiting)
    await callback.message.edit_text(
        "📣 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni yuboring "
        "(matn, rasm, video — istalgan turda):",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.broadcast_waiting)
async def adm_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not admin_only(message):
        return
    await state.clear()
    user_ids = await db.all_user_ids()
    sent, failed = 0, 0
    status_msg = await message.answer(f"⏳ Yuborilmoqda... 0/{len(user_ids)}")
    for i, uid in enumerate(user_ids, 1):
        try:
            await message.copy_to(uid)
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... {i}/{len(user_ids)}")
            except Exception:
                pass
        await asyncio.sleep(0.05)
    await status_msg.edit_text(
        f"✅ Xabar yuborildi!\n\n✔️ Muvaffaqiyatli: {sent}\n❌ Xato: {failed}"
    )
    await message.answer("🛠 Admin panel", reply_markup=admin_menu_kb())


# ---------------- Services sync & price management ----------------

@router.callback_query(F.data == "adm_sync")
async def adm_sync_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    code = f"{random.randint(0, 999999):06d}"
    await state.set_state(AdminStates.confirming_sync)
    await state.update_data(sync_code=code)
    await callback.message.edit_text(
        f"🔐 Xizmatlarni yangilashni tasdiqlash uchun quyidagi bir martalik kodni yuboring:\n\n"
        f"<code>{code}</code>\n\n"
        f"❗️ Bu amal barcha xizmat narxlarini SMM API'dagi joriy kurs bo'yicha qayta hisoblaydi "
        f"va yangi xizmatlarni katalogga qo'shadi.",
        reply_markup=admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.confirming_sync, not_reserved_text)
async def adm_sync_confirm(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    data = await state.get_data()
    expected = data.get("sync_code")
    entered = (message.text or "").strip()

    if entered != expected:
        await message.answer(
            "❗️ Kod noto'g'ri. Qaytadan kiriting yoki \"⬅️ Bekor qilish\" bosing."
        )
        return

    await state.clear()
    status_msg = await message.answer("⏳ Yangilanmoqda...")
    try:
        services = await smm_api.get_services()
        if not isinstance(services, list):
            raise smm_api.SMMApiError("Kutilmagan javob formati")
        await db.upsert_services(services)
        await db.seed_catalog_from_services()
        await status_msg.edit_text(
            f"✅ {len(services)} ta xizmat yangilandi/qo'shildi.\n"
            f"🗂 Yangi xizmatlar katalogga (kategoriyasi nomi bilan) avtomatik joylashtirildi — "
            f"\"🗂 Katalog\" bo'limidan qayta nomlashingiz/guruhlashingiz mumkin.",
            reply_markup=admin_back_kb(),
        )
    except smm_api.SMMApiError as e:
        await status_msg.edit_text(f"❌ Xatolik: {e}", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_prices")
async def adm_prices(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.clear()
    categories = await db.get_categories_all()
    if not categories:
        await callback.message.edit_text(
            "❗️ Xizmatlar hali yuklanmagan. Avval \"🔄 Xizmatlarni yangilash\" tugmasini bosing.",
            reply_markup=admin_back_kb(),
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "💵 Kategoriyani tanlang:", reply_markup=admin_categories_kb(categories)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admcat:"))
async def adm_category_services(callback: CallbackQuery):
    if not admin_only(callback):
        return
    category_id = int(callback.data.split(":")[1])
    category_name = await db.get_category_name(category_id)
    if not category_name:
        await callback.answer("Kategoriya topilmadi.", show_alert=True)
        return
    services = await db.get_services_by_category_all(category_name)
    await callback.message.edit_text(
        f"📦 <b>{category_name}</b>",
        reply_markup=admin_services_kb(services, 0, category_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admpg:"))
async def adm_paginate(callback: CallbackQuery):
    if not admin_only(callback):
        return
    _, category_id, page = callback.data.split(":")
    category_id = int(category_id)
    category_name = await db.get_category_name(category_id)
    if not category_name:
        await callback.answer("Kategoriya topilmadi.", show_alert=True)
        return
    services = await db.get_services_by_category_all(category_name)
    await callback.message.edit_text(
        f"📦 <b>{category_name}</b>",
        reply_markup=admin_services_kb(services, int(page), category_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admsvc:"))
async def adm_service_detail(callback: CallbackQuery):
    if not admin_only(callback):
        return
    service_id = int(callback.data.split(":")[1])
    s = await db.get_service(service_id)
    if not s:
        await callback.answer("Topilmadi", show_alert=True)
        return
    category_id = await db.get_category_id_by_name(s["category"])
    state_text = "🟢 Faol" if s["is_active"] else "🔴 O'chirilgan"
    await callback.message.edit_text(
        f"📦 <b>{s['name']}</b>\n"
        f"ID: {s['service_id']}\n"
        f"Kategoriya: {s['category']}\n"
        f"API narxi: {s['api_rate']}$ / 1000\n"
        f"Sotuv narxi: {format_money(s['price_per_1000'])} / 1000\n"
        f"Min/Max: {s['min_qty']} / {s['max_qty']}\n"
        f"Holat: {state_text}",
        reply_markup=admin_service_detail_kb(service_id, category_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admtoggle:"))
async def adm_toggle_service(callback: CallbackQuery):
    if not admin_only(callback):
        return
    service_id = int(callback.data.split(":")[1])
    await db.toggle_service(service_id)
    await callback.answer("Holat o'zgartirildi ✅")
    await adm_service_detail(callback)


@router.callback_query(F.data.startswith("admprice:"))
async def adm_edit_price_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    service_id = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.editing_price)
    await state.update_data(service_id=service_id)
    await callback.message.edit_text(
        "✏️ Yangi narxni kiriting (so'm, 1000 ta uchun). Masalan: 15000"
    )
    await callback.answer()


@router.message(AdminStates.editing_price, not_reserved_text)
async def adm_edit_price_save(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    text = (message.text or "").strip().replace(" ", "")
    if not text.isdigit():
        await message.answer("❗️ Faqat raqam kiriting.")
        return
    data = await state.get_data()
    await db.set_service_price(data["service_id"], int(text))
    await state.clear()
    s = await db.get_service(data["service_id"])
    await message.answer(
        f"✅ \"{s['name']}\" narxi {format_money(int(text))} / 1000 ga o'zgartirildi.",
        reply_markup=admin_menu_kb(),
    )


# ---------------- Channels ----------------

@router.callback_query(F.data == "adm_channels")
async def adm_channels(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.clear()
    channels = await db.get_channels()
    await callback.message.edit_text(
        "📢 <b>Majburiy obuna kanallar</b>\n\n"
        "Faqat bot admin bo'lgan kanallarni qo'shish mumkin.",
        reply_markup=admin_channels_kb(channels),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admaddch")
async def adm_add_channel_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.set_state(AdminStates.adding_channel)
    await callback.message.edit_text(
        "➕ Kanaldan istalgan xabarni shu botga forward qiling, "
        "yoki kanal username'ini (@kanal) yoki ID raqamini yuboring.\n\n"
        "❗️ Bot o'sha kanalda <b>admin</b> bo'lishi shart.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.adding_channel, not_reserved_text)
async def adm_add_channel_finish(message: Message, state: FSMContext, bot: Bot):
    if not admin_only(message):
        return

    chat_ref = None
    if message.forward_origin and isinstance(message.forward_origin, MessageOriginChannel):
        chat_ref = message.forward_origin.chat.id
    elif message.forward_from_chat:
        chat_ref = message.forward_from_chat.id
    elif message.text:
        t = message.text.strip()
        if t.startswith("@"):
            chat_ref = t
        elif t.lstrip("-").isdigit():
            chat_ref = int(t)

    if chat_ref is None:
        await message.answer(
            "❗️ Kanaldan biror xabarni forward qiling, yoki kanal @username / ID raqamini yuboring."
        )
        return

    try:
        chat = await bot.get_chat(chat_ref)
    except Exception as e:
        await message.answer(
            f"❌ Kanal topilmadi yoki bot unga kira olmaydi: {e}\n"
            f"Botni kanalga admin qilib, qaytadan urinib ko'ring."
        )
        return

    try:
        member = await bot.get_chat_member(chat.id, bot.id)
    except Exception as e:
        await message.answer(f"❌ Bot holatini tekshirib bo'lmadi: {e}")
        return

    if member.status not in ("administrator", "creator"):
        await message.answer(
            f"❌ Bot \"{chat.title}\" kanalida admin emas.\n"
            f"Avval botni shu kanalga admin qiling (kanal sozlamalari → Administrators → bot qo'shish), "
            f"so'ng qaytadan urinib ko'ring."
        )
        return

    invite_link = chat.invite_link
    if not invite_link:
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        else:
            try:
                invite_link = await bot.export_chat_invite_link(chat.id)
            except Exception:
                invite_link = None
    if not invite_link:
        await message.answer(
            "❌ Kanal uchun havola olib bo'lmadi (botga 'Invite Users via Link' huquqini bering)."
        )
        return

    await db.add_channel(chat.id, chat.title, invite_link)
    await state.clear()
    await message.answer(f"✅ \"{chat.title}\" kanali qo'shildi.", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("admdelch:"))
async def adm_delete_channel(callback: CallbackQuery):
    if not admin_only(callback):
        return
    chat_id = int(callback.data.split(":")[1])
    await db.remove_channel(chat_id)
    channels = await db.get_channels()
    await callback.message.edit_text(
        "📢 <b>Majburiy obuna kanallar</b>", reply_markup=admin_channels_kb(channels), parse_mode="HTML"
    )
    await callback.answer("O'chirildi ✅")


# ---------------- Payment cards ----------------

@router.callback_query(F.data == "adm_cards")
async def adm_cards(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.clear()
    cards = await db.get_cards()
    await callback.message.edit_text(
        "💳 <b>To'lov kartalari</b>\n\n"
        "Foydalanuvchilar hisob to'ldirishda shu kartalardan birini tanlaydi.",
        reply_markup=admin_cards_kb(cards),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admaddcard")
async def adm_add_card_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.set_state(AdminStates.adding_card)
    await state.update_data(step="number")
    await callback.message.edit_text("💳 Karta raqamini kiriting (masalan: 8600 1234 5678 9012):")
    await callback.answer()


@router.message(AdminStates.adding_card, not_reserved_text)
async def adm_add_card_step(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    data = await state.get_data()
    if data.get("step") == "number":
        await state.update_data(card_number=message.text.strip(), step="owner")
        await message.answer("👤 Endi karta egasining to'liq ismini (F.I.Sh) kiriting:")
        return

    card_number = data["card_number"]
    card_owner = message.text.strip()
    await db.add_card(card_number, card_owner)
    await state.clear()
    await message.answer(
        f"✅ Karta qo'shildi:\n<code>{card_number}</code>\n👤 {card_owner}",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admdelcard:"))
async def adm_delete_card(callback: CallbackQuery):
    if not admin_only(callback):
        return
    card_id = int(callback.data.split(":")[1])
    await db.remove_card(card_id)
    cards = await db.get_cards()
    await callback.message.edit_text(
        "💳 <b>To'lov kartalari</b>", reply_markup=admin_cards_kb(cards), parse_mode="HTML"
    )
    await callback.answer("O'chirildi ✅")


# ---------------- Settings ----------------

_SETTING_LABELS = {
    "exchange_rate": "💱 Kurs",
    "markup_percent": "📈 Ustama",
    "referral_bonus": "🎁 Referal bonus",
    "star_rate": "⭐️ 1 Star narxi",
}


@router.callback_query(F.data == "adm_settings")
async def adm_settings(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.clear()
    s = await db.get_all_settings()
    lines = ["⚙️ <b>Sozlamalar</b>\n"]
    for key, label in _SETTING_LABELS.items():
        lines.append(f"{label}: {s.get(key)}")
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=admin_settings_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admset:"))
async def adm_edit_setting_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    key = callback.data.split(":")[1]
    await state.set_state(AdminStates.editing_setting)
    await state.update_data(key=key)
    label = _SETTING_LABELS.get(key, key)
    await callback.message.edit_text(f"✏️ Yangi qiymatni kiriting ({label}):")
    await callback.answer()


@router.message(AdminStates.editing_setting, not_reserved_text)
async def adm_edit_setting_save(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    data = await state.get_data()
    key = data["key"]
    value = (message.text or "").strip()
    if not value.replace(".", "", 1).isdigit():
        await message.answer("❗️ Faqat raqam kiriting.")
        return
    await db.set_setting(key, value)
    await state.clear()
    label = _SETTING_LABELS.get(key, key)
    await message.answer(f"✅ Sozlama yangilandi: {label} = {value}", reply_markup=admin_menu_kb())


# ---------------- Catalog management (nested ordering menu) ----------------
# The sentinel folder_id == 0 always means "root" (parent_id IS NULL in the DB).

async def _render_catalog_folder(callback: CallbackQuery, folder_id: int):
    if folder_id == 0:
        children = await db.get_catalog_children(None)
        title = "🗂 <b>Katalog (bosh menyu)</b>"
        parent_of_current = None
    else:
        node = await db.get_catalog_node(folder_id)
        if not node:
            await callback.answer("Topilmadi.", show_alert=True)
            return
        children = await db.get_catalog_children(folder_id)
        title = f"📁 <b>{node['title']}</b>"
        parent_of_current = node["parent_id"]

    if not children:
        title += "\n\n(bo'sh — pastdagi tugmalar orqali bo'lim yoki xizmat qo'shing)"

    await callback.message.edit_text(
        title,
        reply_markup=admin_catalog_kb(children, folder_id, parent_of_current),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admfold:"))
async def adm_catalog_folder(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    await state.clear()
    folder_id = int(callback.data.split(":")[1])
    await _render_catalog_folder(callback, folder_id)


@router.callback_query(F.data.startswith("admnode:"))
async def adm_catalog_node_detail(callback: CallbackQuery):
    if not admin_only(callback):
        return
    node_id = int(callback.data.split(":")[1])
    node = await db.get_catalog_node(node_id)
    if not node:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    if node["node_type"] == "service":
        service = await db.get_service(node["service_id"])
        if service:
            svc_info = (
                f"\n\n🔗 Bog'langan xizmat: {service['name']}\n"
                f"💵 Narx: {format_money(service['price_per_1000'])} / 1000\n"
                f"📏 Min/Max: {service['min_qty']} / {service['max_qty']}"
            )
        else:
            svc_info = "\n\n⚠️ Bog'langan xizmat topilmadi (o'chirilgan bo'lishi mumkin)."
        text = f"🔗 <b>{node['title']}</b>{svc_info}"
    else:
        child_count = len(await db.get_catalog_children(node_id))
        text = f"📁 <b>{node['title']}</b>\n\nIchida: {child_count} ta band"

    await callback.message.edit_text(text, reply_markup=admin_node_detail_kb(node), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admaddfolder:"))
async def adm_catalog_add_folder_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    parent = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.adding_catalog_folder)
    await state.update_data(parent_id=None if parent == 0 else parent)
    await callback.message.edit_text("📁 Yangi bo'lim nomini kiriting (masalan: Reaksiyalar):")
    await callback.answer()


@router.message(AdminStates.adding_catalog_folder, not_reserved_text)
async def adm_catalog_add_folder_save(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    title = (message.text or "").strip()
    if not title:
        await message.answer("❗️ Bo'sh nom bo'lishi mumkin emas.")
        return
    data = await state.get_data()
    await db.add_catalog_folder(data.get("parent_id"), title)
    await state.clear()
    await message.answer(f"✅ \"{title}\" bo'limi qo'shildi.", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("admaddsvc:"))
async def adm_catalog_add_service_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    parent = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.adding_catalog_service)
    await state.update_data(parent_id=None if parent == 0 else parent, step="service_id")
    await callback.message.edit_text(
        "🔗 Qo'shmoqchi bo'lgan xizmatning ID raqamini kiriting.\n\n"
        "ID'ni \"💵 Narxlarni boshqarish\" bo'limida har bir xizmat oldida ko'rishingiz mumkin."
    )
    await callback.answer()


@router.message(AdminStates.adding_catalog_service, not_reserved_text)
async def adm_catalog_add_service_step(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    data = await state.get_data()

    if data.get("step") == "service_id":
        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("❗️ Faqat raqam kiriting.")
            return
        service = await db.get_service(int(text))
        if not service:
            await message.answer("❗️ Bunday ID'li xizmat topilmadi. Qaytadan kiriting.")
            return
        await state.update_data(service_id=int(text), step="title", default_title=service["name"])
        await message.answer(
            f"👤 Endi bu band uchun nom kiriting (foydalanuvchiga shu ko'rinadi).\n"
            f"Standart nom: \"{service['name']}\" — shuni saqlash uchun \"/\" yuboring."
        )
        return

    title = (message.text or "").strip()
    if title == "/":
        title = data.get("default_title", "Xizmat")
    if not title:
        await message.answer("❗️ Bo'sh nom bo'lishi mumkin emas.")
        return

    await db.add_catalog_service(data.get("parent_id"), title, data["service_id"])
    await state.clear()
    await message.answer(f"✅ \"{title}\" katalogga qo'shildi.", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("admrename:"))
async def adm_catalog_rename_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback):
        return
    node_id = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.renaming_catalog_node)
    await state.update_data(node_id=node_id)
    await callback.message.edit_text("✏️ Yangi nomni kiriting:")
    await callback.answer()


@router.message(AdminStates.renaming_catalog_node, not_reserved_text)
async def adm_catalog_rename_save(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    title = (message.text or "").strip()
    if not title:
        await message.answer("❗️ Bo'sh nom bo'lishi mumkin emas.")
        return
    data = await state.get_data()
    await db.rename_catalog_node(data["node_id"], title)
    await state.clear()
    await message.answer(f"✅ Nom yangilandi: \"{title}\"", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("admup:"))
async def adm_catalog_move_up(callback: CallbackQuery):
    if not admin_only(callback):
        return
    node_id = int(callback.data.split(":")[1])
    await db.move_catalog_node(node_id, "up")
    node = await db.get_catalog_node(node_id)
    await callback.answer("⬆️")
    if node:
        folder_id = node["parent_id"] if node["parent_id"] is not None else 0
        await _render_catalog_folder(callback, folder_id)


@router.callback_query(F.data.startswith("admdown:"))
async def adm_catalog_move_down(callback: CallbackQuery):
    if not admin_only(callback):
        return
    node_id = int(callback.data.split(":")[1])
    await db.move_catalog_node(node_id, "down")
    node = await db.get_catalog_node(node_id)
    await callback.answer("⬇️")
    if node:
        folder_id = node["parent_id"] if node["parent_id"] is not None else 0
        await _render_catalog_folder(callback, folder_id)


@router.callback_query(F.data.startswith("admdelnode:"))
async def adm_catalog_delete_confirm(callback: CallbackQuery):
    if not admin_only(callback):
        return
    node_id = int(callback.data.split(":")[1])
    node = await db.get_catalog_node(node_id)
    if not node:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    warning = ""
    if node["node_type"] == "folder":
        count = len(await db.get_catalog_children(node_id))
        if count:
            warning = f"\n\n⚠️ Bu bo'lim ichida {count} ta band bor — ular ham o'chib ketadi!"
    await callback.message.edit_text(
        f"❗️ \"{node['title']}\" ni rostdan o'chirmoqchimisiz?{warning}",
        reply_markup=admin_delete_confirm_kb(node_id, node["parent_id"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admdelnodeok:"))
async def adm_catalog_delete(callback: CallbackQuery):
    if not admin_only(callback):
        return
    node_id = int(callback.data.split(":")[1])
    node = await db.get_catalog_node(node_id)
    if not node:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    parent_id = node["parent_id"]
    await db.delete_catalog_node(node_id)
    await callback.answer("O'chirildi ✅")
    folder_id = parent_id if parent_id is not None else 0
    await _render_catalog_folder(callback, folder_id)
