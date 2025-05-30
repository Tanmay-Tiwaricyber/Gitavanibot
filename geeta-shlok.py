import json
import random
import schedule
import time
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
import asyncio
import logging
import os
from datetime import datetime
import threading
from datetime import timezone, timedelta

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token (replace with your actual bot token)
BOT_TOKEN = ""
# Your group chat ID (replace with your actual group chat ID)
GROUP_CHAT_ID = "-1002320687914"  # @cbseiansss group
# Message thread ID for Geeta quotes section
GEETA_THREAD_ID = 7262  # The specific thread ID for Geeta quotes
# List of authorized chat IDs (group and private chats)
AUTHORIZED_CHATS = [GROUP_CHAT_ID]
# Set to store private chat IDs that have opted in for hourly quotes
PRIVATE_CHATS = set()

def get_ist_time():
    """Get current time in Indian Standard Time (IST)"""
    utc_time = datetime.now(timezone.utc)
    ist_time = utc_time + timedelta(hours=5, minutes=30)  # IST is UTC+5:30
    return ist_time.strftime("%I:%M %p IST")

def is_authorized_chat(chat_id):
    """Check if the chat is authorized to receive messages"""
    return str(chat_id) in AUTHORIZED_CHATS or chat_id > 0  # Allow all private chats (positive chat IDs)

def load_shlokas():
    try:
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        all_shlokas = []
        
        # Load shlok.json
        json_path = os.path.join(script_dir, 'shlok.json')
        logger.info(f"Looking for shlok.json at: {json_path}")
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                shlokas = json.load(file)
                all_shlokas.extend(shlokas)
                logger.info(f"Successfully loaded {len(shlokas)} shlokas from shlok.json")
        except FileNotFoundError:
            logger.warning(f"shlok.json file not found at: {json_path}")
        except json.JSONDecodeError:
            logger.error("Error decoding shlok.json file!")
        except Exception as e:
            logger.error(f"Unexpected error loading shlok.json: {str(e)}")
        
        # Load shlok2.json
        json2_path = os.path.join(script_dir, 'shlok2.json')
        logger.info(f"Looking for shlok2.json at: {json2_path}")
        try:
            with open(json2_path, 'r', encoding='utf-8') as file:
                shlokas2 = json.load(file)
                all_shlokas.extend(shlokas2)
                logger.info(f"Successfully loaded {len(shlokas2)} shlokas from shlok2.json")
        except FileNotFoundError:
            logger.warning(f"shlok2.json file not found at: {json2_path}")
        except json.JSONDecodeError:
            logger.error("Error decoding shlok2.json file!")
        except Exception as e:
            logger.error(f"Unexpected error loading shlok2.json: {str(e)}")
        
        if not all_shlokas:
            logger.error("No shlokas loaded from either file!")
            return []
            
        logger.info(f"Total shlokas loaded: {len(all_shlokas)}")
        return all_shlokas
        
    except Exception as e:
        logger.error(f"Unexpected error in load_shlokas: {str(e)}")
        return []

def format_shloka_message(shloka):
    # Check if it's a detailed format shloka
    if 'sanskrit' in shloka:
        message = f"🌺 *Bhagavad Gita Shloka* 🌺\n\n"
        message += f"📖 *Chapter {shloka.get('chapter', 'N/A')}, Verse {shloka.get('verse', 'N/A')}*\n\n"
        message += f"📜 *Sanskrit:*\n`{shloka.get('sanskrit', 'N/A')}`\n\n"
        message += f"🔤 *Transliteration:*\n`{shloka.get('transliteration', 'N/A')}`\n\n"
        message += f"📝 *Translation:*\n_{shloka.get('translation', 'N/A')}_\n\n"
        message += f"💭 *Meaning:*\n_{shloka.get('meaning', 'N/A')}_"
    else:
        # Simple format shloka
        message = f"🌺 *Bhagavad Gita Wisdom* 🌺\n\n"
        message += f"📖 *Chapter {shloka.get('chapter_verse', 'N/A')}*\n\n"
        message += f"📜 *Quote:*\n_{shloka.get('quote', 'N/A')}_\n\n"
        message += f"💡 *Takeaway:*\n_{shloka.get('takeaway', 'N/A')}_"
    
    # Add timestamp in IST
    current_time = get_ist_time()
    message += f"\n\n⏰ *Posted at {current_time}*"
    
    return message

async def send_shloka(context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    logger.info("Starting send_shloka function...")
    shlokas = load_shlokas()
    if not shlokas:
        logger.error("No shlokas available to send!")
        return
    
    # Select a random shloka
    shloka = random.choice(shlokas)
    logger.info(f"Selected shloka from chapter {shloka.get('chapter', 'N/A')}")
    
    # Format the message
    message = format_shloka_message(shloka)
    
    try:
        if chat_id is None:
            logger.info(f"Attempting to send message to group {GROUP_CHAT_ID} in thread {GEETA_THREAD_ID}")
            # Send to the specific Geeta quotes thread in the group
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=GEETA_THREAD_ID,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Shloka sent successfully to Geeta quotes section (Thread ID: {GEETA_THREAD_ID}) in @cbseiansss group!")
        else:
            logger.info(f"Attempting to send message to private chat {chat_id}")
            # Send to private chat
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Shloka sent successfully to private chat {chat_id}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        if "bot was kicked" in str(e).lower():
            logger.error("Bot was kicked from the group. Please add it back and make it an admin.")
        elif "chat not found" in str(e).lower():
            logger.error("Chat ID is incorrect or chat no longer exists.")
        elif "not enough rights" in str(e).lower():
            logger.error("Bot doesn't have enough rights. Please make it an admin with proper permissions.")
        elif "message thread not found" in str(e).lower():
            logger.error("Geeta quotes thread not found. Please check the GEETA_THREAD_ID.")
        else:
            logger.error(f"Unexpected error: {str(e)}")

async def send_hourly_quotes(context: ContextTypes.DEFAULT_TYPE):
    """Send hourly quotes to all opted-in private chats"""
    logger.info(f"Starting hourly quotes distribution to {len(PRIVATE_CHATS)} private chats")
    for chat_id in PRIVATE_CHATS.copy():
        try:
            logger.info(f"Sending hourly quote to private chat {chat_id}")
            await send_shloka(context, chat_id)
            logger.info(f"Successfully sent hourly quote to private chat {chat_id}")
        except Exception as e:
            logger.error(f"Error sending to private chat {chat_id}: {e}")
            if "chat not found" in str(e).lower() or "bot was blocked" in str(e).lower():
                logger.info(f"Removing inactive private chat {chat_id} from the list")
                PRIVATE_CHATS.discard(chat_id)

async def test_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test if the bot can send messages to the Geeta quotes section"""
    if not is_authorized_chat(update.effective_chat.id):
        return

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=GEETA_THREAD_ID,
            text="🔄 *Testing Geeta Quotes Section* 🔄\n\nThis is a test message to verify the bot can send messages to the Geeta quotes section in @cbseiansss group.",
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ Test message sent successfully to the Geeta quotes section!")
    except Exception as e:
        error_msg = f"❌ Error sending test message: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not is_authorized_chat(chat_id):
        await update.message.reply_text(
            "⚠️ *Unauthorized Access* ⚠️\n\n"
            "This bot is only authorized to operate in specific groups and private chats.",
            parse_mode='Markdown'
        )
        return

    if update.effective_chat.type == 'private':
        # Add chat to private chats set for hourly quotes
        PRIVATE_CHATS.add(chat_id)
        # Send immediate welcome shloka
        await send_shloka(context, chat_id)
        await update.message.reply_text(
            "🌺 *Welcome to the Bhagavad Gita Shloka Bot!* 🌺\n\n"
            "✅ You will now receive:\n"
            "• A random shloka every hour\n"
            "• Wisdom from the Bhagavad Gita\n"
            "• Meaningful insights for daily life\n\n"
            "📝 *Available Commands:*\n"
            "• /shloka - Get a random shloka now\n"
            "• /stopquotes - Stop receiving hourly quotes\n"
            "• /help - Show all commands\n\n"
            "💡 You can use /stopquotes anytime to stop receiving hourly quotes.",
            parse_mode='Markdown'
        )
        logger.info(f"New private chat added for hourly quotes: {chat_id}")
    else:
        await update.message.reply_text(
            "I am the Bhagavad Gita Shloka Bot 🌺\n\n"
            "I will share hourly wisdom from the Bhagavad Gita in the Geeta quotes section.\n"
            "Use /help to see available commands."
        )

async def stop_quotes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop sending hourly quotes to a private chat"""
    chat_id = update.effective_chat.id
    if chat_id in PRIVATE_CHATS:
        PRIVATE_CHATS.remove(chat_id)
        await update.message.reply_text(
            "✅ You will no longer receive hourly quotes.\n"
            "Use /start to start receiving quotes again."
        )
    else:
        await update.message.reply_text(
            "You are not currently receiving hourly quotes.\n"
            "Use /start to start receiving quotes."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized_chat(update.effective_chat.id):
        return

    help_text = (
        "🌺 *Bhagavad Gita Shloka Bot Commands* 🌺\n\n"
        "*/start* - Start the bot and receive hourly quotes\n"
        "*/help* - Show this help message\n"
        "*/shloka* - Get a random shloka immediately\n"
        "*/getid* - Get the current chat ID\n"
        "*/test* - Test Geeta quotes section connection\n"
        "*/stopquotes* - Stop receiving hourly quotes\n\n"
        "The bot will automatically send a random shloka every hour to the Geeta quotes section in @cbseiansss group "
        "and to private chats that have started the bot."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def send_shloka_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized_chat(update.effective_chat.id):
        return
    await send_shloka(context, update.effective_chat.id)

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized_chat(update.effective_chat.id):
        return

    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = update.effective_chat.title if update.effective_chat.title else "Private Chat"
    
    message = (
        f"📊 *Chat Information* 📊\n\n"
        f"*Chat Type:* {chat_type}\n"
        f"*Chat Title:* {chat_title}\n"
        f"*Chat ID:* `{chat_id}`\n"
        f"*Geeta Quotes Thread ID:* `{GEETA_THREAD_ID}`\n\n"
        f"Use these IDs in the bot's configuration to send messages to the correct section."
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

def run_scheduler(application):
    """Run the scheduler in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    # Schedule hourly shloka sending
    schedule.every(1).hours.do(lambda: loop.run_until_complete(send_hourly_quotes(application)))
    
    # Send first shloka immediately
    loop.run_until_complete(send_shloka(application))
    
    # Start the scheduler
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()

def main():
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("shloka", send_shloka_command))
    application.add_handler(CommandHandler("getid", get_chat_id))
    application.add_handler(CommandHandler("test", test_group))
    application.add_handler(CommandHandler("stopquotes", stop_quotes))

    # Start the scheduler in a separate thread
    run_scheduler(application)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
