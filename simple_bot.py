import os
import logging
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
import sqlite3
from datetime import datetime

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Config
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://your-app-name.onrender.com')
PORT = int(os.getenv('PORT', 10000))

# Earning settings
EARN_PER_AD = 0.02
MIN_WITHDRAWAL = 1.00
AD_LINK = "https://saladattic.com/vdzzc7mhs6?key=ad6aa00be4469ae37878287b76fbb59e"

# Initialize bot
bot = Bot(token=BOT_TOKEN)

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  first_name TEXT, 
                  username TEXT,
                  balance REAL DEFAULT 0.0,
                  total_earned REAL DEFAULT 0.0,
                  ads_watched INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, first_name, username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)",
                  (user_id, first_name, username))
        conn.commit()
    except Exception as e:
        print(f"Error creating user: {e}")
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ?, total_earned = total_earned + ?, ads_watched = ads_watched + 1 WHERE user_id = ?",
              (amount, amount, user_id))
    conn.commit()
    conn.close()

# Flask Routes
@app.route('/')
def home():
    return "🤖 Asterix Earnings Bot is RUNNING! Visit /set_webhook"

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        success = bot.set_webhook(webhook_url)
        return f"✅ Webhook set to: {webhook_url}" if success else "❌ Webhook setup failed"
    except Exception as e:
        return f"❌ Error: {e}"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, bot)
        process_update(update)
        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error'

# Bot Handlers
def process_update(update):
    try:
        if update.message:
            handle_message(update.message)
        elif update.callback_query:
            handle_callback(update.callback_query)
    except Exception as e:
        logger.error(f"Update error: {e}")

def handle_message(message):
    try:
        user_id = message.from_user.id
        text = message.text or ""
        
        create_user(user_id, message.from_user.first_name, message.from_user.username)
        
        if text.startswith('/start'):
            send_welcome(message)
        elif text == '/balance' or text == '💰 Balance':
            check_balance(message)
        elif text == '📺 Watch Ads':
            watch_ads(message)
        elif text == '💳 Withdraw':
            withdraw(message)
        elif text == '📋 Instructions':
            send_instructions(message)
        else:
            show_menu(message)
    except Exception as e:
        logger.error(f"Message error: {e}")

def show_menu(message):
    keyboard = [
        [KeyboardButton("💰 Balance"), KeyboardButton("📺 Watch Ads")],
        [KeyboardButton("💳 Withdraw"), KeyboardButton("📋 Instructions")]
    ]
    bot.send_message(
        message.from_user.id,
        "Please choose an option:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

def send_welcome(message):
    user = message.from_user
    welcome_text = f"""
🤖 *Welcome to Asterix Earnings Bot* 💰

*Hi {user.first_name}!* 👋

Earn money by watching ads!

💰 *Earn $0.02 per ad*
💵 *Withdraw from $1.00*

Click *📺 Watch Ads* to start earning!
    """
    
    show_menu(message)
    bot.send_message(user.id, welcome_text, parse_mode='Markdown')

def check_balance(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user:
        balance_text = f"""
💼 *Your Balance*

💰 Available: ${user[3]:.2f}
🏆 Total Earned: ${user[4]:.2f}
📊 Ads Watched: {user[5]}

💡 Minimum withdrawal: ${MIN_WITHDRAWAL}
        """
        bot.send_message(user_id, balance_text, parse_mode='Markdown')
    else:
        bot.send_message(user_id, "Please use /start to begin")

def watch_ads(message):
    user_id = message.from_user.id
    
    ad_text = f"""
🎬 *Watch Ad & Earn ${EARN_PER_AD}*

Click the button below to open the ad link.
Watch for 30 seconds, then click *✅ I Watched Complete* to get paid!

💰 *Earning: ${EARN_PER_AD} per ad*
    """
    
    keyboard = [
        [InlineKeyboardButton("🎬 👉 CLICK HERE 👈 - Watch Ad", url=AD_LINK)],
        [InlineKeyboardButton("✅ I Watched Complete", callback_data="confirm_ad")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ad")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bot.send_message(user_id, ad_text, reply_markup=reply_markup, parse_mode='Markdown')

def withdraw(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(user_id, "Please use /start first")
        return
        
    if user[3] < MIN_WITHDRAWAL:
        bot.send_message(
            user_id, 
            f"❌ Minimum withdrawal is ${MIN_WITHDRAWAL}\nYour balance: ${user[3]:.2f}\nWatch more ads! 💰"
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="withdraw_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="withdraw_nagad")],
        [InlineKeyboardButton("📱 Rocket", callback_data="withdraw_rocket")],
        [InlineKeyboardButton("📱 PayPal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bot.send_message(
        user_id,
        f"💳 *Withdrawal Request*\n💰 Balance: ${user[3]:.2f}\nChoose payment method:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def send_instructions(message):
    instructions = """
📋 *How to Earn Money:*

1. Click *📺 Watch Ads*
2. Click the ad link button
3. Watch the ad page
4. Click *✅ I Watched Complete*
5. Get *$0.02* automatically!

💰 *Withdrawal Info:*
- Minimum: $1.00
- Methods: bKash, Nagad, Rocket, PayPal
- Processing: 24-48 hours

Start earning now! 🚀
    """
    bot.send_message(message.from_user.id, instructions, parse_mode='Markdown')

def handle_callback(query):
    try:
        data = query.data
        user_id = query.from_user.id
        
        if data == "confirm_ad":
            update_balance(user_id, EARN_PER_AD)
            user = get_user(user_id)
            
            success_text = f"""
✅ *Payment Credited!* 🎉

💰 Earned: ${EARN_PER_AD}
📊 New Balance: ${user[3]:.2f}
🏆 Total Ads: {user[5]}

Keep watching to earn more! 💰
            """
            bot.edit_message_text(
                success_text,
                chat_id=user_id,
                message_id=query.message.message_id,
                parse_mode='Markdown'
            )
            
        elif data == "cancel_ad":
            bot.edit_message_text(
                "❌ Ad cancelled",
                chat_id=user_id,
                message_id=query.message.message_id
            )
            
        elif data.startswith("withdraw_"):
            method = data.replace("withdraw_", "")
            user = get_user(user_id)
            bot.edit_message_text(
                f"📋 *Withdrawal Instructions*\n\nSend this message:\n`/{method} {user[3]:.2f} YOUR_ACCOUNT_NUMBER`\n\nWe'll process within 24 hours!",
                chat_id=user_id,
                message_id=query.message.message_id,
                parse_mode='Markdown'
            )
            
        elif data == "cancel_withdraw":
            bot.edit_message_text(
                "❌ Withdrawal cancelled",
                chat_id=user_id,
                message_id=query.message.message_id
            )
            
    except Exception as e:
        logger.error(f"Callback error: {e}")

if __name__ == '__main__':
    print("🤖 Starting Asterix Earnings Bot...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
