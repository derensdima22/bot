from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

DATA_FILE = "tasks.json"
DB_FILE = "tasks.db"

ADDING_TASK = 1  # состояние диалога

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            task TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["/add"],
        ["/list"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я ToDo-бот 👋\nВыбери действие:",
        reply_markup=reply_markup,
    )


# ---------- ADD TASK (CONVERSATION) ----------
async def start_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Напиши задачу:")
    return ADDING_TASK


async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    task = update.message.text.strip()

    if not task:
        await update.message.reply_text("⚠️ Задача не может быть пустой.")
        return ConversationHandler.END

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, task) VALUES (?, ?)", (user_id, task))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Добавлена: {task}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Добавление отменено.")
    return ConversationHandler.END


# ---------- LIST TASKS ----------
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, task FROM tasks WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 Задач нет")
        return

    keyboard = [
        [InlineKeyboardButton(f"❌ {row[1]}", callback_data=f"done:{row[0]}")]
        for row in rows
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📝 Твои задачи:", reply_markup=reply_markup)


# ---------- DELETE VIA BUTTON ----------
async def handle_done_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    task_id = query.data.split(":")[1]

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT task FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    row = c.fetchone()

    if not row:
        await query.edit_message_text("⚠️ Задача не найдена.")
        return

    task_text = row[0]
    c.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    conn.close()

    await query.edit_message_text(f"✅ Удалена: {task_text}")


# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Conversation handler for /add
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", start_add_task)],
        states={
            ADDING_TASK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CallbackQueryHandler(handle_done_button))

    print("🤖 Бот запущен")
    init_db()
    app.run_polling()


if __name__ == "__main__":
    main()
