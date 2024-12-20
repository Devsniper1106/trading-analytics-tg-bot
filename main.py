from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode
from sendDM import start_dm_service, stop_dm_service
from subscribe import payment_start, button_handler
from callback import address_message_handler
import telegram
from database_function import db
from datetime import datetime
import asyncio
import os
from dotenv import load_dotenv
import logging
load_dotenv()
bot_token = os.getenv("bot_token")

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        context.user_data['subscribe_input_flag'] = False
        last_active = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update user data
        db.update_user_data(
            chat_id=update.message.chat_id,
            username=update.message.from_user.username,
            last_active=last_active
        )
        
        # Get user data
        user_data = db.get_user(update.message.chat_id)
        expired_time = user_data.get("expired_time") if user_data else None
        
        if expired_time is None:
            expired_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        current_time = datetime.now()
        expired_time_dt = datetime.strptime(expired_time, '%Y-%m-%d %H:%M:%S')
        is_active = expired_time_dt > current_time
        
        message = (
            "🎉 *Welcome to CryptoAdvisor Bot!*\n\n"
            "I'm here to help you track and analyze cryptocurrencies.\n"
            "I can help you find the best tokens to invest in.\n"
            f"{'Your subscription is active' if is_active else 'Your subscription is expired'}\n"
            f"Your expired time is {expired_time}\n"
            "Run /help to see all available commands."
        )
        
        await update.message.reply_text(text=message, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_name = update.message.from_user.first_name
        await update.message.reply_text(f'Hello {user_name}! How can I assist you today?')
    except Exception as e:
        logger.error(f"Error in hello command: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = (
            "🤖 *Welcome to CryptoAdvisor Bot!*\n\n"
            "I am your AI-powered cryptocurrency market assistant. Here's what I can do for you:\n\n"
            "📊 *Key Features:*\n"
            "• Real-time cryptocurrency analysis and monitoring\n"
            "• Market trend detection and insights\n" 
            "• Detailed metrics including market cap, volume, ATH\n"
            "• AI-powered price movement predictions\n"
            "• Premium features available via subscription\n\n"
            "🔍 *Available Commands:*\n"
            "• /start - Begin interaction\n"
            "• /hello - Get a greeting\n"
            "• /help - Show this help message\n"
            "• /subscribe - Access premium features\n\n"
            "Simply send me a token address to get detailed analytics!"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def start_sendDm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await start_dm_service()
        await update.message.reply_text("DM service started successfully!")

    except Exception as e:
        logger.error(f"Error starting DM service: {e}")
        await update.message.reply_text("Failed to start DM service. Please try again later.")

async def stop_sendDm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await stop_dm_service()
    except Exception as e:
        logger.error(f"Error stopping DM service: {e}")
        await update.message.reply_text("Failed to stop DM service. Please try again later.")

async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        context.user_data['subscribe_input_flag'] = True
        await payment_start(update=update, context=context)
    except Exception as e:
        logger.error(f"Error in payment process: {e}")
        await update.message.reply_text("Payment process failed. Please try again later.")

async def setup_handlers(application):
    handlers = [
        CommandHandler("hello", hello),
        CommandHandler("start", start),
        CommandHandler("help", help),
        CommandHandler("subscribe", start_payment),
        CommandHandler("startdm", start_sendDm),
        CommandHandler("stopdm", stop_sendDm),
        CallbackQueryHandler(button_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, address_message_handler)
    ]
    
    for handler in handlers:
        application.add_handler(handler)

async def main():
    try:
        application = ApplicationBuilder().token(bot_token).build()

        # Add await here
        await setup_handlers(application)
        
        print("👟👟Bot is running...")
        logger.info("Bot is starting...")
        
        # Run the bot
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    try:
        # Use asyncio.run() to run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")