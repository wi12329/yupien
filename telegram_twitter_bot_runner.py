#!/usr/bin/env python
"""
Standalone script for running the Telegram-X bot without any Flask components.
This script is designed to be run by the run_telegram_twitter_bot workflow.
"""

import asyncio
import signal
import sys
import os
import threading
from bot import TelegramTwitterBot
from logger import logger
from keep_alive import run_keep_alive

# Global variable to hold our bot instance
bot_instance = None

async def shutdown(signal, loop):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received exit signal {signal.name}...")
    
    if bot_instance:
        logger.info("Stopping bot...")
        try:
            await bot_instance.stop()
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

def handle_exception(loop, context):
    """Handle exceptions that escape the async tasks."""
    msg = context.get("exception", context["message"])
    logger.error(f"Unhandled exception: {msg}")
    logger.info("Shutting down...")
    asyncio.create_task(shutdown(signal.SIGTERM, loop))

async def main():
    """Main entry point for the Telegram-X integration bot."""
    global bot_instance
    
    logger.info("Starting Telegram-X bot in standalone mode - completely separate from web UI")
    
    # Get event loop
    loop = asyncio.get_running_loop()
    
    # Set up signal handlers for graceful shutdown
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )
    
    # Set up exception handler
    loop.set_exception_handler(handle_exception)
    
    try:
        # Initialize and start the bot
        logger.info("Initializing Telegram-X integration bot...")
        bot_instance = TelegramTwitterBot()
        await bot_instance.start()
        
        # This point should only be reached when the bot is stopped through a signal,
        # as bot.start() is designed to run indefinitely
        logger.info("Bot has been stopped gracefully")
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error in bot: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Print a clear message to indicate this standalone runner is starting
    print("\n" + "="*50)
    print(" STARTING TELEGRAM-X BOT (STANDALONE RUNNER)")
    print("="*50 + "\n")
    
    # Start the keep-alive server to prevent Replit from sleeping
    try:
        logger.info("Starting keep-alive server on port 8080")
        run_keep_alive()  
        logger.info("Keep-alive server started successfully")
    except Exception as e:
        logger.error(f"Error starting keep-alive server: {e}")
    
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot interrupted by user")
    except Exception as e:
        print(f"\nUnhandled exception: {e}")
        sys.exit(1)