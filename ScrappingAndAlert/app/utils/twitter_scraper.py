"""
Module to retrieve tweets from a specific Twitter account
"""
import os
import tweepy
from loguru import logger

class TwitterScraper:
    """Class for scraping tweets from a specific Twitter account"""
    
    def __init__(self, target_account=None):
        """Initialize the Twitter scraper"""
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            logger.warning("Twitter authentication token not found in environment variables")
        
        self.target_account = target_account or os.getenv("TARGET_TWITTER_ACCOUNT", "DamienMATHIS4")
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialize the Twitter client"""
        try:
            client = tweepy.Client(bearer_token=self.bearer_token)
            logger.info("Twitter client successfully initialized")
            return client
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {str(e)}")
            return None
    
    def get_latest_tweet(self, username=None):
        """Retrieve the latest tweet from a Twitter account"""
        target = username or self.target_account
        
        try:
            if not self.client:
                logger.error("Twitter client not initialized")
                return None
            
            # Get user information
            user = self.client.get_user(username=target)
            if not user or not user.data:
                logger.error(f"Twitter user {target} not found")
                return None
            
            user_id = user.data.id
            
            # Get user tweets (max 10, we'll take the first one)
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=10,
                tweet_fields=["created_at", "text", "public_metrics"]
            )
            
            if not tweets or not tweets.data:
                logger.warning(f"No tweets found for user {target}")
                return None
            
            # Take the most recent tweet
            latest_tweet = tweets.data[0]
            
            # Format tweet data
            tweet_data = {
                "id": latest_tweet.id,
                "text": latest_tweet.text,
                "created_at": latest_tweet.created_at.isoformat(),
                "metrics": latest_tweet.public_metrics if hasattr(latest_tweet, "public_metrics") else {}
            }
            
            logger.info(f"Tweet retrieved for {target}: {tweet_data['text'][:50]}...")
            return tweet_data
            
        except Exception as e:
            logger.error(f"Error retrieving tweet for {target}: {str(e)}")
            return None
    
    def test_connection(self):
        """Test the connection to the Twitter API"""
        try:
            if not self.client:
                return False, "Twitter client not initialized"
            
            # Test the connection by retrieving a random user (Twitter)
            user = self.client.get_user(username="Twitter")
            if user and user.data:
                return True, "Connection to Twitter API successful"
            else:
                return False, "Unable to retrieve data from Twitter API"
        except Exception as e:
            return False, f"Error testing connection to Twitter API: {str(e)}"
