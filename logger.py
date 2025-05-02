import logging
from logging.handlers import RotatingFileHandler
import os
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE

def setup_logger():
    """
    Set up a logger with rotating file handler to avoid huge log files.
    Returns the configured logger.
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up logging to file with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Set up console logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log startup information
    root_logger.info("Telegram-X integration bot logger initialized")
    
    return root_logger

# Create a logger instance for import
logger = setup_logger()
