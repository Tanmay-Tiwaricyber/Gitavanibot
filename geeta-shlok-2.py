import json
import random
import schedule
import time
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import logging
import os
from datetime import datetime
import threading
from datetime import timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import re

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token (replace with your actual bot token)
BOT_TOKEN = "6342548180:AAE23RTMPQlriG8srVsAbg6u87mkgSCSDz8"
# Your group chat ID (replace with your actual group chat ID)
GROUP_CHAT_ID = "-100232068791"
# GROUP_CHAT_ID = "-1002320687914"  # @cbseiansss group
# Message thread ID for Geeta quotes section
GEETA_THREAD_ID = 7262  # The specific thread ID for Geeta quotes
# List of authorized chat IDs (group and private chats)
AUTHORIZED_CHATS = [GROUP_CHAT_ID]
# Set to store private chat IDs that have opted in for hourly quotes
PRIVATE_CHATS = set()
# File to store bookmarks
BOOKMARKS_FILE = "bookmarks.json"

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

def get_share_button(shloka):
    """Create inline keyboard with share and bookmark buttons"""
    # For detailed format shloka
    if 'chapter' in shloka and 'verse' in shloka:
        callback_data_share = f"share_{shloka['chapter']}_{shloka['verse']}"
        callback_data_bookmark = f"bookmark_{shloka['chapter']}_{shloka['verse']}"
    # For simple format shloka
    elif 'chapter_verse' in shloka:
        callback_data_share = f"share_{shloka['chapter_verse']}"
        callback_data_bookmark = f"bookmark_{shloka['chapter_verse']}"
    else:
        return None
        
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Share", callback_data=callback_data_share),
            InlineKeyboardButton("🔖 Bookmark", callback_data=callback_data_bookmark)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

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
    logger.info(f"Selected shloka: {shloka.get('chapter', 'N/A')} {shloka.get('verse', 'N/A')}")
    
    # Format the message
    message = format_shloka_message(shloka)
    
    # Create share button for all shlokas
    reply_markup = get_share_button(shloka)
    
    try:
        if chat_id is None:
            logger.info(f"Attempting to send message to group {GROUP_CHAT_ID} in thread {GEETA_THREAD_ID}")
            # Send to the specific Geeta quotes thread in the group
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=GEETA_THREAD_ID,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            logger.info(f"Shloka sent successfully to Geeta quotes section (Thread ID: {GEETA_THREAD_ID}) in @cbseiansss group!")
        else:
            logger.info(f"Attempting to send message to private chat {chat_id}")
            # Send to private chat
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
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
        "*/shloka* - Get a random shloka\n"
        "*/shloka 2.47* - Get a specific shloka by chapter and verse\n"
        "*/bookmark* - Show your bookmarked shlokas\n"
        "*/bookmark <number>* - View a specific bookmarked shloka\n"
        "*/removebookmark <number>* - Remove a bookmark\n"
        "*/getid* - Get the current chat ID\n"
        "*/test* - Test Geeta quotes section connection\n"
        "*/stopquotes* - Stop receiving hourly quotes\n\n"
        "The bot will automatically send a random shloka every hour to the Geeta quotes section in @cbseiansss group "
        "and to private chats that have started the bot."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def send_shloka_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shloka command with optional chapter-verse lookup"""
    if not is_authorized_chat(update.effective_chat.id):
        return

    try:
        # Check if a specific shloka was requested
        if context.args and len(context.args) > 0:
            shloka_reference = context.args[0]
            logger.info(f"Looking up specific shloka: {shloka_reference}")
            
            # Find the specific shloka
            shloka = find_shloka_by_reference(shloka_reference)
            if not shloka:
                await update.message.reply_text(
                    f"❌ Could not find shloka {shloka_reference}.\n"
                    "Please use format: /shloka 2.47 or /shloka for a random shloka."
                )
                return
        else:
            # Get a random shloka if no specific one was requested
            shlokas = load_shlokas()
            if not shlokas:
                await update.message.reply_text("❌ Error: No shlokas available.")
                return
            shloka = random.choice(shlokas)
            logger.info("Selected random shloka")

        # Format and send the message
        message = format_shloka_message(shloka)
        reply_markup = get_share_button(shloka)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info(f"Shloka sent successfully to chat {update.effective_chat.id}")
        
    except Exception as e:
        error_msg = f"Error sending shloka: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(
            "❌ An error occurred while sending the shloka.\n"
            "Please try again or use /shloka for a random shloka."
        )

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

def find_shloka_by_reference(chapter_verse):
    """Find a specific shloka by its chapter and verse number"""
    try:
        shlokas = load_shlokas()
        
        # Try to parse as chapter.verse format first
        match = re.match(r'(\d+)\.(\d+)', chapter_verse)
        if match:
            chapter, verse = map(int, match.groups())
            # Search for detailed format shloka
            for shloka in shlokas:
                if 'chapter' in shloka and 'verse' in shloka:
                    if int(shloka['chapter']) == chapter and int(shloka['verse']) == verse:
                        return shloka
        
        # If not found or not in chapter.verse format, try simple format
        for shloka in shlokas:
            if 'chapter_verse' in shloka and shloka['chapter_verse'] == chapter_verse:
                return shloka
                
        logger.error(f"Could not find shloka for reference: {chapter_verse}")
        return None
    except Exception as e:
        logger.error(f"Error finding shloka by reference: {e}")
        return None

def create_quote_image(shloka):
    """Create a beautiful quote image with the shloka"""
    try:
        logger.info("Starting create_quote_image execution (re-coded approach).") # Updated log
        # Image dimensions - slightly larger square
        width = 500
        height = 500
        margin = 40 # Adjusted margin for smaller size
        
        # Create a new image with a warm background
        image = Image.new('RGB', (width, height), color='#FFF8E7')  # Warm off-white background
        draw = ImageDraw.Draw(image)
        logger.info("Image and Draw object created.") # Log

        # Use default font for all text content to ensure compatibility
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        content_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()
        
        # Approximate multipliers for default font size based on desired scaling
        title_font_size_multiplier = 3.2 # Increased size more
        header_font_size_multiplier = 2.8 # Increased size more
        content_font_size_multiplier = 2.5 # Increased size more
        footer_font_size_multiplier = 1.8 # Increased size more
        logger.info("Using default fonts with further increased size multipliers.") # Updated log

        # Add decorative border
        border_color = '#8B4513'  # Saddle brown
        border_width = 3
        draw.rectangle([(10, 10), (width-10, height-10)], outline=border_color, width=border_width) # Adjusted border position
        logger.info("Border drawn.") # Log
        
        # Add inner decorative line
        inner_margin = 20 # Adjusted inner margin
        draw.line([(inner_margin, inner_margin), (width-inner_margin, inner_margin)], fill=border_color, width=1)
        draw.line([(inner_margin, height-inner_margin), (width-inner_margin, height-inner_margin)], fill=border_color, width=1)
        logger.info("Inner decorative lines drawn.") # Log
        
        y_text = inner_margin + 10 # Starting Y position for text, adjusted
        
        # Add title
        title = "Bhagavad Gita"
        logger.info(f"Drawing title: {title}") # Log before drawing title
        # Manually position text for default font
        # Calculate accurate text width for centering
        title_width = draw.textlength(title, font=title_font)
        draw.text(((width - title_width) // 2, y_text), title, font=title_font, fill=border_color)
        y_text += 8 * title_font_size_multiplier + 15 # Increased padding
        logger.info("Finished drawing title.") # Log after drawing title

        # Add chapter and verse
        if 'chapter' in shloka and 'verse' in shloka:
            chapter_verse = f"Chapter {shloka.get('chapter', 'N/A')}, Verse {shloka.get('verse', 'N/A')}"
        else:
            chapter_verse = f"Chapter {shloka.get('chapter_verse', 'N/A')}"
        logger.info(f"Drawing chapter/verse: {chapter_verse}") # Log before drawing chapter/verse
        # Manually position text for default font
        # Calculate accurate text width for centering
        chapter_width = draw.textlength(chapter_verse, font=header_font)
        draw.text(((width - chapter_width) // 2, y_text), chapter_verse, font=header_font, fill=border_color)
        y_text += 10 * header_font_size_multiplier + 30 # Increased padding
        logger.info("Finished drawing chapter/verse.") # Log after drawing chapter/verse

        
        # Add decorative line after chapter
        draw.line([(width//4, y_text - 5), (3*width//4, y_text - 5)], fill=border_color, width=1) # Adjusted line position
        logger.info("Line after chapter drawn.") # Log

        y_text += 35 # Increased space after the line

        # Content area width (still needed for wrapping calculation)
        content_width = width - 2 * inner_margin
        logger.info(f"Content area width calculated: {content_width}") # Log content width
        
        # Add content based on shloka format
        if 'sanskrit' in shloka:
            logger.info("Processing detailed shloka format.") # Log detailed format
            # Detailed format
            # Sanskrit text
            sanskrit = shloka.get('sanskrit', 'N/A')
            logger.info(f"Processing sanskrit text: {sanskrit[:50]}...") # Log sanskrit text snippet
            # Calculate wrap width for default font
            wrap_width_sanskrit = int(content_width / (6 * content_font_size_multiplier)) - 5 # Approximate wrap width
            wrapped_sanskrit = textwrap.fill(sanskrit, width=wrap_width_sanskrit)
            
            # Draw multi-line text manually for better control
            for i, line in enumerate(wrapped_sanskrit.split('\n')):
                logger.info(f"Drawing sanskrit line {i}: {line[:50]}...") # Log before drawing each line
                # Manually position text for default font with accurate centering
                line_width = draw.textlength(line, font=content_font)
                draw.text(((width - line_width) // 2, y_text), line, font=content_font, fill='#000000')
                y_text += 8 * content_font_size_multiplier + 4 # Increased spacing
            logger.info("Finished drawing sanskrit.") # Log
            
            y_text += 15 # Increased space after sanskrit

            # Translation
            translation = shloka.get('translation', 'N/A')
            logger.info(f"Processing translation text: {translation[:50]}...") # Log translation text snippet
            # Calculate wrap width for default font
            wrap_width_translation = int(content_width / (6 * content_font_size_multiplier)) - 5
            wrapped_translation = textwrap.fill(translation, width=wrap_width_translation)
            
            for i, line in enumerate(wrapped_translation.split('\n')):
                logger.info(f"Drawing translation line {i}: {line[:50]}...") # Log before drawing each line
                # Manually position text for default font with accurate centering
                line_width = draw.textlength(line, font=content_font)
                draw.text(((width - line_width) // 2, y_text), line, font=content_font, fill='#333333')
                y_text += 8 * content_font_size_multiplier + 4 # Increased spacing
            logger.info("Finished drawing translation.") # Log

            y_text += 15 # Increased space after translation

            # Meaning
            meaning = shloka.get('meaning', 'N/A')
            logger.info(f"Processing meaning text: {meaning[:50]}...") # Log meaning text snippet
            # Calculate wrap width for default font
            wrap_width_meaning = int(content_width / (6 * content_font_size_multiplier)) - 5
            wrapped_meaning = textwrap.fill(meaning, width=wrap_width_meaning)

            for i, line in enumerate(wrapped_meaning.split('\n')):
                logger.info(f"Drawing meaning line {i}: {line[:50]}...") # Log before drawing each line
                # Manually position text for default font with accurate centering
                line_width = draw.textlength(line, font=content_font)
                draw.text(((width - line_width) // 2, y_text), line, font=content_font, fill='#666666')
                y_text += 8 * content_font_size_multiplier + 4 # Increased spacing
            logger.info("Finished drawing meaning.") # Log

        else:
            logger.info("Processing simple shloka format.") # Log simple format
            # Simple format

            # Add Quote heading and text
            quote_heading = "Quote:"
            logger.info(f"Drawing quote heading: {quote_heading}") # Log quote heading
            # Manually position text for default font with accurate centering
            heading_width = draw.textlength(quote_heading, font=content_font)
            draw.text(((width - heading_width) // 2, y_text), quote_heading, font=content_font, fill='#333333') # Using content_font and color
            y_text += 8 * content_font_size_multiplier + 9 # Increased space after heading

            # Quote text
            quote = shloka.get('quote', 'N/A')
            logger.info(f"Processing quote text: {quote[:50]}...") # Log quote text snippet
            # Calculate wrap width for default font
            wrap_width_quote = int(content_width / (6 * content_font_size_multiplier)) - 5
            wrapped_quote = textwrap.fill(quote, width=wrap_width_quote)

            for i, line in enumerate(wrapped_quote.split('\n')):
                logger.info(f"Drawing quote line {i}: {line[:50]}...") # Log before drawing each line
                # Manually position text for default font with accurate centering
                line_width = draw.textlength(line, font=content_font)
                draw.text(((width - line_width) // 2, y_text), line, font=content_font, fill='#333333')
                y_text += 8 * content_font_size_multiplier + 4 # Increased spacing
            logger.info("Finished drawing quote.") # Log
            
            y_text += 15 # Increased space after quote

            # Add Takeaway heading and text
            takeaway_heading = "Takeaway:"
            logger.info(f"Drawing takeaway heading: {takeaway_heading}") # Log takeaway heading
            # Manually position text for default font with accurate centering
            heading_width = draw.textlength(takeaway_heading, font=content_font)
            draw.text(((width - heading_width) // 2, y_text), takeaway_heading, font=content_font, fill='#666666') # Using content_font and color
            y_text += 8 * content_font_size_multiplier + 9 # Increased space after heading

            # Takeaway text
            takeaway = shloka.get('takeaway', 'N/A')
            logger.info(f"Processing takeaway text: {takeaway[:50]}...") # Log takeaway text snippet
            # Calculate wrap width for default font
            wrap_width_takeaway = int(content_width / (6 * content_font_size_multiplier)) - 5
            wrapped_takeaway = textwrap.fill(takeaway, width=wrap_width_takeaway)

            for i, line in enumerate(wrapped_takeaway.split('\n')):
                logger.info(f"Drawing takeaway line {i}: {line[:50]}...") # Log before drawing each line
                # Manually position text for default font with accurate centering
                line_width = draw.textlength(line, font=content_font)
                draw.text(((width - line_width) // 2, y_text), line, font=content_font, fill='#666666')
                y_text += 8 * content_font_size_multiplier + 4 # Increased spacing
            logger.info("Finished drawing takeaway.") # Log

        # Add decorative line before footer - position based on content height
        footer_line_y = y_text + 25 # Increased space after content
        logger.info(f"Drawing footer line at y: {footer_line_y}") # Log footer line position
        draw.line([(width//4, footer_line_y), (3*width//4, footer_line_y)], fill=border_color, width=1)
        logger.info("Footer line drawn.") # Log

        # Add footer - position based on footer_line_y
        footer = "Share the wisdom of Bhagavad Gita"
        footer_y = footer_line_y + 15 # Increased vertical position
        logger.info(f"Drawing footer: {footer} at y: {footer_y}") # Log footer position
        # Manually position text for default font with accurate centering
        footer_width = draw.textlength(footer, font=footer_font)
        draw.text(((width - footer_width) // 2, footer_y), footer, font=footer_font, fill=border_color)
        logger.info("Finished drawing footer.") # Log

        # Add copyright text
        copyright_text = "GitaVaniBot"
        # Position copyright text below footer
        copyright_y = footer_y + 8 * footer_font_size_multiplier + 9 # Increased space after footer
        logger.info(f"Drawing copyright: {copyright_text} at y: {copyright_y}") # Log copyright position
        # Manually position text for default font with accurate centering
        copyright_width = draw.textlength(copyright_text, font=footer_font)
        draw.text(((width - copyright_width) // 2, copyright_y), copyright_text, font=footer_font, fill=border_color)
        logger.info("Finished drawing copyright.") # Log

        # Add decorative corner elements (keep existing)
        corner_size = 15 # Smaller corner size
        logger.info("Drawing corner elements.") # Log before drawing corners
        # Top-left corner
        draw.line([(10, 10), (10+corner_size, 10)], fill=border_color, width=border_width) # Adjusted position
        draw.line([(10, 10), (10, 10+corner_size)], fill=border_color, width=border_width)
        # Top-right corner
        draw.line([(width-10-corner_size, 10), (width-10, 10)], fill=border_color, width=border_width)
        draw.line([(width-10, 10), (width-10, 10+corner_size)], fill=border_color, width=border_width)
        # Bottom-left corner
        draw.line([(10, height-10-corner_size), (10, height-10)], fill=border_color, width=border_width)
        draw.line([(10, height-10), (10+corner_size, height-10)], fill=border_color, width=border_width)
        # Bottom-right corner
        draw.line([(width-10-corner_size, height-10), (width-10, height-10)], fill=border_color, width=border_width)
        draw.line([(width-10, height-10-corner_size), (width-10, height-10)], fill=border_color, width=border_width)
        logger.info("Finished drawing corner elements.") # Log

        # Convert image to bytes
        logger.info("Attempting to save image to bytes.") # Updated log
        img_byte_arr = io.BytesIO()
        try:
            image.save(img_byte_arr, format='PNG', quality=95)  # Higher quality
            logger.info("Image saved to bytes successfully.") # Log successful save
        except Exception as save_error:
            logger.error(f"Error saving image to bytes: {str(save_error)}") # Log specific save error
            return None # Return None if saving fails

        img_byte_arr.seek(0)
        
        logger.info("Successfully created quote image with 500x500 dimensions using default font.") # Updated success log
        return img_byte_arr
    except Exception as e:
        logger.error(f"An unexpected error occurred in create_quote_image: {str(e)}") # Updated error log
        return None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        logger.info(f"Button callback received with data: {query.data}")
        
        if query.data.startswith("share_"):
            logger.info("Share button clicked.")
            # Extract chapter and verse from callback data
            parts = query.data.split("_")
            if len(parts) == 3:  # Detailed format (chapter_verse)
                chapter, verse = parts[1], parts[2]
                chapter_verse = f"{chapter}.{verse}"
            else:  # Simple format (just chapter_verse)
                chapter_verse = parts[1]
            
            logger.info(f"Attempting to find shloka for reference: {chapter_verse}")
            
            # Find the shloka
            shloka = find_shloka_by_reference(chapter_verse)
            if not shloka:
                logger.warning(f"Shloka not found for reference: {chapter_verse}")
                await query.message.reply_text(
                    f"❌ Could not find the shloka for {chapter_verse}.\n"
                    "Please try again or use /shloka to get a new shloka."
                )
                return
            
            # Send "generating" message
            status_message = await query.message.reply_text("🔄 Generating beautiful quote image...")
            logger.info("Sent 'generating' status message.")
            
            try:
                # Create the quote image
                logger.info("Calling create_quote_image function...")
                image_bytes = create_quote_image(shloka)
                logger.info("create_quote_image function returned.")
                
                if not image_bytes:
                    logger.error("create_quote_image returned None.")
                    await status_message.edit_text("❌ Error generating quote image. Please try again.")
                    return
                    
                # Send the image
                caption = "Bhagavad Gita"
                if 'chapter' in shloka and 'verse' in shloka:
                    caption += f" Chapter {shloka['chapter']}, Verse {shloka['verse']}"
                elif 'chapter_verse' in shloka:
                    caption += f" Chapter {shloka['chapter_verse']}"
                
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=image_bytes,
                    caption=caption
                )
                logger.info("Image sent successfully.")
                
                # Delete the status message
                await status_message.delete()
                logger.info("Status message deleted.")
                
            except Exception as e:
                logger.error(f"Error during image generation or sending: {str(e)}")
                try:
                    await status_message.edit_text("❌ Error generating quote image. Please try again.")
                except Exception as edit_error:
                    logger.error(f"Error editing status message: {str(edit_error)}")

        elif query.data.startswith("bookmark_"):
            logger.info("Bookmark button clicked.")
            user_id = str(query.from_user.id)
            bookmarks = load_bookmarks()
            
            # Initialize user's bookmarks if they don't exist
            if user_id not in bookmarks:
                bookmarks[user_id] = []

            # Extract chapter and verse from callback data
            parts = query.data.split("_")
            if len(parts) == 3:  # Detailed format (chapter_verse)
                chapter, verse = parts[1], parts[2]
                chapter_verse = f"{chapter}.{verse}"
            else:  # Simple format (just chapter_verse)
                chapter_verse = parts[1]
            
            # Find the shloka
            shloka = find_shloka_by_reference(chapter_verse)
            if not shloka:
                await query.answer("❌ Could not find the shloka to bookmark.", show_alert=True)
                return

            # Check if already bookmarked
            bookmark_key = get_bookmark_key(shloka)
            if any(get_bookmark_key(b) == bookmark_key for b in bookmarks[user_id]):
                await query.answer("✅ This shloka is already in your bookmarks!", show_alert=True)
                return

            # Add to bookmarks
            bookmarks[user_id].append(shloka)
            save_bookmarks(bookmarks)
            
            # Show confirmation
            if 'chapter' in shloka and 'verse' in shloka:
                await query.answer(
                    f"✅ Added Chapter {shloka['chapter']}, Verse {shloka['verse']} to your bookmarks!",
                    show_alert=True
                )
            else:
                await query.answer(
                    f"✅ Added Chapter {shloka.get('chapter_verse', 'N/A')} to your bookmarks!",
                    show_alert=True
                )

    except Exception as e:
        logger.error(f"Error in button callback: {str(e)}")
        try:
            await query.answer("❌ An error occurred. Please try again.", show_alert=True)
        except:
            pass

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

def load_bookmarks():
    """Load bookmarks from JSON file"""
    try:
        if os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading bookmarks: {e}")
        return {}

def save_bookmarks(bookmarks):
    """Save bookmarks to JSON file"""
    try:
        with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving bookmarks: {e}")

def get_bookmark_key(shloka):
    """Generate a unique key for a shloka"""
    if 'chapter' in shloka and 'verse' in shloka:
        return f"{shloka['chapter']}.{shloka['verse']}"
    return shloka.get('chapter_verse', '')

async def bookmark_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bookmark command to save or list bookmarks"""
    if not is_authorized_chat(update.effective_chat.id):
        return

    user_id = str(update.effective_user.id)
    bookmarks = load_bookmarks()
    
    # Initialize user's bookmarks if they don't exist
    if user_id not in bookmarks:
        bookmarks[user_id] = []

    # If no arguments, show list of bookmarks
    if not context.args:
        if not bookmarks[user_id]:
            await update.message.reply_text(
                "📚 *Your Bookmarks*\n\n"
                "You haven't bookmarked any shlokas yet.\n"
                "Use /bookmark while replying to a shloka message to save it.",
                parse_mode='Markdown'
            )
            return

        # Create message with list of bookmarks
        message = "📚 *Your Bookmarked Shlokas*\n\n"
        for i, bookmark in enumerate(bookmarks[user_id], 1):
            if 'chapter' in bookmark and 'verse' in bookmark:
                message += f"{i}. Chapter {bookmark['chapter']}, Verse {bookmark['verse']}\n"
            else:
                message += f"{i}. Chapter {bookmark.get('chapter_verse', 'N/A')}\n"
        
        message += "\nUse /bookmark <number> to view a bookmarked shloka."
        await update.message.reply_text(message, parse_mode='Markdown')
        return

    # If argument is a number, show that bookmarked shloka
    if context.args[0].isdigit():
        try:
            index = int(context.args[0]) - 1
            if 0 <= index < len(bookmarks[user_id]):
                shloka = bookmarks[user_id][index]
                message = format_shloka_message(shloka)
                reply_markup = get_share_button(shloka)
                await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Invalid bookmark number. Use /bookmark to see your list.")
        except ValueError:
            await update.message.reply_text("❌ Please use a valid number to view a bookmark.")
        return

    # If replying to a message, try to bookmark it
    if update.message.reply_to_message:
        try:
            # Try to extract chapter and verse from the message
            text = update.message.reply_to_message.text
            # Look for chapter and verse in the message
            match = re.search(r'Chapter (\d+), Verse (\d+)', text)
            if match:
                chapter, verse = match.groups()
                shloka = find_shloka_by_reference(f"{chapter}.{verse}")
                if shloka:
                    bookmark_key = get_bookmark_key(shloka)
                    # Check if already bookmarked
                    if any(get_bookmark_key(b) == bookmark_key for b in bookmarks[user_id]):
                        await update.message.reply_text("✅ This shloka is already in your bookmarks!")
                        return
                    
                    bookmarks[user_id].append(shloka)
                    save_bookmarks(bookmarks)
                    await update.message.reply_text(
                        f"✅ Shloka (Chapter {chapter}, Verse {verse}) added to your bookmarks!"
                    )
                else:
                    await update.message.reply_text("❌ Could not find the shloka to bookmark.")
            else:
                await update.message.reply_text(
                    "❌ Please reply to a shloka message to bookmark it.\n"
                    "Or use /bookmark to see your bookmarked shlokas."
                )
        except Exception as e:
            logger.error(f"Error bookmarking shloka: {e}")
            await update.message.reply_text("❌ An error occurred while bookmarking the shloka.")
    else:
        await update.message.reply_text(
            "📚 *How to use bookmarks:*\n\n"
            "1. Reply to a shloka message with /bookmark to save it\n"
            "2. Use /bookmark to see your list of bookmarks\n"
            "3. Use /bookmark <number> to view a specific bookmarked shloka",
            parse_mode='Markdown'
        )

async def remove_bookmark_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removebookmark command to remove a bookmark"""
    if not is_authorized_chat(update.effective_chat.id):
        return

    user_id = str(update.effective_user.id)
    bookmarks = load_bookmarks()
    
    if user_id not in bookmarks or not bookmarks[user_id]:
        await update.message.reply_text("❌ You don't have any bookmarks to remove.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❌ Please specify the bookmark number to remove.\n"
            "Use /bookmark to see your list of bookmarks."
        )
        return

    try:
        index = int(context.args[0]) - 1
        if 0 <= index < len(bookmarks[user_id]):
            removed_shloka = bookmarks[user_id].pop(index)
            save_bookmarks(bookmarks)
            
            # Create confirmation message
            if 'chapter' in removed_shloka and 'verse' in removed_shloka:
                message = f"✅ Removed bookmark: Chapter {removed_shloka['chapter']}, Verse {removed_shloka['verse']}"
            else:
                message = f"✅ Removed bookmark: Chapter {removed_shloka.get('chapter_verse', 'N/A')}"
            
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Invalid bookmark number. Use /bookmark to see your list.")
    except Exception as e:
        logger.error(f"Error removing bookmark: {e}")
        await update.message.reply_text("❌ An error occurred while removing the bookmark.")

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
    application.add_handler(CommandHandler("bookmark", bookmark_command))
    application.add_handler(CommandHandler("removebookmark", remove_bookmark_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the scheduler in a separate thread
    run_scheduler(application)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
