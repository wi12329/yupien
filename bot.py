import logging
import asyncio
from telegram_handler import TelegramHandler
from twitter_handler import TwitterHandler
from logger import logger

class TelegramTwitterBot:
    """Main bot class to manage integration between Telegram and X (Twitter)."""
    
    def __init__(self):
        """Initialize the bot with required handlers."""
        self.twitter_handler = TwitterHandler()
        self.telegram_handler = TelegramHandler(self.twitter_handler)
        
    async def start(self):
        """Start the bot services."""
        logger.info("Starting Telegram-X Integration Bot...")
        
        try:
            # Setup the telegram handlers
            self.telegram_handler.setup_handlers()
            
            # Start the Telegram bot - this will block until the application is stopped
            # No need for a custom sleep loop as run_polling handles this
            logger.info("Bot is now running...")
            await self.telegram_handler.run()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by keyboard interrupt")
            await self.stop()
        except Exception as e:
            logger.critical(f"Fatal error: {str(e)}", exc_info=True)
            await self.stop()
            raise
            
    async def stop(self):
        """Stop the bot services gracefully."""
        logger.info("Stopping Telegram-X Integration Bot...")
        try:
            await self.telegram_handler.stop()
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            # Continue with shutdown even if there's an error
