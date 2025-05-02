#!/usr/bin/env python
"""
Standalone script to run just the Telegram-X integration bot.
This avoids conflicts with the Flask web server.
"""

import asyncio
import os
import sys
import time
import signal
import logging
from bot import TelegramTwitterBot
from logger import setup_logger
from status_manager import update_status

# Set up logger
logger = setup_logger()

async def main():
    """Run the Telegram-X integration bot."""
    # Display a clear startup message
    print("\n" + "="*70)
    print("  STANDALONE TELEGRAM-X BOT  ".center(70))
    print("="*70 + "\n")
    
    logger.info("Starting standalone Telegram-X bot...")
    
    try:
        # Update status to show we're starting
        update_status(
            running=True,
            telegram_status="Initializing...",
            twitter_status="Connecting..."
        )
        
        # Create and start the bot
        logger.info("Creating TelegramTwitterBot instance...")
        try:
            bot = TelegramTwitterBot()
            logger.info("Successfully created TelegramTwitterBot instance")
        except Exception as e:
            logger.critical(f"Failed to create TelegramTwitterBot instance: {e}", exc_info=True)
            update_status(
                running=False,
                telegram_status="Failed to initialize",
                twitter_status="Failed to initialize",
                error=f"Bot creation error: {e}"
            )
            raise
        
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(sig, loop, bot)))
        
        # Start the bot
        logger.info("Starting bot services...")
        update_status(
            running=True,
            telegram_status="Starting...",
            twitter_status="Connecting..."
        )
        
        try:
            # Print information about the token for debugging
            from config import TELEGRAM_TOKEN
            logger.info(f"Telegram token available: {bool(TELEGRAM_TOKEN)}, Length: {len(TELEGRAM_TOKEN)}")
            
            # Start the bot with detailed error logging
            await bot.start()
        except Exception as e:
            logger.critical(f"Failed to start bot: {e}", exc_info=True)
            update_status(
                running=False,
                telegram_status="Failed to start",
                twitter_status="Failed to start",
                error=f"Bot start error: {e}"
            )
            raise
        
        # Update status to show we're running
        update_status(
            running=True,
            telegram_status="Connected",
            twitter_status="Ready to tweet"
        )
        
        # Keep the script running
        while True:
            # Periodically update the status to show we're still alive
            update_status(running=True)
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error in bot: {str(e)}", exc_info=True)
        sys.exit(1)

async def shutdown(sig, loop, bot):
    """Handle graceful shutdown on signals."""
    logger.info(f"Received exit signal {sig.name}...")
    logger.info("Shutting down bot...")
    
    # Update status to show we're shutting down
    update_status(
        running=False,
        telegram_status="Shutting down...",
        twitter_status="Disconnecting..."
    )
    
    try:
        await bot.stop()
    except Exception as e:
        logger.error(f"Error during bot shutdown: {e}")
        update_status(error=f"Error during shutdown: {e}")
    
    # Final status update
    update_status(
        running=False,
        telegram_status="Offline",
        twitter_status="Disconnected"
    )
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass