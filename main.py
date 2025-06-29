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

    bookings[time] = {"name": name, "phone": phone}

    await message.answer(
        f"✅ Ви успішно записані на {time}!\n"
        f"👤 Ім’я: {name}\n📞 Телефон: {phone}"
    )

    await bot.send_message(
        ADMIN_ID,
        f"🔔 Нова бронь:\n🕒 {time}\n👤 {name}\n📞 {phone}"
    )
    await state.finish()

if name == '__main__':
    executor.start_polling(dp, skip_updates=True)
