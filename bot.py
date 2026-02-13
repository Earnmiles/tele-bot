import os
import logging
import psycopg2
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==============================
# ENV VARIABLES
# ==============================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "database": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASS"),
    "port": os.environ.get("DB_PORT", 5432)
}

# ==============================
# DATABASE CONNECTION
# ==============================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ==============================
# BOT COMMANDS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO NOTHING;
        """, (user.id, user.username, user.first_name))

        conn.commit()
        cur.close()
        conn.close()

        await update.message.reply_text("✅ You are registered successfully!")

    except Exception as e:
        print("DB ERROR:", e)
        await update.message.reply_text("❌ Database error.")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT telegram_id, username, first_name, joined_at FROM users;")
        rows = cur.fetchall()

        if not rows:
            await update.message.reply_text("No users found.")
            return

        text = "📋 Registered Users:\n\n"
        for row in rows:
            text += f"""
ID: {row[0]}
Username: {row[1]}
Name: {row[2]}
Joined: {row[3]}

"""

        await update.message.reply_text(text)

        cur.close()
        conn.close()

    except Exception as e:
        print("DB ERROR:", e)
        await update.message.reply_text("❌ Database error.")

# ==============================
# FLASK SERVER
# ==============================

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("users", users))

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

# ==============================
# STARTUP
# ==============================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import asyncio
    asyncio.run(application.initialize())
    asyncio.run(application.bot.set_webhook(WEBHOOK_URL))

    print("🚀 Bot started with webhook!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
