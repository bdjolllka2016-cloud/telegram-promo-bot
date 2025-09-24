import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from aiogram.filters import Command
import os

# --- конфиг ---
TOKEN = "8442006569:AAHMQb9oBpRvEpIOETQutZ0ZGKDx8VVS7nM"  # твой токен
ADMIN_ID = 5597660360  # твой ID
PROMO_CODE = "TGBOT6"
PROMO_DISCOUNT = 6
PROMO_END = "01.11.2025"
PROMO_IMAGE = os.path.join(os.path.dirname(__file__), "promo.jpg")  # путь к картинке

# --- база данных ---
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    phone TEXT,
    subscribed_at TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS answers (
    user_id INTEGER PRIMARY KEY,
    q1 TEXT,
    q2 TEXT,
    q3 TEXT,
    q4 TEXT
)
""")
conn.commit()

# --- шаги опроса ---
user_steps = {}

# --- бот и диспетчер ---
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()  # исправлено: без аргументов

# --- обработчики ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    now = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, subscribed_at) VALUES (?, ?, ?, ?)",
        (user_id, username, first_name, now)
    )
    conn.commit()

    user_steps[user_id] = {"step": 1, "answers": {}}

    await message.answer(
        "👋 Привет! Ответьте на несколько вопросов.\n\n1️⃣ Сколько рулонов Вы планируете приобрести?"
    )

@dp.message()
async def handle_answers(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_steps:
        await message.answer("Нажмите /start, чтобы начать.")
        return

    step = user_steps[user_id]["step"]

    if step == 1:
        user_steps[user_id]["answers"]["q1"] = message.text
        user_steps[user_id]["step"] = 2
        await message.answer("2️⃣ В какой город необходима доставка?")

    elif step == 2:
        user_steps[user_id]["answers"]["q2"] = message.text
        user_steps[user_id]["step"] = 3
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
            resize_keyboard=True
        )
        await message.answer("3️⃣ Нужна ли консультация?", reply_markup=kb)

    elif step == 3:
        user_steps[user_id]["answers"]["q3"] = message.text
        user_steps[user_id]["step"] = 4
        await message.answer(
            "4️⃣ Если выбрали артикул – напишите его. Отправим запрос на склад.",
            reply_markup=ReplyKeyboardRemove()
        )

    elif step == 4:
        user_steps[user_id]["answers"]["q4"] = message.text
        user_steps[user_id]["step"] = 5

        # кнопка отправки контакта или пропустить
        contact_button = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        skip_button = KeyboardButton(text="Пропустить")
        kb = ReplyKeyboardMarkup(keyboard=[[contact_button, skip_button]], resize_keyboard=True)
        await message.answer("📱 Отправьте свой номер телефона или пропустите:", reply_markup=kb)

# --- обработка контакта ---
@dp.message(lambda msg: msg.contact is not None)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
    conn.commit()
    await finalize_user(user_id, message)

# --- обработка кнопки "Пропустить" ---
@dp.message(lambda msg: msg.text == "Пропустить")
async def handle_skip(message: types.Message):
    user_id = message.from_user.id
    await finalize_user(user_id, message)

# --- финализация ---
async def finalize_user(user_id, message):
    await message.answer("✅ Спасибо за ответы!", reply_markup=ReplyKeyboardRemove())

    ans = user_steps.get(user_id, {}).get("answers", {})
    cursor.execute(
        "INSERT OR REPLACE INTO answers (user_id, q1, q2, q3, q4) VALUES (?, ?, ?, ?, ?)",
        (user_id, ans.get("q1"), ans.get("q2"), ans.get("q3"), ans.get("q4"))
    )
    conn.commit()
    if user_id in user_steps:
        del user_steps[user_id]

    try:
        photo = InputFile(PROMO_IMAGE)
        await message.answer_photo(
            photo=photo,
            caption=f"🎁 Ваш промокод: <b>{PROMO_CODE}</b>\nСкидка: <b>{PROMO_DISCOUNT}%</b>\nДействует до: {PROMO_END}"
        )
    except:
        await message.answer(f"Ваш промокод: {PROMO_CODE} ({PROMO_DISCOUNT}% до {PROMO_END})")

    cursor.execute("SELECT first_name, username, phone FROM users WHERE user_id = ?", (user_id,))
    user_info = cursor.fetchone()
    first_name = user_info[0] if user_info else ""
    username = f"@{user_info[1]}" if user_info and user_info[1] else ""
    phone = user_info[2] if user_info and user_info[2] else "не указан"

    await bot.send_message(
        ADMIN_ID,
        f"✅ Пользователь прошёл опрос!\nИмя: {first_name}\nUsername: {username}\nТелефон: {phone}"
    )

# --- запуск ---
async def main():
    print("🚀 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
