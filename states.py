from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    choosing_service = State()
    entering_link = State()
    entering_quantity = State()
    confirming = State()


class TopupStates(StatesGroup):
    choosing_method = State()
    choosing_card = State()
    entering_amount = State()
    waiting_payment_confirm = State()
    waiting_receipt = State()
    entering_stars_amount = State()


class SupportStates(StatesGroup):
    waiting_message = State()


class AdminStates(StatesGroup):
    broadcast_waiting = State()
    editing_price = State()
    adding_channel = State()
    editing_setting = State()
    adding_card = State()
    adding_catalog_folder = State()
    adding_catalog_service = State()
    renaming_catalog_node = State()
    confirming_sync = State()
