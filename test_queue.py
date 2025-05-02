"""
Test script for the tweet queue processor.
This script simulates adding a tweet to the queue and then processing it.
"""

import os
import sys
import logging
from flask import Flask
from models import db, TweetQueue
from queue_processor import process_queue

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestQueue")

def main():
    """Test the queue processor."""
    # Create a test Flask app to set up database connection
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        # Check if we already have tweets in the queue
        pending_tweets = TweetQueue.query.filter_by(status="pending").all()
        if pending_tweets:
            logger.info(f"Found {len(pending_tweets)} pending tweets in the queue")
        else:
            logger.info("No pending tweets found, let's add a test tweet")
            
            # Add a test tweet to the queue
            test_tweet = TweetQueue.add_to_queue(
                user_id="12345",
                message="This is a test tweet from the queue processor [Test Tweet ID: 12345]",
                command_prefix="-yupi"
            )
            logger.info(f"Added test tweet to queue with ID {test_tweet.id}")
        
        # Process the queue
        logger.info("Processing the queue...")
        process_queue()
        logger.info("Queue processing completed")
        
        # Check the status of tweets
        pending = TweetQueue.query.filter_by(status="pending").count()
        posting = TweetQueue.query.filter_by(status="posting").count()
        posted = TweetQueue.query.filter_by(status="posted").count()
        failed = TweetQueue.query.filter_by(status="failed").count()
        
        logger.info("Queue status:")
        logger.info(f"- Pending: {pending}")
        logger.info(f"- Posting: {posting}")
        logger.info(f"- Posted: {posted}")
        logger.info(f"- Failed: {failed}")
        
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)