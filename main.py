"""
DRAGOVS TELEGRAM BOT (bitta fayl)

ISHGA TUSHIRISH:
1) Telegramda @BotFather -> /newbot -> nomi: Dragovs -> token oling
2) Pastdagi BOT_TOKEN ga tokenni yozing
3) Terminalda:
       pip install python-telegram-bot==21.6
       python dragovs_bot.py

BUYRUQLAR:
  /start   - ro'yxatdan o'tish (profil bor bo'lsa, to'g'ridan-to'g'ri Play tugmasi)
  /profile - profilni ko'rish
  /reset   - ism va familiyani qayta kiritish
  /cancel  - bekor qilish

Profillar dragovs.db (SQLite) faylida saqlanadi.
Play tugmasi Telegram Web App sifatida ishlaydi (havola https:// bo'lishi shart).
"""

import logging
import os
import sqlite3

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ====== SOZLAMALAR ======
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GAME_URL = "https://profound-snickerdoodle-468309.netlify.app"
DB_PATH = os.getenv("DB_PATH", "dragovs.db")
# ========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

FIRST_NAME, LAST_NAME = range(2)


# ---------- Ma'lumotlar bazasi ----------
def db_init() -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT NOT NULL,
                last_name   TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def db_get_user(telegram_id: int):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT first_name, last_name FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()


def db_save_user(telegram_id: int, username, first_name: str, last_name: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
            """,
            (telegram_id, username, first_name, last_name),
        )


# ---------- Yordamchi ----------
def play_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("▶️ Play", web_app=WebAppInfo(url=GAME_URL))]]
    )


async def send_welcome(update: Update, first_name: str, last_name: str) -> None:
    await update.effective_message.reply_text(
        f"🎮 Dasturga xush kelibsiz, {first_name} {last_name}!\n\n"
        "O'yinni boshlash uchun Play tugmasini bosing 👇",
        reply_markup=play_keyboard(),
    )


# ---------- Handlerlar ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    existing = db_get_user(update.effective_user.id)
    if existing:
        await send_welcome(update, existing[0], existing[1])
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 Dragovs botiga xush kelibsiz!\n\n"
        "Profil yaratish uchun avval ismingizni kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return FIRST_NAME


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Yangi ismingizni kiriting:")
    return FIRST_NAME


async def get_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    first_name = update.message.text.strip()
    if not (2 <= len(first_name) <= 40):
        await update.message.reply_text(
            "Ism 2 dan 40 gacha belgidan iborat bo'lsin. Qayta kiriting:"
        )
        return FIRST_NAME
    context.user_data["first_name"] = first_name
    await update.message.reply_text("Endi familiyangizni kiriting:")
    return LAST_NAME


async def get_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    last_name = update.message.text.strip()
    if not (2 <= len(last_name) <= 40):
        await update.message.reply_text(
            "Familiya 2 dan 40 gacha belgidan iborat bo'lsin. Qayta kiriting:"
        )
        return LAST_NAME

    user = update.effective_user
    first_name = context.user_data.pop("first_name")
    db_save_user(user.id, user.username, first_name, last_name)

    await update.message.reply_text("✅ Profilingiz yaratildi!")
    await send_welcome(update, first_name, last_name)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Bekor qilindi. Qayta boshlash uchun /start ni bosing."
    )
    return ConversationHandler.END


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = db_get_user(update.effective_user.id)
    if not data:
        await update.message.reply_text("Profil topilmadi. /start ni bosing.")
        return
    await update.message.reply_text(
        f"👤 Profilingiz:\nIsm: {data[0]}\nFamiliya: {data[1]}",
        reply_markup=play_keyboard(),
    )


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. Railway Variables bo'limiga BOT_TOKEN qo'shing.")

    db_init()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("reset", reset)],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_last_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("profile", profile))

    logging.info("Dragovs bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
