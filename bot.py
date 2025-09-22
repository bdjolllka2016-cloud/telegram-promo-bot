import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InputFile
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- конфиг ---
TOKEN = "8442006569:AAEH03mtwRrRj0-fkFXXm7j73AXmoGK1VD4"
ADMIN_ID = 5597660360  # ваш Telegram user_id
PROMO_CODE = "TGBOT6"
PROMO_DISCOUNT = 6
PROMO_END = "2025-10-01"
PROMO_IMAGE = "promo.jpg"  # картинка промокода в папке с ботом

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

# --- диспетчер ---
dp = Dispatcher()

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

        # Сохраняем ответы в SQLite
        ans = user_steps[user_id]["answers"]
        cursor.execute(
            "INSERT OR REPLACE INTO answers (user_id, q1, q2, q3, q4) VALUES (?, ?, ?, ?, ?)",
            (user_id, ans["q1"], ans["q2"], ans["q3"], ans["q4"])
        )
        conn.commit()
        del user_steps[user_id]

        # --- отправляем пользователю промокод с картинкой ---
        try:
            photo = InputFile(PROMO_IMAGE)
            await message.answer_photo(
                photo=photo,
                caption=f"🎁 Ваш промокод: <b>{PROMO_CODE}</b>\nСкидка: <b>{PROMO_DISCOUNT}%</b>\nДействует до: {PROMO_END}"
            )
        except Exception as e:
            await message.answer(f"Ваш промокод: {PROMO_CODE} ({PROMO_DISCOUNT}% до {PROMO_END})")

        # --- уведомление админу ---
        cursor.execute("SELECT first_name, username FROM users WHERE user_id = ?", (user_id,))
        user_info = cursor.fetchone()
        first_name = user_info[0] if user_info else ""
        username = f"@{user_info[1]}" if user_info and user_info[1] else ""

        await bot.send_message(
            ADMIN_ID,
            f"✅ Пользователь прошёл опрос!\nИмя: {first_name}\nUsername: {username}\nТелефон: {ans.get('phone', 'не указан')}"
        )

# --- кнопка отправки контакта ---
@dp.message()
async def handle_contact(message: types.Message):
    if message.contact:
        phone = message.contact.phone_number
        user_id = message.from_user.id
        cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        conn.commit()

# --- запуск ---
async def main():
    global bot
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    print("🚀 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())