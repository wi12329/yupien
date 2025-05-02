#!/bin/bash

# This script is a wrapper to run just the bot without a web interface
# It will be called by the run_telegram_twitter_bot workflow

echo "Starting Telegram-X integration bot (no web interface)..."
# Run the bot-only script - this will just start the bot without any web interface
python start_bot_only.py