import json
import random
import logging
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

# Logging
logging.basicConfig(level=logging.INFO)

USER_FILE = "cs2_teammates.json"
MATCH_LOG = {}

(PREMIER, WINGMAN, MAPS, TALKATIVE, ROLE, MIC, HOURS, TEAM_TYPE, LANGUAGE, AGGRO) = range(10)

CS2_MAPS = ["Mirage", "Inferno", "Nuke", "Overpass", "Vertigo", "Ancient", "Anubis", "Dust II", "Cache", "Train"]
ROLES = ["Entry", "Support", "AWPer", "Lurker", "IGL"]

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Let's build your CS2 profile.\nWhat is your Premier rating?")
    return PREMIER

async def collect_premier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['premier_rating'] = int(update.message.text)
        await update.message.reply_text("What is your Wingman rank (MG, DMG, GE, etc.)?")
        return WINGMAN
    except ValueError:
        await update.message.reply_text("❌ Enter a number (e.g., 9700)")
        return PREMIER

async def collect_wingman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wingman_rank'] = update.message.text
    await update.message.reply_text("Favorite maps? (comma-separated)\nChoose from: " + ", ".join(CS2_MAPS))
    return MAPS

async def collect_maps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    maps = [m.strip() for m in update.message.text.split(',') if m.strip()]
    if not maps:
        await update.message.reply_text("❌ Enter at least one map.")
        return MAPS
    context.user_data['favorite_maps'] = maps
    keyboard = [[InlineKeyboardButton("Yes", callback_data='talkative_yes'), InlineKeyboardButton("No", callback_data='talkative_no')]]
    await update.message.reply_text("Are you talkative?", reply_markup=InlineKeyboardMarkup(keyboard))
    return TALKATIVE

async def talkative_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['talkative'] = query.data == 'talkative_yes'
    keyboard = [[InlineKeyboardButton(role, callback_data=role)] for role in ROLES]
    await query.edit_message_text("Preferred role?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ROLE

async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['preferred_role'] = query.data
    keyboard = [[InlineKeyboardButton("Yes", callback_data='mic_yes'), InlineKeyboardButton("No", callback_data='mic_no')]]
    await query.edit_message_text("Do you have a microphone?", reply_markup=InlineKeyboardMarkup(keyboard))
    return MIC

async def mic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['microphone'] = query.data == 'mic_yes'
    await query.edit_message_text("What are your available hours? (e.g., 18:00–23:00)")
    return HOURS

async def collect_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['available_hours'] = update.message.text
    keyboard = [[InlineKeyboardButton("Duo", callback_data='Duo'), InlineKeyboardButton("Team", callback_data='Team')]]
    await update.message.reply_text("Looking for Duo or Team?", reply_markup=InlineKeyboardMarkup(keyboard))
    return TEAM_TYPE

async def team_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['team_type'] = query.data
    keyboard = [[InlineKeyboardButton("English", callback_data='English'), InlineKeyboardButton("Russian", callback_data='Russian')]]
    await query.edit_message_text("Preferred language?", reply_markup=InlineKeyboardMarkup(keyboard))
    return LANGUAGE

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['language'] = query.data
    await query.edit_message_text("Rate your aggressiveness (1–5)")
    return AGGRO

async def collect_aggro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = int(update.message.text)
        if not 1 <= value <= 5:
            raise ValueError
        context.user_data['aggressiveness'] = value
    except ValueError:
        await update.message.reply_text("❌ Enter 1–5")
        return AGGRO

    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or "unknown"
    today = datetime.today().strftime("%Y-%m-%d")

    context.user_data.update({
        'daily_rating': {today: random.randint(8000, 10000)},
        'daily_teammate': {},
        'last_updated': datetime.now().isoformat(),
        'username': f"@{username}"
    })

    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = {}

    users[user_id] = context.user_data
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    await update.message.reply_text("✅ Profile saved!")
    return ConversationHandler.END

# Matchmaking + Rating
async def find_teammate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        await update.message.reply_text("❌ Could not load data.")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ Use /start in DM first.")
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
            f"🔹 {m['username']}\nRating: {m['premier_rating']} | Role: {m['preferred_role']}\nMaps: {', '.join(m['favorite_maps'])}\n"
            f"Talkative: {'Yes' if m['talkative'] else 'No'} | Mic: {'Yes' if m['microphone'] else 'No'}\n"
            f"Ratings: 👍 {m.get('ratings', {}).get('very_friendly', 0)} | 🎯 {m.get('ratings', {}).get('good_player', 0)} | 🚫 {m.get('ratings', {}).get('didnt_choose', 0)} | ❌ {m.get('ratings', {}).get('no_show', 0)}"
            for _, m in top_matches
        ])
        await update.message.reply_text(f"🎯 Top teammate suggestions:\n\n{reply}")
        MATCH_LOG[user_id] = {"time": datetime.now(), "teammates": [t[1]['username'] for t in top_matches]}
        await schedule_review_prompt(update, context, user_id, MATCH_LOG[user_id]["teammates"])
    else:
        await update.message.reply_text("❌ No teammates found.")

async def schedule_review_prompt(update, context, user_id, teammates):
    await asyncio.sleep(2700)  # 45 min
    keyboard = [
        [InlineKeyboardButton("✅ Very friendly teammate", callback_data=f"rate:{teammates[0]}:very_friendly")],
        [InlineKeyboardButton("🎯 Good playing teammate", callback_data=f"rate:{teammates[0]}:good_player")],
        [InlineKeyboardButton("🚫 Didn't choose him", callback_data=f"rate:{teammates[0]}:didnt_choose")],
        [InlineKeyboardButton("❌ Didn't show up", callback_data=f"rate:{teammates[0]}:no_show")]
    ]
    await context.bot.send_message(chat_id=int(user_id), text=f"⏱ 45 minutes ago we matched you with {teammates[0]}\nHow was it?", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, username, rating = query.data.split(":")

    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        return await query.edit_message_text("⚠️ Could not update rating.")

    for uid, data in users.items():
        if data.get("username") == username:
            if "ratings" not in data:
                data["ratings"] = {}
            data["ratings"][rating] = data["ratings"].get(rating, 0) + 1
            break

    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    await query.edit_message_text(f"✅ Thanks for your feedback on {username}!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token("7628113009:AAHjVjN00kSN15S_Rxe5gPa2rWCK0kpvTS8").build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PREMIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_premier)],
            WINGMAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_wingman)],
            MAPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_maps)],
            TALKATIVE: [CallbackQueryHandler(talkative_handler)],
            ROLE: [CallbackQueryHandler(role_handler)],
            MIC: [CallbackQueryHandler(mic_handler)],
            HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_hours)],
            TEAM_TYPE: [CallbackQueryHandler(team_type_handler)],
            LANGUAGE: [CallbackQueryHandler(language_handler)],
            AGGRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_aggro)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("find", find_teammate))
    app.add_handler(CallbackQueryHandler(handle_rating, pattern=r"^rate:.*"))

    app.run_polling()

if __name__ == "__main__":
    main()
