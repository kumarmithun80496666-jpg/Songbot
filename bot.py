# bot.py
import os
import sqlite3
import logging
from typing import Optional, List
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# ==========================================================
# 🔧 CONFIG — Yahan apna details likho
BOT_TOKEN = "6746892009:AAF0V5NtsqKFI7hbnOCAOeZfWsknT_6n56I"   # 👉 Yahan BotFather se mila token daalo
CHANNEL_ID = "-1003257098289"            # 👉 Apne Telegram channel ka @username daalo (ya -100 se shuru hone wala ID)
ADMIN_IDS = {6247257907}                    # 👉 Apna Telegram numeric ID (use @userinfobot to get it)
# ==========================================================

DB_FILE = "bot_data.db"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        passed_channel_check INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def mark_user_passed(user_id: int, username: Optional[str] = None):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users(user_id, username, passed_channel_check) VALUES(?,?,1)",
                (user_id, username or ""))
    conn.commit(); conn.close()

def user_passed_channel(user_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT passed_channel_check FROM users WHERE user_id = ?", (user_id,))
    r = cur.fetchone()
    conn.close()
    return bool(r and r[0] == 1)

# ---------- CHANNEL CHECK ----------
async def check_channel_membership(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning("get_chat_member failed: %s", e)
        return False

# ---------- MENUS ----------
def main_menu_keyboard(is_admin: bool = False):
    keys = [
        [InlineKeyboardButton("🎵 Play Music", callback_data="play_music")],
        [InlineKeyboardButton("📢 Vote Section", callback_data="vote")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    if is_admin:
        keys.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keys)

def admin_panel_keyboard():
    keys = [
        [InlineKeyboardButton("➕ Add Video Source", callback_data="admin_add_source")],
        [InlineKeyboardButton("🗳️ Create Vote", callback_data="admin_create_vote")],
        [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin")]
    ]
    return InlineKeyboardMarkup(keys)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    uname = user.username or user.full_name

    if user_passed_channel(uid):
        await update.message.reply_text(
            f"👋 Welcome back, {uname}!",
            reply_markup=main_menu_keyboard(is_admin=(uid in ADMIN_IDS))
        )
        return

    is_member = await check_channel_membership(context.bot, uid)
    if is_member:
        mark_user_passed(uid, uname)
        await update.message.reply_text(
            "✅ Channel joined! Now you can use the bot.",
            reply_markup=main_menu_keyboard(is_admin=(uid in ADMIN_IDS))
        )
        return

    join_btns = []
    if isinstance(CHANNEL_ID, str) and CHANNEL_ID.startswith("@"):
        join_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        join_btns.append([InlineKeyboardButton("📢 Join Channel", url=join_url)])
    join_btns.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_join")])

    await update.message.reply_text(
        "🔒 Please join our channel first before using this bot.\n"
        "Once done, press *I've Joined* ✅",
        reply_markup=InlineKeyboardMarkup(join_btns)
    )

# ---------- CALLBACK: Check join ----------
async def callback_check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    uname = query.from_user.username or query.from_user.full_name
    is_member = await check_channel_membership(context.bot, uid)

    if is_member:
        mark_user_passed(uid, uname)
        await query.edit_message_text("✅ Thank you for joining! Menu unlocked.")
        await context.bot.send_message(
            chat_id=uid,
            text="Choose an option below 👇",
            reply_markup=main_menu_keyboard(is_admin=(uid in ADMIN_IDS))
        )
    else:
        await query.edit_message_text("⚠️ You haven’t joined yet. Please join the channel first!")

# ---------- CALLBACKS ----------
async def callback_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if not user_passed_channel(uid):
        await query.edit_message_text("❌ Join the channel first to use this bot.")
        return

    if data == "play_music":
        await query.edit_message_text("🎶 Send me a song title to play or search!")
    elif data == "vote":
        await query.edit_message_text("🗳️ Voting system coming soon!")
    elif data == "help":
        await query.edit_message_text("ℹ️ Commands:\n/start - Open menu\n/help - Help info")
    elif data == "admin_panel" and uid in ADMIN_IDS:
        await query.edit_message_text("⚙️ Admin Panel:", reply_markup=admin_panel_keyboard())
    else:
        await query.edit_message_text("⚠️ You are not authorized for this command.")

# ---------- MAIN ----------
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(callback_main))

    print("✅ Bot started and running... (press CTRL+C to stop)")
    app.run_polling()

if __name__ == "__main__":
    main()