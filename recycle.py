import asyncio
import telegram
import requests
import json
from database_function import db
import os
from dotenv import load_dotenv
from ai_insight import ai_insight
from pymongo import MongoClient
from datetime import datetime
from messagecollection import main
from telegram.constants import ParseMode

load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
mongo_client = MongoClient(mongo_uri)
mongodb = mongo_client["telegram_bot_db"]
token_collection = mongodb["token_contracts"]
TOKEN = os.getenv("bot_token")

URL_TELEGRAM_BASE = f'https://api.telegram.org/bot{TOKEN}'
URL_GET_UPDATES = f'{URL_TELEGRAM_BASE}/getUpdates'

# Flag to control the DM service
dm_task = None

async def send_message(text, chat_id, parse_mode=ParseMode.MARKDOWN):
    try:
        temp_bot = telegram.Bot(token=TOKEN)
        await temp_bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return True
    except telegram.error.TelegramError as e:
        print(f"Failed to send message to {chat_id}: {str(e)}")
        return False

async def send_dm():
    try:
        users = db.get_all_users()
        processed_chat_ids = set()

        if not users:
            print("No users found in database.")
            return

        ai_insight_text = await ai_insight()

        for user in users:
            chat_id = user.get('chat_id')
            if not chat_id:
                print(f"Invalid chat_id for user: {user}")
                continue
                
            is_paid = user.get('is_paid', False)
            username = user.get('username', 'User')
            
            if chat_id not in processed_chat_ids:
                message = (
                    f"Hello {username}!\n\n"
                    f"{' Thank you for being our premium member!' if is_paid else '💫 Upgrade to premium for more features!'}\n"
                    f"{ai_insight_text if is_paid else ''}\n"
                    f"Use /help to see available commands."
                )
                
                if await send_message(text=message, chat_id=chat_id):
                    processed_chat_ids.add(chat_id)
                    print(f"Successfully sent message to {username} (ID: {chat_id})")
                else:
                    print(f"Failed to send message to {username} (ID: {chat_id})")
            
    except Exception as e:
        print(f"Error in send_dm: {str(e)}")

async def stop_dm_service():
    global dm_task
    if dm_task:
        dm_task.cancel()
        try:
            await dm_task
        except asyncio.CancelledError:
            pass
        dm_task = None
    print("DM service stopped successfully")

async def periodic_dm():
    while True:
        try:
            # await asyncio.gather(
            #     message_collection(),
            #     all_token_data_update()
            # )
            # print("Message collection and token data update completed")
            # await asyncio.sleep(10)
            
            print("👇👇👇Periodic DM service starting...")
            await send_dm()
            await asyncio.sleep(300)  # 5 minutes interval
            print(f"Last run: {datetime.now()}")
            
        except asyncio.CancelledError:
            print("DM service cancelled")
            break
        except Exception as e:
            print(f"Error in DM service: {str(e)}")
            await asyncio.sleep(50)

async def start_dm_service():
    global dm_task
    if dm_task is None:
        print("DM service starting...")
        dm_task = asyncio.create_task(periodic_dm())
    else:
        print("DM service is already running")