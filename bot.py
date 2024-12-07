import asyncio
import aioschedule as schedule
from datetime import datetime
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import logging
from config import TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect('schedulers.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS schedulers (
    user_id INTEGER PRIMARY KEY,
    time TEXT NOT NULL
)
""")
conn.commit()

async def send_reminder():
    now = datetime.now().strftime('%H:%M')
    cursor.execute('SELECT user_id, time FROM schedulers WHERE time = ?', (now,))
    users = cursor.fetchall()

    for user in users:
        user_id, time = user
        try:
            await bot.send_message(
                user_id, 
                f"⏰ НАШЕ ВРЕМЯ НАСТАЛО! Время: {time}. Самое время исправить ваши ошибки."
            )
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

async def scheduler():
    schedule.every(1).minute.do(send_reminder)

    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)

@dp.message(Command('start'))
async def start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute('INSERT OR IGNORE INTO schedulers (user_id, time) VALUES (?, ?)', (user_id, '15:55'))
    conn.commit()
    await message.answer(
        "👋 Привет! Я ваш личный помощник для планирования задач. Чтобы настроить уведомления, используйте команду:\n"
        "`/set_schedule HH:MM` — установите время для уведомления.\n\n"
        "📅 Просмотреть текущее расписание: `/view_schedule`\n"
        "❌ Удалить расписание: `/delete_schedule`\n"
        "🔄 Обновить расписание: `/update_schedule <старое_время> <новое_время>`"
    )

@dp.message(Command('set_schedule'))
async def set_schedule(message: types.Message):
    try:
        time_str = message.text.split()[1]
        datetime.strptime(time_str, '%H:%M')
        user_id = message.from_user.id
        cursor.execute('INSERT OR REPLACE INTO schedulers (user_id, time) VALUES (?, ?)', (user_id, time_str))
        conn.commit()
        await message.answer(f"✅ Уведомление успешно установлено на {time_str}. Я напомню вам!")
    except (IndexError, ValueError):
        await message.answer("⚠️ Неверный формат времени. Используйте `/set_schedule HH:MM`, например, `/set_schedule 14:30`.")

@dp.message(Command('view_schedule'))
async def view_schedule(message: types.Message):
    user_id = message.from_user.id
    cursor.execute('SELECT time FROM schedulers WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        await message.answer(f"🕒 Ваше текущее расписание: {result[0]}. Не забудьте подготовиться!")
    else:
        await message.answer("ℹ️ У вас пока нет установленного расписания. Используйте `/set_schedule HH:MM`, чтобы настроить уведомления.")

@dp.message(Command('delete_schedule'))
async def delete_schedule(message: types.Message):
    try:
        user_id = message.from_user.id
        cursor.execute('DELETE FROM schedulers WHERE user_id = ?', (user_id,))
        conn.commit()
        await message.answer("🗑️ Ваше расписание было успешно удалено.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command('update_schedule'))
async def update_schedule(message: types.Message):
    try:
        old_time, new_time = message.text.split()[1:3]
        datetime.strptime(new_time, '%H:%M')
        user_id = message.from_user.id
        cursor.execute(
            'UPDATE schedulers SET time = ? WHERE user_id = ? AND time = ?',
            (new_time, user_id, old_time)
        )
        conn.commit()
        await message.answer(f"🔄 Уведомление обновлено: время изменено с {old_time} на {new_time}.")
    except (IndexError, ValueError):
        await message.answer("⚠️ Неверный формат. Используйте `/update_schedule <старое_время> <новое_время>`, например, `/update_schedule 14:00 15:30`.")

async def main():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
