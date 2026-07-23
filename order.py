import math
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import smm_api
from keyboards import (
    catalog_kb,
    confirm_order_kb,
    BTN_ORDER,
    BTN_ORDERS,
)
from states import OrderStates
from utils import format_money, not_reserved_text

router = Router()


@router.message(F.text == BTN_ORDER)
async def order_start(message: Message, state: FSMContext):
    await state.clear()
    nodes = await db.get_catalog_children(None)
    if not nodes:
        await message.answer(
            "⏳ Katalog hali to'ldirilmagan. Iltimos birozdan so'ng qayta urinib ko'ring."
        )
        return
    await message.answer(
        "🛒 Quyidagi bo'limlardan birini tanlang:",
        reply_markup=catalog_kb(nodes, None, is_root=True),
    )


@router.callback_query(F.data.startswith("cnav:"))
async def catalog_navigate(callback: CallbackQuery, state: FSMContext):
    node_id = int(callback.data.split(":")[1])
    node = await db.get_catalog_node(node_id)
    if not node:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    if node["node_type"] == "service":
        await _select_service_node(callback, state, node)
        return

    children = await db.get_catalog_children(node_id)
    if not children:
        await callback.answer("Bu bo'lim hozircha bo'sh.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📁 <b>{node['title']}</b> — kerakli bo'limni tanlang:",
        reply_markup=catalog_kb(children, node["parent_id"], is_root=False),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cback:"))
async def catalog_back(callback: CallbackQuery):
    target = int(callback.data.split(":")[1])
    if target == 0:
        nodes = await db.get_catalog_children(None)
        await callback.message.edit_text(
            "🛒 Quyidagi bo'limlardan birini tanlang:",
            reply_markup=catalog_kb(nodes, None, is_root=True),
        )
        await callback.answer()
        return

    node = await db.get_catalog_node(target)
    if not node:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    children = await db.get_catalog_children(target)
    await callback.message.edit_text(
        f"📁 <b>{node['title']}</b> — kerakli bo'limni tanlang:",
        reply_markup=catalog_kb(children, node["parent_id"], is_root=False),
        parse_mode="HTML",
    )
    await callback.answer()


async def _select_service_node(callback: CallbackQuery, state: FSMContext, node):
    service = await db.get_service(node["service_id"])
    if not service:
        await callback.answer("Bu xizmat hozircha mavjud emas.", show_alert=True)
        return
    await state.update_data(service_id=service["service_id"])
    await state.set_state(OrderStates.entering_link)
    await callback.message.edit_text(
        f"✅ Tanlandi: <b>{node['title']}</b>\n"
        f"💵 Narx: {format_money(service['price_per_1000'])} / 1000 ta\n"
        f"📏 Min: {service['min_qty']} — Max: {service['max_qty']}\n\n"
        f"🔗 Endi havolani (link) yuboring:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OrderStates.entering_link, not_reserved_text)
async def enter_link(message: Message, state: FSMContext):
    link = message.text.strip() if message.text else ""
    if not link.startswith("http"):
        await message.answer("❗️ Iltimos, to'g'ri havola (https://... bilan boshlanuvchi) yuboring.")
        return
    await state.update_data(link=link)
    data = await state.get_data()
    service = await db.get_service(data["service_id"])
    await state.set_state(OrderStates.entering_quantity)
    await message.answer(
        f"🔢 Miqdorni kiriting (Min: {service['min_qty']}, Max: {service['max_qty']}):"
    )


@router.message(OrderStates.entering_quantity, not_reserved_text)
async def enter_quantity(message: Message, state: FSMContext):
    text = (message.text or "").strip().replace(" ", "")
    if not text.isdigit():
        await message.answer("❗️ Faqat raqam kiriting.")
        return
    quantity = int(text)
    data = await state.get_data()
    service = await db.get_service(data["service_id"])
    if quantity < service["min_qty"] or quantity > service["max_qty"]:
        await message.answer(
            f"❗️ Miqdor {service['min_qty']} dan {service['max_qty']} gacha bo'lishi kerak."
        )
        return

    charge = math.ceil(service["price_per_1000"] * quantity / 1000)
    user = await db.get_user(message.from_user.id)
    balance = user["balance"] if user else 0

    await state.update_data(quantity=quantity, charge=charge)
    await state.set_state(OrderStates.confirming)

    text_out = (
        "🧾 <b>Buyurtmani tasdiqlang</b>\n\n"
        f"📦 Xizmat: {service['name']}\n"
        f"🔗 Havola: {data['link']}\n"
        f"🔢 Miqdor: {quantity}\n"
        f"💵 Narx: <b>{format_money(charge)}</b>\n"
        f"💳 Balansingiz: {format_money(balance)}\n"
    )
    if balance < charge:
        text_out += "\n❗️ Balansingiz yetarli emas. Avval hisobingizni to'ldiring."
    await message.answer(text_out, reply_markup=confirm_order_kb(), parse_mode="HTML")


@router.callback_query(OrderStates.confirming, F.data == "order_cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
    await callback.answer()


@router.callback_query(OrderStates.confirming, F.data == "order_confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    service = await db.get_service(data["service_id"])
    user = await db.get_user(callback.from_user.id)
    charge = data["charge"]

    if not user or user["balance"] < charge:
        await callback.answer("❗️ Balansingiz yetarli emas.", show_alert=True)
        return

    await callback.answer("⏳ Yuborilmoqda...")

    try:
        result = await smm_api.add_order(service["service_id"], data["link"], data["quantity"])
        api_order_id = result.get("order") if isinstance(result, dict) else None
    except smm_api.SMMApiError as e:
        await callback.message.edit_text(f"❌ Xatolik yuz berdi: {e}\nBalansingizdan pul yechilmadi.")
        await state.clear()
        return

    await db.update_balance(callback.from_user.id, -charge)
    order_id = await db.create_order(
        callback.from_user.id,
        service["service_id"],
        service["name"],
        data["link"],
        data["quantity"],
        charge,
        api_order_id,
    )
    await state.clear()

    await callback.message.edit_text(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma raqami: #{order_id}\n"
        f"📦 Xizmat: {service['name']}\n"
        f"🔢 Miqdor: {data['quantity']}\n"
        f"💵 To'landi: {format_money(charge)}\n\n"
        f"Holatini \"📊 Buyurtmalar\" bo'limidan kuzatishingiz mumkin.",
        parse_mode="HTML",
    )


@router.message(F.text == BTN_ORDERS)
async def my_orders(message: Message):
    orders = await db.get_user_orders(message.from_user.id, limit=10)
    if not orders:
        await message.answer("📭 Sizda hali buyurtmalar mavjud emas.")
        return

    lines = ["📊 <b>So'nggi buyurtmalaringiz:</b>\n"]
    for o in orders:
        status = o["status"]
        if o["api_order_id"]:
            try:
                st = await smm_api.order_status(o["api_order_id"])
                if isinstance(st, dict) and st.get("status"):
                    status = st["status"]
                    if status != o["status"]:
                        await db.update_order_status(o["id"], status)
            except smm_api.SMMApiError:
                pass
        lines.append(
            f"#{o['id']} — {o['service_name']}\n"
            f"   🔢 {o['quantity']} dona | 💵 {format_money(o['charge_uzs'])} | 📌 {status}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")
