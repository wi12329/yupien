#!/usr/bin/env python3
"""
Simple script to test Telegram bot connection.
"""

import os
import sys
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from logger import setup_logger

# Set up logging
logger = setup_logger()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    logger.info(f"Received /start command from user {update.effective_user.id}")
    await update.message.reply_text("Bot is working! This is a test message.")

async def main():
    """Run the test bot."""
    # Get the token from environment
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set")
        return

    logger.info(f"Token is available (length: {len(token)})")
    
    try:
        # Create the Application
        logger.info("Creating Application...")
        application = Application.builder().token(token).build()
        
        # Add command handler
        logger.info("Adding command handler...")
        application.add_handler(CommandHandler("start", start_command))
        
        # Start the bot
        logger.info("Starting bot...")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting Telegram test script...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)