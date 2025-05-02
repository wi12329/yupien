#!/usr/bin/env python
"""
Simple script that just runs the bot without any web interface.
This is designed to be called by the bot_starter.sh script.
"""

import os
import sys
import asyncio
import traceback
from bot import TelegramTwitterBot
from logger import logger

async def run_bot():
    """Run the Telegram-X bot without any web interface."""
    try:
        logger.info("Starting Telegram-X bot without web interface...")
        bot = TelegramTwitterBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error in bot: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Display a clear startup message
    print("\n" + "="*70)
    print("  TELEGRAM-X BOT STANDALONE RUNNER (NO WEB INTERFACE)  ".center(70))
    print("="*70 + "\n")
    
    # Run the async function
    asyncio.run(run_bot())