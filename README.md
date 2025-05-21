# SUI Memecoin Trading Bot

A Telegram bot that simulates paper trading of SUI memecoins. This bot allows users to practice trading SUI memecoins without using real money.

## Features

- 📈 View available SUI memecoins and their prices
- 💰 Track your portfolio and unrealized PnL
- 💸 Buy and sell memecoins using SUI
- 🧾 Simulated trading with realistic price fluctuations
- 🔄 Reset portfolio to start fresh

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd sui-trading-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your Telegram bot token:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

To get a Telegram bot token:
1. Open Telegram and search for "@BotFather"
2. Start a chat and send `/newbot`
3. Follow the instructions to create your bot
4. Copy the API token provided by BotFather

## Running the Bot

1. Make sure you have set up your `.env` file with the bot token
2. Run the bot:
```bash
python sui_trading_bot.py
```

## Usage

1. Start a chat with your bot on Telegram
2. Send `/start` to begin
3. Use the inline buttons to:
   - View available tokens
   - Check your portfolio
   - Buy tokens
   - Sell tokens
   - Reset your portfolio

## Notes

- This is a paper trading bot - no real transactions are made
- All data is stored in memory and will be reset when the bot restarts
- Each user starts with 1000 SUI
- Token prices are simulated with random fluctuations
- The bot supports multiple users independently

## Disclaimer

This bot is for educational and entertainment purposes only. It does not make real trades or interact with the SUI blockchain. All trading is simulated. 