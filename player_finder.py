# CS2 Teammate Finder Bot – Cleaned for PTB v21+

import json
import random
import logging
from datetime import datetime, timedelta
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)

logging.basicConfig(level=logging.INFO)

USER_FILE = "cs2_teammates.json"
MATCH_LOG = {}

(PREMIER, WINGMAN, MAPS, TALKATIVE, ROLE, MIC, HOURS, TEAM_TYPE, LANGUAGE, AGGRO) = range(10)

CS2_MAPS = [
    "Mirage", "Inferno", "Nuke", "Overpass", "Vertigo", "Ancient", "Anubis", "Dust II", "Cache", "Train"
]
ROLES = ["Entry", "Support", "AWPer", "Lurker", "IGL"]
LANGUAGES = ["English", "Russian"]

# ----- Start Conversation -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Welcome! Let's build your CS2 profile.\nWhat is your Premier rating?")
    return PREMIER

async def ask_wingman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['premier_rating'] = int(update.message.text)
    await update.message.reply_text("What is your Wingman rating?")
    return WINGMAN

async def ask_maps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wingman_rating'] = int(update.message.text)
    keyboard = [[KeyboardButton(m)] for m in CS2_MAPS]
    await update.message.reply_text("Choose your favorite map (send one per message, type /done when finished):",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    context.user_data['favorite_maps'] = []
    return MAPS

async def collect_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text in CS2_MAPS:
        context.user_data['favorite_maps'].append(update.message.text)
    return MAPS

async def done_maps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Are you talkative in voice chat? (yes/no)")
    return TALKATIVE

async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['talkative'] = update.message.text.lower() == 'yes'
    keyboard = [[KeyboardButton(r)] for r in ROLES]
    await update.message.reply_text("What is your preferred role?",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return ROLE

async def ask_mic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['preferred_role'] = update.message.text
    await update.message.reply_text("Do you have a microphone? (yes/no)")
    return MIC

async def ask_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['microphone'] = update.message.text.lower() == 'yes'
    await update.message.reply_text("What hours are you available to play? (e.g., 18:00-22:00)")
    return HOURS

async def ask_team_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['available_hours'] = update.message.text
    await update.message.reply_text("Do you want to play Premier or Wingman?")
    return TEAM_TYPE

async def ask_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['team_type'] = update.message.text
    keyboard = [[KeyboardButton(lang)] for lang in LANGUAGES]
    await update.message.reply_text("Preferred communication language:",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return LANGUAGE

async def ask_aggro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['language'] = update.message.text
    await update.message.reply_text("Do you prefer aggressive teammates? (yes/no)")
    return AGGRO

async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['aggressive_preference'] = update.message.text.lower() == 'yes'
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or f"user_{user_id}"
    context.user_data['username'] = username

    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = {}

    users[user_id] = context.user_data.copy()

    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    await update.message.reply_text("✅ Profile saved successfully!")
    return ConversationHandler.END

# ----- Matchmaking Logic -----
async def find_teammate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        await update.message.reply_text("❌ Could not load user data.")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ You haven't set up your profile yet. Use /start in DM.")
        return

    current = users[user_id]
    scored = []

    for uid, data in users.items():
        if uid == user_id:
            continue
        score = 0
        if abs(current['premier_rating'] - data['premier_rating']) <= 500:
            score += 2
        if current['talkative'] == data['talkative']:
            score += 1
        if current['language'] == data['language']:
            score += 1
        if current['preferred_role'] != data['preferred_role']:
            score += 1
        elif current['preferred_role'] == 'IGL':
            score += 2
        if any(m in data['favorite_maps'] for m in current['favorite_maps']):
            score += 2

        ratings = data.get("ratings", {})
        score += ratings.get("very_friendly", 0) * 0.5
        score += ratings.get("good_player", 0) * 0.3
        score -= ratings.get("didnt_choose", 0) * 0.2
        score -= ratings.get("no_show", 0) * 0.5

        scored.append((score, data))

    top_matches = sorted(scored, key=lambda x: x[0], reverse=True)[:4]

    if top_matches:
        reply = "\n\n".join([
            f"🔹 {match['username']}\nRating: {match['premier_rating']} | Role: {match['preferred_role']}\nMaps: {', '.join(match['favorite_maps'])}\n"
            f"Talkative: {'Yes' if match['talkative'] else 'No'} | Mic: {'Yes' if match['microphone'] else 'No'}\n"
            f"Ratings: 👍 {match.get('ratings', {}).get('very_friendly', 0)} | 🎯 {match.get('ratings', {}).get('good_player', 0)} | 🚫 {match.get('ratings', {}).get('didnt_choose', 0)} | ❌ {match.get('ratings', {}).get('no_show', 0)}"
            for _, match in top_matches
        ])
        await update.message.reply_text(f"🎯 Top teammate suggestions:\n\n{reply}")

        MATCH_LOG[user_id] = {
            "time": datetime.now(),
            "teammates": [t[1]['username'] for t in top_matches]
        }
        await schedule_review_prompt(context, user_id, MATCH_LOG[user_id]["teammates"])

    else:
        await update.message.reply_text("❌ No suitable teammates found.")

# ----- 45-Minute Review Prompt -----
async def schedule_review_prompt(context, user_id, teammates):
    await asyncio.sleep(2700)  # 45 minutes
    keyboard = [
        [InlineKeyboardButton("✅ Very friendly teammate", callback_data=f"rate:{teammates[0]}:very_friendly")],
        [InlineKeyboardButton("🎯 Good playing teammate", callback_data=f"rate:{teammates[0]}:good_player")],
        [InlineKeyboardButton("🚫 Didn't choose him", callback_data=f"rate:{teammates[0]}:didnt_choose")],
        [InlineKeyboardButton("❌ Didn't show up", callback_data=f"rate:{teammates[0]}:no_show")]
    ]
    await context.bot.send_message(chat_id=int(user_id), text=f"⏱ 45 minutes ago we matched you with {teammates[0]}\nHow was the experience?", reply_markup=InlineKeyboardMarkup(keyboard))

# ----- Rating Handler -----
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, teammate_username, rating = query.data.split(":")

    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        return await query.edit_message_text("⚠️ Could not update rating.")

    for uid, data in users.items():
        if data.get("username") == teammate_username:
            if "ratings" not in data:
                data["ratings"] = {}
            data["ratings"][rating] = data["ratings"].get(rating, 0) + 1
            break

    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    await query.edit_message_text(f"✅ Thank you for your feedback on {teammate_username}!")

# ----- Cancel -----
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# ----- Main App -----
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable not set")

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PREMIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_wingman)],
            WINGMAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_maps)],
            MAPS: [CommandHandler("done", done_maps), MessageHandler(filters.TEXT & ~filters.COMMAND, collect_map)],
            TALKATIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_role)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_mic)],
            MIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_hours)],
            HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_team_type)],
            TEAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_language)],
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_aggro)],
            AGGRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_user)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("find", find_teammate))
    app.add_handler(CallbackQueryHandler(handle_rating, pattern=r"^rate:.*"))

    app.run_polling()

if __name__ == "__main__":
    main()
