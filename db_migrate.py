"""
Database migration script for the Telegram-X bot.
This script updates the database schema to add new columns for the queue system.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment variables")
    sys.exit(1)

def execute_sql(sql, params=None):
    """Execute SQL with error handling."""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(sql), params)
            else:
                result = conn.execute(text(sql))
            conn.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"SQL Error: {e}")
        return False

def check_column_exists(table, column):
    """Check if a column exists in a table."""
    sql = """
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = :table_name AND column_name = :column_name
    )
    """
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), {"table_name": table, "column_name": column})
            exists = result.scalar()
        return exists
    except SQLAlchemyError as e:
        logger.error(f"Error checking if column exists: {e}")
        return False

def migrate():
    """Run the migration to update the database schema."""
    logger.info("Starting database migration...")
    
    # Add image_path column if it doesn't exist
    if not check_column_exists("tweet_queue", "image_path"):
        logger.info("Adding image_path column...")
        if not execute_sql("ALTER TABLE tweet_queue ADD COLUMN image_path TEXT"):
            return False
    
    # Add command_prefix column if it doesn't exist
    if not check_column_exists("tweet_queue", "command_prefix"):
        logger.info("Adding command_prefix column...")
        if not execute_sql("ALTER TABLE tweet_queue ADD COLUMN command_prefix VARCHAR(16)"):
            return False
    
    # Add telegram_file_id column if it doesn't exist
    if not check_column_exists("tweet_queue", "telegram_file_id"):
        logger.info("Adding telegram_file_id column...")
        if not execute_sql("ALTER TABLE tweet_queue ADD COLUMN telegram_file_id VARCHAR(255)"):
            return False
    
    # Add attempt_count column if it doesn't exist
    if not check_column_exists("tweet_queue", "attempt_count"):
        logger.info("Adding attempt_count column...")
        if not execute_sql("ALTER TABLE tweet_queue ADD COLUMN attempt_count INTEGER DEFAULT 0"):
            return False
    
    # Add last_attempt column if it doesn't exist
    if not check_column_exists("tweet_queue", "last_attempt"):
        logger.info("Adding last_attempt column...")
        if not execute_sql("ALTER TABLE tweet_queue ADD COLUMN last_attempt TIMESTAMP"):
            return False
    
    # Add error_message column if it doesn't exist
    if not check_column_exists("tweet_queue", "error_message"):
        logger.info("Adding error_message column...")
        if not execute_sql("ALTER TABLE tweet_queue ADD COLUMN error_message TEXT"):
            return False
    
    logger.info("Migration completed successfully")
    return True

if __name__ == "__main__":
    if migrate():
        logger.info("Database migration completed successfully")
    else:
        logger.error("Database migration failed")
        sys.exit(1)