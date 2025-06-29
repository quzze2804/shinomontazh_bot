import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 7285220061))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Часи
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
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Старт"))
    await message.answer(
        "👋 Вітаємо у сервісі онлайн-запису на шиномонтаж!\n"
        "Натисніть «Старт», щоб обрати зручний час 🛞\n"
        "🕗 Графік роботи: 08:00 – 17:00", reply_markup=keyboard)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привіт! Я бот шиномонтажу. Тут ти можеш легко записатись на зручний час.\n\n"
        "📌 Для керування своїм записом натисни /mybooking"
    )

@dp.message_handler(lambda m: m.text == "Старт")
async def start_booking(message: types.Message):
    await BookingStates.waiting_for_time.set()
    await message.answer("🕒 Оберіть вільний час:", reply_markup=create_keyboard())

@dp.message_handler(state=BookingStates.waiting_for_time)
async def time_chosen(message: types.Message, state: FSMContext):
    selected_time = message.text.replace("❌", "").strip()
    if selected_time not in time_slots or selected_time in bookings:
        await message.answer("⛔ Цей час зайнятий або недоступний. Спробуйте інший.")
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

    await bot.send_message(
        ADMIN_ID,
        f"🔔 Нова бронь:\n🕒 {time}\n👤 {name}\n📞 {phone}"
    )
    await state.finish()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@dp.message_handler(commands=['mybooking'])
async def my_booking(message: types.Message):
    user_id = message.from_user.id

    # Шукаємо бронь для користувача
    found_time = None
    for time, data in bookings.items():
        if data.get("user_id") == user_id:
            found_time = time
            break

    if found_time:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Скасувати запис", callback_data="cancel_booking"),
            InlineKeyboardButton("🔄 Перенести запис", callback_data="reschedule_booking")
        )
        await message.answer(
            f"🔔 У тебе є активний запис на:\n🕒 {found_time}\n👤 {data['name']}\n📞 {data['phone']}",
            reply_markup=kb
        )
    else:
        await message.answer("ℹ️ У тебе немає активного запису.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)


import asyncio
from aiogram import Bot, Dispatcher, executor, types
from scheduler import start_scheduler

API_TOKEN = "твой_токен_бота"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Пример хранения записей в памяти
bookings = []

def get_bookings():
    return bookings

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я бот шиномонтажу. Обирай час для запису...")

# Допустим, где-то у тебя код записи добавляет запись в bookings:
# bookings.append({"user_id": message.from_user.id, "datetime": datetime_obj})

async def on_startup(dp):
    loop = asyncio.get_event_loop()
    start_scheduler(loop, bot, get_bookings)
    print("Scheduler started")

if name == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
