from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from collections import defaultdict
import time
import logging

BOT_TOKEN = '8011013049:AAFStiHobHvvndOPMsEUyvOrN-Xlww24zms'
ADMIN_ID = 7401896933
FORCE_JOIN_CHANNEL_ID = -1002316557460

FREE_TIME = 5 * 3600  # 5 hours
BONUS_TIME = 4 * 3600  # 4 hours
BANNED_WORDS = ['badword1', 'badword2']  # Example offensive words

GENDERS = ['Male', 'Female', 'Other', 'Prefer not to say']
COUNTRIES = ['India', 'USA', 'UK', 'Canada', 'Bangladesh', 'Pakistan', 'Nepal', 'Other']

users = {}
referrals = defaultdict(set)
waiting = []
total_users = 0

logging.basicConfig(level=logging.INFO)

def check_join(update, context):
    try:
        member = context.bot.get_chat_member(FORCE_JOIN_CHANNEL_ID, update.effective_user.id)
        if member.status not in ['member', 'creator', 'administrator']:
            raise Exception
    except:
        btn = InlineKeyboardMarkup.from_button(InlineKeyboardButton("Join Channel", url="https://t.me/+g-i8Vohdrv44NDRl"))
        update.message.reply_text("Join the channel to use the bot", reply_markup=btn)
        return False
    return True

def start(update: Update, context: CallbackContext):
    if not check_join(update, context): return
    user = update.effective_user
    uid = user.id

    if uid not in users:
        users[uid] = {
            'referrals': set(), 'start_time': time.time(), 'duration': FREE_TIME,
            'partner': None, 'banned': False, 'gender': None, 'age': None, 'country': None
        }
        context.bot.send_message(ADMIN_ID, f"New user joined\nID: {uid}\nName: {user.first_name}")

    if users[uid]['banned']:
        update.message.reply_text("You are banned.")
        return

    update.message.reply_text("Welcome to Dating Bot! Let's start by choosing your gender.")
    gender_btns = [[InlineKeyboardButton(g, callback_data=f"gender:{g}")] for g in GENDERS]
    update.message.reply_text("Select Gender:", reply_markup=InlineKeyboardMarkup(gender_btns))

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    uid = query.from_user.id
    data = query.data

    if data.startswith("gender:"):
        users[uid]['gender'] = data.split(":")[1]
        age_btns = [[InlineKeyboardButton(str(age), callback_data=f"age:{age}")] for age in range(18, 41)]
        query.edit_message_text("Select Age:", reply_markup=InlineKeyboardMarkup(age_btns))

    elif data.startswith("age:"):
        users[uid]['age'] = data.split(":")[1]
        country_btns = [[InlineKeyboardButton(c, callback_data=f"country:{c}")] for c in COUNTRIES]
        query.edit_message_text("Select Country:", reply_markup=InlineKeyboardMarkup(country_btns))

    elif data.startswith("country:"):
        users[uid]['country'] = data.split(":")[1]
        query.edit_message_text("Profile complete! Tap Connect to start chatting.")
        send_main_menu(uid, context)

def send_main_menu(uid, context):
    kb = ReplyKeyboardMarkup([
        ["🔗 Connect", "❌ Stop Search"],
        ["🔌 Disconnect", "⏳ Time"],
        ["🎁 Referral Link"]
    ], resize_keyboard=True)
    context.bot.send_message(uid, "Choose an option:", reply_markup=kb)

def connect(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if users[uid]['partner']:
        update.message.reply_text("You're already connected. Type /disconnect to end it.")
        return

    for u in waiting:
        if u != uid and not users[u]['partner']:
            users[uid]['partner'] = u
            users[u]['partner'] = uid
            waiting.remove(u)
            update.message.reply_text("Connected! Type to chat.")
            context.bot.send_message(u, "Connected! Type to chat.")
            send_info(uid, u, context)
            send_info(u, uid, context)
            return
    waiting.append(uid)
    update.message.reply_text("Searching for a partner...")

def send_info(uid1, uid2, context):
    u = users[uid2]
    text = f"Gender: {u['gender']}\nAge: {u['age']}\nCountry: {u['country']}"
    context.bot.send_message(uid1, text)

def message_handler(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid not in users or users[uid]['banned']: return
    text = update.message.text
    if any(b in text.lower() for b in BANNED_WORDS):
        update.message.reply_text("Message blocked due to inappropriate content.")
        return

    partner = users[uid].get('partner')
    if partner:
        try:
            context.bot.send_chat_action(partner, ChatAction.TYPING)
            context.bot.copy_message(chat_id=partner, from_chat_id=uid, message_id=update.message.message_id)
        except:
            update.message.reply_text("Failed to send message.")

def disconnect(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    partner = users[uid].get('partner')
    if partner:
        users[uid]['partner'] = None
        users[partner]['partner'] = None
        context.bot.send_message(partner, "Your partner disconnected.")
        update.message.reply_text("You disconnected.")
    else:
        update.message.reply_text("You are not connected.")

def stop_search(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid in waiting:
        waiting.remove(uid)
        update.message.reply_text("Search cancelled.")
    else:
        update.message.reply_text("You were not searching.")

def admin_commands(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid != ADMIN_ID: return
    args = update.message.text.split()
    if len(args) < 3: return
    cmd, target_id = args[0], int(args[1])
    if cmd == "🚫" or cmd == "/ban":
        users[target_id]['banned'] = True
        update.message.reply_text(f"User {target_id} banned.")
    elif cmd == "✅" or cmd == "/unban":
        users[target_id]['banned'] = False
        update.message.reply_text(f"User {target_id} unbanned.")

def referral(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    ref_link = f"https://t.me/{context.bot.username}?start={uid}"
    update.message.reply_text(f"Your referral link: {ref_link}")
    
    if uid not in referrals:
        referrals[uid] = set()

    # Check if user has 3 referrals
    if len(referrals[uid]) >= 3:
        users[uid]['duration'] = BONUS_TIME
        update.message.reply_text("Congratulations! You've earned 4 hours of free time for your referrals.")

def time_left(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    elapsed = time.time() - users[uid]['start_time']
    left = users[uid]['duration'] - elapsed
    if left <= 0:
        update.message.reply_text("Your time has expired.")
    else:
        update.message.reply_text(f"Time left: {int(left // 60)} minutes")

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    dp.add_handler(MessageHandler(Filters.regex("^🔗 Connect$"), connect))
    dp.add_handler(MessageHandler(Filters.regex("^🔌 Disconnect$"), disconnect))
    dp.add_handler(MessageHandler(Filters.regex("^❌ Stop Search$"), stop_search))
    dp.add_handler(MessageHandler(Filters.regex("^⏳ Time$"), time_left))
    dp.add_handler(MessageHandler(Filters.regex("^🎁 Referral Link$"), referral))
    dp.add_handler(MessageHandler(Filters.regex("^🚫 Ban.*") | Filters.regex("^✅ Unban.*"), admin_commands))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
