import os
import random
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# Load environment variables
load_dotenv()

# States for conversation handler
SELECTING_ACTION, ENTERING_TOKEN, ENTERING_AMOUNT, ENTERING_SELL_QUANTITY = range(4)

# In-memory data storage
USERS: Dict[int, Dict] = {}  # user_id -> user_data
TOKENS = {
    "SUI": {"name": "Sui", "price": 1.0},  # Base token
    "MOON": {"name": "Moon", "price": 0.5},
    "STAR": {"name": "Star", "price": 0.75},
    "ROCKET": {"name": "Rocket", "price": 1.25},
    "GALAXY": {"name": "Galaxy", "price": 0.9},
}
REFERRAL_BONUS = 500.0

# Tutorial messages
TUTORIALS = {
    "welcome": """
🎓 *Welcome to SUI Memecoin Trading Bot!*

This bot lets you practice trading SUI memecoins without using real money. Here's what you can do:

1️⃣ *View Tokens* 📈
   - See available memecoins
   - Check current prices
   - Monitor price changes

2️⃣ *My Portfolio* 💰
   - Track your holdings
   - View unrealized profits/losses
   - Monitor total portfolio value

3️⃣ *Buy Tokens* 💸
   - Choose a token
   - Enter amount in SUI
   - Execute simulated trades

4️⃣ *Sell Tokens* 🧾
   - Select tokens to sell
   - Enter quantity
   - Convert back to SUI

Start with 1000 SUI and begin your trading journey! 🚀
""",
    "view_tokens": """
📈 *How to View Tokens*

1. Click "View Tokens" to see available memecoins
2. Each token shows:
   - Current price in SUI
   - 24h price change
   - Trading volume (simulated)
3. Use the back button to return to main menu
""",
    "portfolio": """
💰 *Understanding Your Portfolio*

Your portfolio shows:
1. Individual token holdings
2. Average purchase price
3. Current value
4. Unrealized profit/loss
5. Total portfolio value
6. Available SUI balance

💡 *Tip*: Monitor your PnL to track trading performance
""",
    "buy": """
💸 *How to Buy Tokens*

1. Click "Buy"
2. Enter token symbol (e.g., MOON)
3. Enter amount in SUI
4. Confirm the trade

💡 *Tips*:
- Start with small amounts
- Check token prices first
- Monitor your SUI balance
""",
    "sell": """
🧾 *How to Sell Tokens*

1. Click "Sell"
2. Select token from your holdings
3. Enter quantity to sell
4. Confirm the trade

💡 *Tips*:
- Sell in portions
- Check current prices
- Monitor your PnL
"""
}

def get_token_price(symbol: str) -> float:
    """Get current token price (simulated with random fluctuations)"""
    base_price = TOKENS[symbol]["price"]
    # Simulate price fluctuation between -5% and +5%
    fluctuation = random.uniform(-0.05, 0.05)
    return base_price * (1 + fluctuation)

def format_price(price: float) -> str:
    """Format price to 4 decimal places"""
    return f"{price:.4f}"

def get_portfolio_value(user_id: int) -> float:
    """Calculate total portfolio value in SUI"""
    if user_id not in USERS:
        return 0.0
    
    total_value = 0.0
    for token, holding in USERS[user_id].get("holdings", {}).items():
        current_price = get_token_price(token)
        total_value += holding["quantity"] * current_price
    
    return total_value

def get_unrealized_pnl(user_id: int) -> float:
    """Calculate unrealized PnL"""
    if user_id not in USERS:
        return 0.0
    
    total_pnl = 0.0
    for token, holding in USERS[user_id].get("holdings", {}).items():
        current_price = get_token_price(token)
        avg_price = holding["avg_price"]
        quantity = holding["quantity"]
        pnl = (current_price - avg_price) * quantity
        total_pnl += pnl
    
    return total_pnl

def format_balance_message(user_id: int) -> str:
    """Format balance message with emojis and highlighting"""
    if user_id not in USERS:
        return "No balance found"
    
    user_data = USERS[user_id]
    total_value = get_portfolio_value(user_id)
    total_pnl = get_unrealized_pnl(user_id)
    
    message = "💎 *Your Balance*\n\n"
    message += f"💰 Available SUI: `{format_price(user_data['sui_balance'])}`\n"
    message += f"📊 Portfolio Value: `{format_price(total_value)}`\n"
    
    # Add PnL with color emoji
    pnl_percentage = (total_pnl / total_value * 100) if total_value > 0 else 0
    pnl_emoji = "🟢" if pnl_percentage >= 0 else "🔴"
    message += f"{pnl_emoji} Unrealized PnL: `{format_price(total_pnl)}` ({pnl_percentage:+.2f}%)\n"
    
    return message

def get_user_data(user_id: int) -> Dict:
    if user_id not in USERS:
        USERS[user_id] = {
            "holdings": {},
            "sui_balance": 1000.0,
            "referral_bonus": REFERRAL_BONUS,
        }
    return USERS[user_id]

def format_main_menu(user_id: int) -> (str, InlineKeyboardMarkup):
    user_data = get_user_data(user_id)
    total_value = get_portfolio_value(user_id)
    total_pnl = get_unrealized_pnl(user_id)
    pnl_percent = (total_pnl / total_value * 100) if total_value > 0 else 0
    pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
    welcome_msg = (
        "👋 <b>Welcome to SUI Memecoin Paper Trading!</b>\n\n"
        f"💰 <b>Balance:</b> <code>{user_data['sui_balance']:.1f} SUI</code>   "
        f"🎁 <b>Bonus:</b> <code>{user_data['referral_bonus']:.1f} SUI</code>\n"
        f"{pnl_emoji} <b>PnL:</b> <code>{total_pnl:+.2f} SUI</code> ({pnl_percent:+.2f}%)\n\n"
        "Choose an action:"
    )
    keyboard = [
        [
            InlineKeyboardButton("🟢 Buy", callback_data="buy"),
            InlineKeyboardButton("🔴 Sell", callback_data="sell"),
        ],
        [
            InlineKeyboardButton("💼 Portfolio", callback_data="portfolio"),
            InlineKeyboardButton("📈 Tokens", callback_data="view_tokens"),
        ],
        [
            InlineKeyboardButton("👥 Invite Friends", callback_data="invite_friends"),
            InlineKeyboardButton("❓ Help", callback_data="tutorials"),
        ],
        [
            InlineKeyboardButton("🔄 Reset", callback_data="reset"),
        ],
    ]
    return welcome_msg, InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    get_user_data(user_id)  # Ensure user is initialized
    welcome_msg, reply_markup = format_main_menu(user_id)
    await update.message.reply_html(welcome_msg, reply_markup=reply_markup)
    return SELECTING_ACTION

async def show_tutorials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show available tutorials"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📈 View Tokens Guide", callback_data="tut_view_tokens")],
        [InlineKeyboardButton("💰 Portfolio Guide", callback_data="tut_portfolio")],
        [InlineKeyboardButton("💸 Buy Guide", callback_data="tut_buy")],
        [InlineKeyboardButton("🧾 Sell Guide", callback_data="tut_sell")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Select a tutorial to learn more:",
        reply_markup=reply_markup
    )
    return SELECTING_ACTION

async def show_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show specific tutorial"""
    query = update.callback_query
    await query.answer()
    
    tutorial_key = query.data.replace("tut_", "")
    tutorial_text = TUTORIALS.get(tutorial_key, "Tutorial not found.")
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Tutorials", callback_data="tutorials")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        tutorial_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    return SELECTING_ACTION

async def view_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show available tokens with their prices"""
    query = update.callback_query
    await query.answer()
    
    message = "📈 *Available Tokens*\n\n"
    for symbol, data in TOKENS.items():
        if symbol != "SUI":  # Skip base token
            current_price = get_token_price(symbol)
            change = random.uniform(-10, 10)  # Simulated price change
            volume = random.uniform(1000, 10000)  # Simulated volume
            
            # Add emoji based on price change
            change_emoji = "🟢" if change >= 0 else "🔴"
            
            message += (
                f"*${symbol}*\n"
                f"Price: `{format_price(current_price)}` SUI\n"
                f"{change_emoji} Change: `{change:+.2f}%`\n"
                f"📊 Volume: `{format_price(volume)}` SUI\n\n"
            )
    
    keyboard = [
        [InlineKeyboardButton("❓ How to View Tokens", callback_data="tut_view_tokens")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    return SELECTING_ACTION

async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user's portfolio"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = USERS[user_id]
    
    # Show balance summary
    message = format_balance_message(user_id) + "\n\n"
    
    # Show holdings
    if user_data.get("holdings"):
        message += "*Your Holdings:*\n\n"
        for token, holding in user_data["holdings"].items():
            current_price = get_token_price(token)
            value = holding["quantity"] * current_price
            pnl = (current_price - holding["avg_price"]) * holding["quantity"]
            pnl_percentage = (pnl / value * 100) if value > 0 else 0
            
            # Add emoji based on PnL
            pnl_emoji = "🟢" if pnl_percentage >= 0 else "🔴"
            
            message += (
                f"*${token}*\n"
                f"Quantity: `{holding['quantity']:.4f}`\n"
                f"Avg Price: `{format_price(holding['avg_price'])}` SUI\n"
                f"Current Value: `{format_price(value)}` SUI\n"
                f"{pnl_emoji} PnL: `{format_price(pnl)}` SUI ({pnl_percentage:+.2f}%)\n\n"
            )
    else:
        message += "You don't have any tokens yet. Use the Buy option to start trading!"
    
    keyboard = [
        [InlineKeyboardButton("❓ Portfolio Guide", callback_data="tut_portfolio")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    return SELECTING_ACTION

async def start_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the buy process"""
    query = update.callback_query
    await query.answer()
    
    message = "Enter the token symbol you want to buy (e.g., MOON, STAR, ROCKET):"
    await query.edit_message_text(text=message)
    return ENTERING_TOKEN

async def process_buy_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the token symbol for buying"""
    token = update.message.text.upper()
    
    if token not in TOKENS or token == "SUI":
        await update.message.reply_text(
            "Invalid token symbol. Please try again with a valid token:"
        )
        return ENTERING_TOKEN
    
    context.user_data["buy_token"] = token
    await update.message.reply_text(
        f"Enter amount in SUI to buy {token}:"
    )
    return ENTERING_AMOUNT

async def process_buy_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the buy amount and execute the trade"""
    try:
        amount = float(update.message.text)
        token = context.user_data["buy_token"]
        user_id = update.effective_user.id
        user_data = USERS[user_id]
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if amount > user_data["sui_balance"]:
            await update.message.reply_text(
                "Insufficient SUI balance. Please enter a smaller amount:"
            )
            return ENTERING_AMOUNT
        
        current_price = get_token_price(token)
        quantity = amount / current_price
        
        # Update user's holdings
        if token not in user_data["holdings"]:
            user_data["holdings"][token] = {
                "quantity": 0,
                "avg_price": 0
            }
        
        # Calculate new average price
        old_quantity = user_data["holdings"][token]["quantity"]
        old_avg_price = user_data["holdings"][token]["avg_price"]
        new_quantity = old_quantity + quantity
        new_avg_price = (
            (old_quantity * old_avg_price + quantity * current_price) / new_quantity
        )
        
        user_data["holdings"][token].update({
            "quantity": new_quantity,
            "avg_price": new_avg_price
        })
        user_data["sui_balance"] -= amount
        
        await update.message.reply_text(
            f"✅ Trade executed!\n"
            f"Bought {quantity:.4f} {token} for {amount:.4f} SUI\n"
            f"Price: {format_price(current_price)} SUI per {token}"
        )
        
        # Show main menu
        keyboard = [
            [
                InlineKeyboardButton("📈 View Tokens", callback_data="view_tokens"),
                InlineKeyboardButton("💰 My Portfolio", callback_data="portfolio"),
            ],
            [
                InlineKeyboardButton("💸 Buy", callback_data="buy"),
                InlineKeyboardButton("🧾 Sell", callback_data="sell"),
            ],
            [InlineKeyboardButton("🔄 Reset Portfolio", callback_data="reset")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select an option:",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
        
    except ValueError:
        await update.message.reply_text(
            "Invalid amount. Please enter a valid number:"
        )
        return ENTERING_AMOUNT

async def start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the sell process"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = USERS[user_id]
    
    if not user_data.get("holdings"):
        await query.edit_message_text(
            "You don't have any tokens to sell.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]])
        )
        return SELECTING_ACTION
    
    keyboard = []
    for token in user_data["holdings"]:
        keyboard.append([InlineKeyboardButton(f"Sell {token}", callback_data=f"sell_{token}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Select token to sell:",
        reply_markup=reply_markup
    )
    return ENTERING_SELL_QUANTITY

async def process_sell_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the token selection for selling"""
    query = update.callback_query
    await query.answer()
    
    token = query.data.split("_")[1]
    context.user_data["sell_token"] = token
    
    await query.edit_message_text(
        f"Enter quantity of {token} to sell:"
    )
    return ENTERING_SELL_QUANTITY

async def process_sell_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the sell quantity and execute the trade"""
    try:
        quantity = float(update.message.text)
        token = context.user_data["sell_token"]
        user_id = update.effective_user.id
        user_data = USERS[user_id]
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if token not in user_data["holdings"] or quantity > user_data["holdings"][token]["quantity"]:
            await update.message.reply_text(
                "Invalid quantity. Please enter a valid amount:"
            )
            return ENTERING_SELL_QUANTITY
        
        current_price = get_token_price(token)
        sui_received = quantity * current_price
        
        # Update holdings
        user_data["holdings"][token]["quantity"] -= quantity
        if user_data["holdings"][token]["quantity"] == 0:
            del user_data["holdings"][token]
        
        user_data["sui_balance"] += sui_received
        
        await update.message.reply_text(
            f"✅ Trade executed!\n"
            f"Sold {quantity:.4f} {token} for {sui_received:.4f} SUI\n"
            f"Price: {format_price(current_price)} SUI per {token}"
        )
        
        # Show main menu
        keyboard = [
            [
                InlineKeyboardButton("📈 View Tokens", callback_data="view_tokens"),
                InlineKeyboardButton("💰 My Portfolio", callback_data="portfolio"),
            ],
            [
                InlineKeyboardButton("💸 Buy", callback_data="buy"),
                InlineKeyboardButton("🧾 Sell", callback_data="sell"),
            ],
            [InlineKeyboardButton("🔄 Reset Portfolio", callback_data="reset")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select an option:",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
        
    except ValueError:
        await update.message.reply_text(
            "Invalid quantity. Please enter a valid number:"
        )
        return ENTERING_SELL_QUANTITY

async def reset_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset user's portfolio"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    USERS[user_id] = {
        "holdings": {},
        "sui_balance": 1000.0,
    }
    
    await query.edit_message_text(
        "Portfolio has been reset. You now have 1000 SUI to start trading again."
    )
    
    # Show main menu
    keyboard = [
        [
            InlineKeyboardButton("📈 View Tokens", callback_data="view_tokens"),
            InlineKeyboardButton("💰 My Portfolio", callback_data="portfolio"),
        ],
        [
            InlineKeyboardButton("💸 Buy", callback_data="buy"),
            InlineKeyboardButton("🧾 Sell", callback_data="sell"),
        ],
        [InlineKeyboardButton("🔄 Reset Portfolio", callback_data="reset")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Select an option:",
        reply_markup=reply_markup
    )
    return SELECTING_ACTION

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    msg = (
        f"<b>💰 Your Balance</b>\n\n"
        f"SUI: <code>{user_data['sui_balance']:.2f}</code>\n"
        f"Referral Bonus: <code>{user_data['referral_bonus']:.2f}</code>\n"
    )
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

async def show_pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    total_value = get_portfolio_value(user_id)
    total_pnl = get_unrealized_pnl(user_id)
    pnl_percent = (total_pnl / total_value * 100) if total_value > 0 else 0
    emoji = "🟢" if pnl_percent >= 0 else "🔴"
    msg = (
        f"<b>📈 Portfolio PnL</b>\n\n"
        f"{emoji} Unrealized PnL: <code>{total_pnl:.2f} SUI</code> ({pnl_percent:+.2f}%)\n"
    )
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

async def copy_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔁 <b>Copy Trade</b>\n\nThis feature is coming soon!", parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

async def wallet_pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔍 <b>Check Wallet PnL</b>\n\nThis feature is coming soon!", parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

async def invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👥 <b>Invite Friends</b>\n\nThis feature is coming soon!", parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    welcome_msg, reply_markup = format_main_menu(user_id)
    await query.edit_message_text(welcome_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

def main() -> None:
    """Start the bot"""
    # Get token from environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(view_tokens, pattern="^view_tokens$"),
                CallbackQueryHandler(show_portfolio, pattern="^portfolio$"),
                CallbackQueryHandler(start_buy, pattern="^buy$"),
                CallbackQueryHandler(start_sell, pattern="^sell$"),
                CallbackQueryHandler(reset_portfolio, pattern="^reset$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_tutorials, pattern="^tutorials$"),
                CallbackQueryHandler(show_tutorial, pattern="^tut_"),
                CallbackQueryHandler(show_balance, pattern="^balance$"),
                CallbackQueryHandler(show_pnl, pattern="^pnl$"),
                CallbackQueryHandler(copy_trade, pattern="^copy_trade$"),
                CallbackQueryHandler(wallet_pnl, pattern="^wallet_pnl$"),
                CallbackQueryHandler(invite_friends, pattern="^invite_friends$"),
            ],
            ENTERING_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_buy_token),
            ],
            ENTERING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_buy_amount),
            ],
            ENTERING_SELL_QUANTITY: [
                CallbackQueryHandler(process_sell_token, pattern="^sell_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_sell_quantity),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(conv_handler)
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main() 
    main() 