import os
import asyncio
import logging
from bot import TelegramTwitterBot
from logger import logger

async def main():
    """Main entry point for the Telegram-X integration bot."""
    logger.info("Initializing Telegram-X integration bot...")
    
    try:
        # Create and start the bot with retry logic
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                bot = TelegramTwitterBot()
                await bot.start()
                break  # If successful, exit the retry loop
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                logger.error(f"Error starting bot (attempt {retry_count}/{max_retries}): {error_msg}")
                
                if retry_count >= max_retries:
                    logger.critical(f"Failed to start bot after {max_retries} attempts. Last error: {error_msg}")
                    raise
                
                # Wait before retrying
                logger.info(f"Waiting 5 seconds before retry...")
                await asyncio.sleep(5)
    except Exception as e:
        logger.critical(f"Fatal error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        raise