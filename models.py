import os
import time
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

class TweetQueue(db.Model):
    """
    Model to track tweet times and implement the 10-minute queue system.
    This prevents public abuse by limiting tweet frequency.
    """
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String(32), nullable=True)  # Twitter's tweet ID
    user_id = db.Column(db.String(32), nullable=False)  # Telegram user ID
    message = db.Column(db.Text, nullable=True)         # Tweet content
    image_path = db.Column(db.Text, nullable=True)      # Path to image file (if any)
    command_prefix = db.Column(db.String(16), nullable=True)  # The command prefix used
    telegram_file_id = db.Column(db.String(255), nullable=True)  # Telegram file ID for images
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(16), default="pending")  # pending, posting, posted, failed
    attempt_count = db.Column(db.Integer, default=0)      # Number of posting attempts
    last_attempt = db.Column(db.DateTime, nullable=True)  # Timestamp of last attempt
    error_message = db.Column(db.Text, nullable=True)     # Last error message

    @classmethod
    def get_last_tweet_time(cls):
        """Get the timestamp of the most recent successful tweet."""
        last_tweet = cls.query.filter_by(status="posted").order_by(cls.timestamp.desc()).first()
        if last_tweet:
            return last_tweet.timestamp
        return None
    
    @classmethod
    def can_tweet_now(cls):
        """
        Check if we can tweet now based on the 10-minute rule.
        Returns True if at least 10 minutes have passed since the last tweet.
        """
        last_time = cls.get_last_tweet_time()
        if not last_time:
            # No tweets yet, so we can tweet immediately
            return True
        
        # Check if 10 minutes have passed
        time_limit = datetime.utcnow() - timedelta(minutes=10)
        return last_time <= time_limit
    
    @classmethod
    def time_until_next_available(cls):
        """
        Get the time remaining until the next tweet is allowed.
        Returns time in seconds, or 0 if tweeting is allowed now.
        """
        last_time = cls.get_last_tweet_time()
        if not last_time:
            return 0
        
        # Calculate next available time (10 minutes after last tweet)
        next_available = last_time + timedelta(minutes=10)
        now = datetime.utcnow()
        
        if now >= next_available:
            return 0
        
        # Return seconds until next available time
        return (next_available - now).total_seconds()
    
    @classmethod
    def add_to_queue(cls, user_id, message, image_path=None, command_prefix=None, telegram_file_id=None):
        """
        Add a new tweet to the queue.
        Returns the created queue entry.
        """
        entry = cls(
            user_id=user_id, 
            message=message, 
            status="pending", 
            image_path=image_path,
            command_prefix=command_prefix,
            telegram_file_id=telegram_file_id
        )
        db.session.add(entry)
        db.session.commit()
        return entry
    
    @classmethod
    def mark_as_posting(cls, entry_id):
        """
        Mark a queue entry as currently being posted.
        """
        entry = cls.query.get(entry_id)
        if entry:
            entry.status = "posting"
            entry.attempt_count += 1
            entry.last_attempt = datetime.utcnow()
            db.session.commit()
            return True
        return False
    
    @classmethod
    def mark_as_posted(cls, entry_id, tweet_id):
        """
        Mark a queue entry as successfully posted.
        """
        entry = cls.query.get(entry_id)
        if entry:
            entry.status = "posted"
            entry.tweet_id = tweet_id
            entry.timestamp = datetime.utcnow()  # Update timestamp to actual posting time
            db.session.commit()
            return True
        return False
    
    @classmethod
    def mark_as_failed(cls, entry_id, error=None):
        """
        Mark a queue entry as failed.
        """
        entry = cls.query.get(entry_id)
        if entry:
            entry.status = "failed"
            entry.error_message = error
            db.session.commit()
            return True
        return False
        
    @classmethod
    def get_pending_tweets(cls, max_age_hours=24):
        """
        Get all pending tweets that haven't been processed yet.
        Only returns tweets that are less than max_age_hours old.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        return cls.query.filter(
            cls.status == "pending",
            cls.timestamp >= cutoff_time
        ).order_by(cls.timestamp.asc()).all()
    
    @classmethod
    def get_stalled_tweets(cls, minutes_since_attempt=15):
        """
        Get tweets that got stuck in 'posting' status.
        Returns tweets that have been in 'posting' status for more than minutes_since_attempt.
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_since_attempt)
        return cls.query.filter(
            cls.status == "posting",
            cls.last_attempt <= cutoff_time
        ).order_by(cls.timestamp.asc()).all()
        
    @classmethod
    def format_wait_time(cls, seconds):
        """
        Format wait time in seconds to a human-readable string.
        Returns a string like "5m 30s" or "30s"
        """
        minutes = int(seconds / 60)
        remaining_seconds = int(seconds % 60)
        
        if minutes > 0:
            return f"{minutes}m {remaining_seconds}s"
        else:
            return f"{remaining_seconds}s"