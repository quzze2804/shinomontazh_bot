from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio

scheduler = AsyncIOScheduler()

def start_scheduler(loop, bot, get_bookings):
    """
    Запускает планировщик с периодической задачей,
    которая проверяет записи и отправляет напоминания.
    
    :param loop: asyncio event loop
    :param bot: экземпляр aiogram.Bot
    :param get_bookings: функция для получения списка записей (должна возвращать список словарей)
    """
    async def reminder_job():
        now = datetime.now()
        bookings = get_bookings()
        for booking in bookings:
            user_id = booking["user_id"]
            booking_time = booking["datetime"]
            
            # Если напоминание ещё не отправлено и время напоминания пришло
            for reminder_delta in [timedelta(hours=24), timedelta(hours=1)]:
                reminder_time = booking_time - reminder_delta
                if reminder_time <= now < reminder_time + timedelta(minutes=1):
                    try:
                        if reminder_delta == timedelta(hours=24):
                            text = f"Привіт! Нагадуємо, що твоя запис на шиномонтаж запланована на {booking_time.strftime('%Y-%m-%d %H:%M')} (завтра)."
                        else:
                            text = f"Привіт! Нагадуємо, що твоя запис на шиномонтаж через 1 годину — {booking_time.strftime('%Y-%m-%d %H:%M')}."
                        await bot.send_message(user_id, text)
                    except Exception as e:
                        print(f"Не вдалося надіслати нагадування користувачу {user_id}: {e}")

    scheduler.add_job(reminder_job, 'interval', minutes=1)
    scheduler.start()
