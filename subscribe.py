from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ContextTypes

from math_function import convert_usd_to_crypto
import aiohttp
from database_function import db
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from decimal import Decimal
import asyncio
from functools import wraps
import json
import os
from dotenv import load_dotenv
load_dotenv()



# Enhanced Constants with more options
WALLET_ADDRESSES: Dict[str, str] = {
    "BSC": "0xDD025846edc0Be0F5374817a49250d2e5890C73B",# 0xF560D0dEbAeFE59a6012037b338eab6F5ebfde66 # 0x29f3a673fbb4d1b311f92ad659c04087bfd510a039fade4d0853b301831a3d72 # 0.008722 BNB
    "ETH": "0x310166751C19a2b1C37129a52ff8b433D8C6Df17", # 0xbb985902c457c623178efde482b2e08ac2f66106 # 0x60be1425015791c39fe17e2cc8b230734988e999cc9a9a696d5785854a119be2
    "SOL": "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",# JD38n7ynKYcgPpF7k1BhXEeREu1KqptU93fVGy3S624k # 33bkeyDdtous4izFwhWWPFQvhVPERDd4Y1t6PN4HrbwthY1MGgBEwwcFVSox9bdENww5Z6R91mwaMCSHoLruij5k # 0.00004 sol   
    #"TON": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
}

SUBSCRIPTION_PLANS_GROUP = [
    {"duration": 1, "price": 500, "label": "1 Month", "discount": 0},
    {"duration": 3, "price": 1200, "label": "3 Months", "discount": 20},
    {"duration": 12, "price": 5000, "label": "1 Year", "discount": 30}
]

SUBSCRIPTION_PLANS_USER = [
    {"duration": 1, "price": 50, "label": "1 Month", "discount": 0},
    {"duration": 3, "price": 120, "label": "3 Months", "discount": 20},
    {"duration": 12, "price": 500, "label": "1 Year", "discount": 30}
]

SUPPORTED_CHAINS = list(WALLET_ADDRESSES.keys())
MIN_WALLET_LENGTH = 10
MIN_TX_HASH_LENGTH = 10
MAX_RETRIES = 3
RETRY_DELAY = 2

# Chain-specific configurations
CHAIN_CONFIGS = {
    "ETH": {
        "decimals": 18,
        "explorer_api": "https://api.etherscan.io/api",
        "api_kkey": os.getenv("ETHERSCAN_API_KEY"),
        "action": "eth_getTransactionByHash"
    },
    "BSC": {
        "decimals": 18,
        "explorer_api": "https://api.bscscan.com/api",
        "api_kkey": os.getenv("BSCSCAN_API_KEY"),
        "action": "eth_getTransactionByHash"
    },
    "SOL": {
        "decimals": 9,
        "explorer_api": "https://api.solscan.io",
        "api_kkey": os.getenv("SOLSCAN_API_KEY"),
        "action": "sol_getTransactionByHash"
    },
    "TON": {
        "decimals": 18,
        "explorer_api": "https://api.tonscan.com/api",
        "api_kkey": os.getenv("TONSCAN_API_KEY"),
        "action": "ton_getTransactionByHash"
    }
}

def retry_on_failure(max_retries: int = MAX_RETRIES, delay: int = RETRY_DELAY):
    """Decorator to retry functions on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    print(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                    print(f"Retrying in {wait_time} seconds...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        print("Max retries reached. Giving up.")
            return False
        return wrapper
    return decorator

def get_duration_keyboard(chat_id: int) -> List[List[InlineKeyboardButton]]:
    """Generate enhanced keyboard for subscription duration selection with discounts."""
    keyboard = []
    row = []
    if db.get_user(chat_id=chat_id).get("is_group") == True:
        SUBSCRIPTION_PLANS= SUBSCRIPTION_PLANS_GROUP
    else:
        SUBSCRIPTION_PLANS= SUBSCRIPTION_PLANS_USER
    for i, plan in enumerate(SUBSCRIPTION_PLANS):
        display_text = f"{plan['label']} (${plan['price']}"
        if plan['discount'] > 0:
            display_text += f" - {plan['discount']}% OFF)"
        else:
            display_text += ")"
            
        button = InlineKeyboardButton(
            display_text,
            callback_data=f"duration:{plan['duration']}:{plan['price']}"
        )
        row.append(button)
        if len(row) == 2 or i == len(SUBSCRIPTION_PLANS) - 1:
            keyboard.append(row)
            row = []
    return keyboard

def get_payment_keyboard() -> List[List[InlineKeyboardButton]]:
    """Generate enhanced keyboard for payment chain selection."""
    keyboard = []
    row = []
    for i, chain in enumerate(SUPPORTED_CHAINS):
        row.append(InlineKeyboardButton(chain, callback_data=f"pay:{chain}"))
        if len(row) == 3 or i == len(SUPPORTED_CHAINS) - 1:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton("Back", callback_data="back")])
    return keyboard

async def payment_start(update: Update, context: CallbackContext) -> None:
    """Initialize the enhanced subscription process."""
    chat_id = update.effective_chat.id
    print(f"Starting payment process for chat_id: {chat_id}")
    print("🎈",context.user_data)
    keyboard = get_duration_keyboard(chat_id)
    message = (
        f"🔥 {'👥Group' if db.get_user(chat_id=chat_id).get('is_group') else '👤User'} *Premium Subscription Plans*\n\n"
        "Choose your subscription duration:\n\n"
        "✨ *Benefits Include:*\n"
        "• Real-time market analysis and alerts\n"
        "• Advanced AI-powered price predictions\n"
        "• Priority 24/7 support\n"
        "• Exclusive trading signals\n"
        "• Custom portfolio tracking\n"
        "• Risk management tools\n\n"
        "🎉 *Special Offer:*\n"
        "• Save up to 30% on longer subscriptions!\n\n"
        "👥 *Group Plans Benefits:*\n"
        "• Additional discounts for group subscriptions\n"
        "• Shared access to premium features among group members\n"
        "• Enhanced collaboration tools for group trading strategies\n\n"
        "👤 *Individual Plans Benefits:*\n"
        "• Personalized support tailored to your trading needs\n"
        "• Exclusive insights and recommendations based on your preferences\n"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data["current_state"] = "duration_selection"

async def handle_duration_selection(update: Update, context: CallbackContext, duration: int, price: float) -> None:
    """Handle enhanced duration selection callback."""
    chat_id = update.effective_chat.id
    if db.get_user(chat_id=chat_id).get("is_group") == True:
        SUBSCRIPTION_PLANS= SUBSCRIPTION_PLANS_GROUP
    else:
        SUBSCRIPTION_PLANS= SUBSCRIPTION_PLANS_USER
    selected_plan = next((plan for plan in SUBSCRIPTION_PLANS if plan['duration'] == duration), None)
    if selected_plan and selected_plan['discount'] > 0:
        original_price = price
        price = price * (100 - selected_plan['discount']) / 100
        context.user_data['discount_applied'] = selected_plan['discount']
        context.user_data['original_price'] = original_price

    context.user_data.update({
        "duration": duration,
        "price": Decimal(str(price)),
        "current_state": "payment_selection",
        "selection_timestamp": datetime.now().isoformat()
    })

    keyboard = get_payment_keyboard()
    message = "Select your preferred payment chain:"
    await context.bot.send_message(
        chat_id=chat_id, 
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_payment_chain_selection(update: Update, context: CallbackContext, chain: str) -> None:
    """Handle payment chain selection callback."""
    chat_id = update.effective_chat.id
    
    context.user_data.update({
        "payment_chain": chain,
        "current_state": "wallet_input"
    })
    
    message = (
        "Please enter your wallet address for receiving rewards.\n\n"
        "This wallet will be used for future reward distributions and premium features."
    )
    await context.bot.send_message(chat_id=chat_id, text=message)

async def handle_wallet_input(update: Update, context: CallbackContext, wallet_address: str) -> None:
    """Handle wallet address input."""
    chat_id = update.effective_chat.id
    username = update.message.from_user.username
    if len(wallet_address) < MIN_WALLET_LENGTH:
        await update.message.reply_text("❌ Invalid wallet address. Please try again.")
        return
    
    try:
        price_usd = context.user_data.get("price", 0)
        duration = context.user_data.get("duration", 1)
        chain = context.user_data.get("payment_chain")
        
        crypto_amounts = convert_usd_to_crypto(float(price_usd))
        expected_amount = crypto_amounts.get(chain)
        

        # Get current expired date from database
        current_expired = db.get_expired_date(chat_id)
        
        # Calculate new expired date
        if current_expired and current_expired > datetime.now():
            # If user has active subscription, add duration to current expired
            expired_date = current_expired + timedelta(days=duration * 30)
        else:
            # If no active subscription or expired, calculate from now
            expired_date = datetime.now() + timedelta(days=duration * 30)

        context.user_data.update({
            "chat_id": chat_id,
            "username": username,
            "wallet_address": wallet_address,
            "expected_amount": price_usd,
            "current_state": "awaiting_payment",
            "expired_date": expired_date
        })
        print(f"chat_id: {chat_id}, wallet_address: {wallet_address}, chain: {chain}")
        # Update user's payment details in database with chain-specific wallet address
        if chain == "ETH":
           db.update_user_data(chat_id=chat_id, ETH_wallet_address=wallet_address, payment_method=chain)
        elif chain == "BSC": 
           db.update_user_data(chat_id=chat_id, BTC_wallet_address=wallet_address, payment_method=chain)
        elif chain == "SOL":
           db.update_user_data(chat_id=chat_id, USDT_wallet_address=wallet_address, payment_method=chain)
        else:
            print(f"Unsupported payment chain: {chain}")
            raise ValueError(f"Unsupported payment chain: {chain}")

        keyboard = [        
            [InlineKeyboardButton("Cancel", callback_data="back")]
        ]

        message = (
            f"💳 *Payment Details*\n\n"
            f"Amount: {expected_amount} {chain} (${price_usd})\n"
            f"Send to address:\n`{WALLET_ADDRESSES[chain]}`\n\n"
            f"your reward username: {username}\n\n"
            f"Your reward wallet:\n`{wallet_address}`\n\n"
            f"Duration: {duration} {'month' if duration == 1 else 'months'}\n"
            f"Expires: {expired_date.strftime('%Y-%m-%d')}\n\n"
            "please input your transaction hash and wait for verification just a moment"
        )

        await update.message.reply_text(
            text=message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print(f"Error processing wallet for chat_id {chat_id}: {str(e)}")
        await update.message.reply_text("❌ Error processing wallet. Please try again.")

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    current_state = context.user_data.get("current_state", "")

    if current_state == "duration_selection" and query.data.startswith("duration:"):
        _, duration, price = query.data.split(":")
        await handle_duration_selection(update, context, int(duration), float(price))
    
    elif current_state == "payment_selection" and query.data.startswith("pay:"):
        chain = query.data.split(":")[1]
        await handle_payment_chain_selection(update, context, chain)
    
    elif query.data == "back":
        keyboard = get_duration_keyboard(chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Select your subscription duration:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["current_state"] = "duration_selection"
    
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Invalid action. Please try again."
        )

async def handle_payment_verification(update: Update, context: CallbackContext, tx_hash: str) -> None:
    
    chat_id = update.effective_chat.id
    print(f"🚀 Starting payment verification journey for chat_id: {chat_id}")
    
    if not tx_hash or len(tx_hash) < MIN_TX_HASH_LENGTH:
        await update.message.reply_text("❌ Invalid transaction hash. Please provide a valid transaction hash.")
        print(f"😕 Invalid transaction hash provided by chat_id {chat_id}")
        return

    chain = context.user_data.get("payment_chain", "")
    if not chain or chain not in SUPPORTED_CHAINS:
        await update.message.reply_text("❌ Invalid payment chain. Please start the payment process again.")
        print(f"😫 Invalid payment chain {chain} for chat_id {chat_id}")
        return

    expected_amount = context.user_data.get("expected_amount", 0)
    if chain == "BSC":
        expected_amount=0.008722 ############################################################################################################################################
    elif chain == "ETH":
        expected_amount=0.02618 ############################################################################################################################################
    elif chain == "SOL":
        expected_amount=0.00004 ############################################################################################################################################
    else:
        expected_amount=0
    payment_address = WALLET_ADDRESSES.get(chain)
    print(f"💰 Expected payment: {expected_amount} {chain} to {payment_address}")
    
    await update.message.reply_text("🔍 Verifying your transaction, please wait...")
    print(f"🔎 Starting detailed transaction verification for chat_id {chat_id}, chain {chain}, tx_hash {tx_hash}")

    try:
        tx_details = await verify_transaction(chain, tx_hash, expected_amount, payment_address)
        print(tx_details)
        if not tx_details:
            await update.message.reply_text(
                "❌ Transaction verification failed.\n"
                "Please ensure:\n"
                "• The transaction hash is correct\n"
                "• You've sent the exact amount required\n"
                "• The transaction is confirmed on the blockchain\n"
                "• You've sent to the correct address"
            )
            print(f"😢 Transaction verification failed for chat_id {chat_id}, tx_hash {tx_hash}")
            return

        expired_date = context.user_data.get("expired_date")
        if not expired_date:
            await update.message.reply_text("❌ Invalid expired date. Please start the payment process again.")
            print(f"Missing expired date for chat_id {chat_id}")
            return
        print(expired_date)    
        total_amount = float(context.user_data.get("price", 0))  # Convert Decimal to float
        username = update.message.from_user.username
        db.update_user_data(
            chat_id=chat_id,
            username=username,
            # is_paid=True,
            total_amount=total_amount,
            transaction_hash=tx_hash,
            last_paid_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            expired_time=expired_date.strftime('%Y-%m-%d %H:%M:%S'),
            payment_method=chain,
            ETH_wallet_address=tx_details['from_address'] if chain == "ETH" else None,
            BTC_wallet_address=tx_details['from_address'] if chain == "BTC" else None,
            USDT_wallet_address=tx_details['from_address'] if chain == "USDT" else None
        )
        print(f"✅ Payment successfully recorded in database for chat_id {chat_id}")
        
        success_message = (
            "✅ *Payment Verified Successfully!*\n\n"
            "*Transaction Details:*\n"
            f"• Amount: {tx_details['amount']} {chain}\n"
            f"• Time: {tx_details['timestamp']}\n"
            f"• From: `{tx_details['from_address']}`\n"
            f"• To: `{tx_details['to_address']}`\n\n"
            "🎉 *Your Premium Subscription is Now Active!*\n"
            f"• Expires: {expired_date.strftime('%Y-%m-%d')}\n\n"
            "Enjoy your enhanced features and premium benefits!"
        )
        
        await update.message.reply_text(
            text=success_message,
            parse_mode="Markdown"
        )
        print(f"🎉 Payment verification completed successfully for chat_id {chat_id}")
        
        # Clear user data after successful verification
        context.user_data.clear()
        
    except Exception as e:
        print(f"😱 Payment verification error for chat_id {chat_id}: {str(e)}")
        await update.message.reply_text(
            "❌ An error occurred during verification.\n"
            "Please contact support if the issue persists."
        )

@retry_on_failure()
async def verify_transaction(chain: str, tx_hash: str, expected_amount: float, payment_address: str) -> Optional[Dict]:
    """Enhanced transaction verification with better validation and error handling."""
    try:
        print(f"🔄 Starting transaction verification process for chain {chain}, tx_hash {tx_hash}")
        async with aiohttp.ClientSession() as session:
            if chain == "SOL":
                tx_details = await verify_solana_transaction(session, tx_hash)
            elif chain in ("BSC", "ETH", "TON"):
                tx_details = await verify_evm_transaction(session, chain, tx_hash)
            else:
                print(f"❌ Unsupported chain: {chain}")
                return None

            if not tx_details:
                print(f"😕 No transaction details found for {chain} tx: {tx_hash}")
                return None

            # Validate transaction details
            amount = tx_details.get("amount", 0)
            to_address = tx_details.get("to_address", "").lower()
            if chain == "BSC":
                expected_amount=0.008722 ############################################################################################################################################
            elif chain == "ETH":
                expected_amount=0.02618 ############################################################################################################################################
            elif chain == "SOL":
                expected_amount=0.00004 ############################################################################################################################################
            else:
                expected_amount=0
            
            expected_address = payment_address.lower()
            # print(f"🔍 Validating transaction - Amount: {amount}, Expected: {expected_amount}")
       
            if (abs(float(amount) - float(expected_amount)) <= 0.0001 and
                to_address == expected_address
                ):
                # print(f"✨ Transaction validation successful for {chain} tx: {tx_hash}")
                return {
                    **tx_details,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            print(f"❌ Transaction validation failed for {chain} tx: {tx_hash}")
            return None

    except Exception as e:
        print(f"💥 Error verifying {chain} transaction: {str(e)}")
        return None

@retry_on_failure()
async def verify_solana_transaction(session: aiohttp.ClientSession, tx_hash: str) -> Optional[Dict]:
    """Enhanced Solana transaction verification."""
    api_url = f"{CHAIN_CONFIGS['SOL']['explorer_api']}/transaction/{tx_hash}"
    print(f"🌟 Verifying Solana transaction: {tx_hash}")
    
    try:
        async with session.get(api_url) as response:
            if response.status != 200:
                print(f"😫 Solana API error: {response.status}")
                return None

            data = await response.json()
            if not data or "transaction" not in data:
                print(f"😕 Invalid Solana transaction data for tx: {tx_hash}")
                return None

            print(f"✨ Successfully retrieved Solana transaction data for tx: {tx_hash}")
            return {
                "amount": float(data["transaction"]["amount"]) / 10**CHAIN_CONFIGS["SOL"]["decimals"],
                "to_address": data["transaction"]["to"],
                "from_address": data["transaction"]["from"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            }

    except Exception as e:
        print(f"💥 Solana verification error: {str(e)}")
        return None

@retry_on_failure()
async def verify_evm_transaction(session: aiohttp.ClientSession, chain: str, tx_hash: str) -> Optional[Dict]:
    """Enhanced EVM transaction verification with better error handling."""
    config = CHAIN_CONFIGS.get(chain)
    if not config:
        print(f"😱 Missing configuration for chain: {chain}")
        return None

    api_key = config["api_kkey"]  # Should be stored securely
    api_url = config["explorer_api"]
    # print(f"🚀 Starting EVM transaction verification for {chain}")
    print("tx_hash-------",tx_hash)   
    params = {
        "module": "proxy",
        "action": config["action"],
        "txhash": tx_hash,
        "apikey": api_key
    }
    
    try:
        async with session.get(api_url, params=params) as response:
            if response.status != 200:
                print(f"😫 {chain} API error: {response.status}")
                return None

            data = await response.json()
            result = data.get("result")
            print(f"📝 Raw transaction data: {result}")
            if not result:
                print(f"😕 No transaction data found for {chain} tx: {tx_hash}")
                return None
            # print(f"🚀 {chain} transaction verification successful for tx: {tx_hash}")
            print({
                "amount": int(result["value"],16) / 10**config["decimals"],
                "to_address": result["to"],
                "from_address": result["from"]
            })
            return {
                "amount": int(result["value"],16) / 10**config["decimals"],
                "to_address": result["to"],
                "from_address": result["from"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

           
    except Exception as e:
        print(f"💥 {chain} verification error1: {str(e)}")
        return None
