import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 7285220061))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Вільні слоти
time_slots = [
    "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
    "16:00", "16:30", "17:00"
]
bookings = {}

class BookingStates(StatesGroup):
    waiting_for_time = State()
    waiting_for_name = State()
    waiting_for_phone = State()

def create_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    buttons = []
    for time in time_slots:
        if time in bookings:
            buttons.append(KeyboardButton(f"❌ {time}"))
        else:
            buttons.append(KeyboardButton(time))
    keyboard.add(*buttons)
    return keyboard

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Старт"))
    await message.answer(
        "👋 Вітаємо у сервісі онлайн-запису на шиномонтаж!\n"
        "Натисніть «Старт», щоб обрати зручний час 🛞\n"
        "🕗 Графік роботи: 08:00 – 17:00", reply_markup=keyboard)

@dp.message_handler(lambda m: m.text == "Старт")
async def start_booking(message: types.Message):
    await BookingStates.waiting_for_time.set()
    await message.answer("🕒 Оберіть вільний час:", reply_markup=create_keyboard())

@dp.message_handler(state=BookingStates.waiting_for_time)
async def time_chosen(message: types.Message, state: FSMContext):
    selected_time = message.text.replace("❌", "").strip()
    if selected_time not in time_slots or selected_time in bookings:
        await message.answer("⛔️ Цей час зайнятий або недоступний. Спробуйте інший.")
        return
    await state.update_data(time=selected_time)
    await BookingStates.next()
    await message.answer("✏️ Введіть ваше ім’я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=BookingStates.waiting_for_name)
async def name_chosen(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await BookingStates.next()
    await message.answer("📞 Введіть ваш номер телефону:")

@dp.message_handler(state=BookingStates.waiting_for_phone)
async def phone_chosen(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    time = user_data['time']
    name = user_data['name']
    phone = message.text

    bookings[time] = {"name": name, "phone": phone, "user_id": message.from_user.id}

    await message.answer(
        f"✅ Ви успішно записані на {time}!\n"
        f"👤 Ім’я: {name}\n📞 Телефон: {phone}"
    )

    await bot.send_message(
        ADMIN_ID,
        f"🔔 Нова бронь:\n🕒 {time}\n👤 {name}\n📞 {phone}"
    )
    await state.finish()

@dp.message_handler(commands=['mybooking'])
async def my_booking(message: types.Message):
    user_id = message.from_user.id

    found_time = None
    found_data = None
    for time, data in bookings.items():
        if data.get("user_id") == user_id:
            found_time = time
            found_data = data
            break

    if found_time:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Скасувати запис", callback_data="cancel_booking"),
            InlineKeyboardButton("🔄 Перенести запис", callback_data="reschedule_booking")
        )
        await message.answer(
            f"🔔 У тебе є активний запис:\n"
            f"🕒 {found_time}\n👤 {found_data['name']}\n📞 {found_data['phone']}",
            reply_markup=kb
        )
    else:
        await message.answer("ℹ️ У тебе немає активного запису.")



@dp.callback_query_handler(lambda c: c.data == "cancel_booking")
async def cancel_booking(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    for time in list(bookings):
        if bookings[time].get("user_id") == user_id:
            del bookings[time]
            await callback.message.edit_text("✅ Запис скасовано. Якщо захочеш — можеш записатися знову через /start 😉")
            return
    await callback.message.edit_text("ℹ️ Запис не знайдено.")

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Скасування запису
@dp.callback_query_handler(lambda c: c.data == "cancel_booking")
async def cancel_booking(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    global bookings
    for time in list(bookings):
        if bookings[time].get("user_id") == user_id:
            del bookings[time]
            await callback.message.edit_text("✅ Ваш запис скасовано. Якщо захочеш — можеш записатися знову через /start 😉")
            return
    await callback.message.edit_text("ℹ️ У тебе немає активного запису.")

# Клас для станів переносу
class RescheduleStates(StatesGroup):
    waiting_for_new_time = State()

# Початок переносу
@dp.callback_query_handler(lambda c: c.data == "reschedule_booking")
async def reschedule_booking_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_booking = None
    for time, data in bookings.items():
        if data.get("user_id") == user_id:
            user_booking = time
            break
    if not user_booking:
        await callback.message.edit_text("ℹ️ У тебе немає активного запису для переносу.")
        return

    await RescheduleStates.waiting_for_new_time.set()
    await state.update_data(old_time=user_booking)
    
    # Відображаємо клавіатуру з вільними слотами
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    buttons = []
    for time in time_slots:
        if time in bookings and time != user_booking:
            buttons.append(KeyboardButton(f"❌ {time}"))
        else:
            buttons.append(KeyboardButton(time))
    keyboard.add(*buttons)
    await callback.message.answer("🕓 Оберіть новий час для переносу:", reply_markup=keyboard)

# Вибір нового часу
@dp.message_handler(state=RescheduleStates.waiting_for_new_time)
async def process_new_time(message: types.Message, state: FSMContext):
    new_time = message.text.replace("❌", "").strip()
    data = await state.get_data()
    old_time = data.get("old_time")

    if new_time not in time_slots:
        await message.answer("⛔️ Недійсний час, оберіть час зі списку.")
        return

    if new_time in bookings and new_time != old_time:
        await message.answer("⛔️ Цей час вже зайнятий. Оберіть інший.")
        return

    bookings[new_time] = bookings.pop(old_time)

    await message.answer(f"✅ Твій запис перенесено з {old_time} на {new_time}.")
    await bot.send_message(ADMIN_ID, f"♻️ Користувач {bookings[new_time]['name']} переніс запис з {old_time} на {new_time}.")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
