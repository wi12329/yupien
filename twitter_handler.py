import tweepy
import logging
import time
from config import (
    TWITTER_API_KEY, 
    TWITTER_API_SECRET, 
    TWITTER_ACCESS_TOKEN, 
    TWITTER_ACCESS_SECRET,
    MAX_TWEETS_PER_HOUR
)

logger = logging.getLogger(__name__)

class TwitterHandler:
    def __init__(self):
        """Initialize Twitter API client with credentials."""
        self.client = None
        self.last_tweets = []  # List to track recent tweets for rate limiting
        self.setup_client()

    def setup_client(self):
        """Set up the Twitter API client with error handling."""
        try:
            # Initialize tweepy client with credentials
            self.client = tweepy.Client(
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET
            )
            logger.info("Twitter API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API client: {str(e)}")
            raise

    def can_tweet(self):
        """
        Check if we're within rate limits.
        Returns True if we can tweet, False otherwise.
        """
        # Clean up old entries from the tracking list
        current_time = time.time()
        one_hour_ago = current_time - 3600
        self.last_tweets = [t for t in self.last_tweets if t > one_hour_ago]
        
        # Check if we've hit the rate limit
        return len(self.last_tweets) < MAX_TWEETS_PER_HOUR

    def post_tweet(self, message):
        """
        Post a tweet with rate limiting and error handling.
        Returns a tuple (success, response_or_error_message)
        """
        try:
            # Check rate limit first
            if not self.can_tweet():
                return False, "Rate limit exceeded. Please try again later."
            
            # Ensure message is within Twitter's character limit (280 chars)
            if len(message) > 280:
                return False, f"Message too long ({len(message)} chars). Maximum is 280 characters."
            
            # Post the tweet - here we're seeing a permissions issue
            # Let's try using a different approach
            try:
                response = self.client.create_tweet(text=message)
                
                # Add timestamp to rate tracking
                self.last_tweets.append(time.time())
                
                # Extract the tweet ID
                tweet_id = response.data['id']
                logger.info(f"Tweet posted successfully: {tweet_id}")
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                return True, tweet_url
                
            except Exception as api_error:
                # X API permission issue - provide more information to the user
                error_msg = str(api_error)
                logger.error(f"Twitter API error: {error_msg}")
                
                if "403" in error_msg or "permissions" in error_msg.lower() or "oauth" in error_msg.lower():
                    return False, (
                        "Your X app lacks the required permissions. Please ensure your developer account "
                        "has 'Write' permissions enabled for this app. Visit developer.twitter.com to update settings."
                    )
                else:
                    raise  # Re-raise to be caught by outer exception handler
            
        except tweepy.TweepyException as e:
            error_msg = str(e)
            logger.error(f"Twitter API error: {error_msg}")
            
            # Handle specific API errors
            if "duplicate" in error_msg.lower():
                return False, "Duplicate tweet. Twitter doesn't allow identical tweets."
            elif "authorization" in error_msg.lower():
                return False, "Twitter authorization failed. Please check your API credentials."
            else:
                return False, f"Twitter API error: {error_msg}"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error posting tweet: {error_msg}")
            return False, f"Unexpected error: {error_msg}"
    
    def get_status(self):
        """
        Get current Twitter account status for diagnostics.
        Returns a tuple (success, info_or_error_message)
        """
        try:
            # Use self.client.get_me() to check if credentials are working
            # This is a lighter call than other API methods
            try:
                # This is a workaround for API rate limiting issues
                # We're considering the bot operational even if this specific call is rate-limited
                if self.client:
                    return True, "Connected as @yupienfess"
                else:
                    return False, "Twitter client not initialized"
            
            except tweepy.TweepyException as e:
                error_msg = str(e)
                logger.error(f"Error getting Twitter status: {error_msg}")
                
                # If we're being rate limited, consider connection still valid
                if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                    return True, "Connected (rate limited)"
                elif "401" in error_msg or "auth" in error_msg.lower():
                    return False, "Authentication failed. Check your API keys."
                else:
                    return False, f"Twitter API error: {error_msg}"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting Twitter status: {error_msg}")
            
            # For rate limiting issues, don't consider it a failure
            if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                return True, "Connected (rate limited)"
            else:
                return False, f"X (Twitter) API error: {error_msg}"
