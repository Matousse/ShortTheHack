"""
Module for analyzing tweet sentiment using the Claude API
"""
import os
import json
from anthropic import Anthropic
from loguru import logger

class SentimentAnalyzer:
    """Class for analyzing tweet sentiment using the Claude API"""
    
    def __init__(self, api_key=None):
        """Initialize the sentiment analyzer"""
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            logger.warning("Claude API key not found in environment variables")
        
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialize the Claude client"""
        try:
            client = Anthropic(api_key=self.api_key)
            logger.info("Claude client successfully initialized")
            return client
        except Exception as e:
            logger.error(f"Error initializing Claude client: {str(e)}")
            return None
    
    def is_hack_event(self, text):
        """
        Determines if a text contains information about a hack event
        
        Args:
            text (str): The text to analyze
            
        Returns:
            bool: True if the text contains information about a hack, False otherwise
        """
        try:
            if not self.client:
                logger.error("Claude client not initialized")
                return False
            
            # Build the prompt for Claude
            prompt = f"""
            Analyze the following tweet and determine if it contains the word "hack" AND if it suggests that a hack has occurred.
            
            Tweet: "{text}"
            
            Respond only with a JSON with a key "is_hack" that contains a boolean (true/false).
            Respond true only if the tweet contains the word "hack" AND suggests that a hack has actually occurred.
            """
            
            # Call the Claude API
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=100,
                temperature=0,
                system="You are an assistant that analyzes tweets to detect hack events. Respond only with a JSON with a key 'is_hack' that contains a boolean.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the response
            content = response.content[0].text
            
            # Try to parse the JSON response
            try:
                result = json.loads(content)
                is_hack = result.get("is_hack", False)
                logger.info(f"Tweet analysis: is_hack={is_hack}")
                return is_hack
            except json.JSONDecodeError:
                # If the response is not a valid JSON, check if it contains "true"
                logger.warning(f"Non-JSON Claude response: {content}")
                return "true" in content.lower()
            
        except Exception as e:
            logger.error(f"Error analyzing tweet: {str(e)}")
            return False
    
    def test_connection(self):
        """Test the connection to the Claude API"""
        try:
            if not self.client:
                return False, "Claude client not initialized"
            
            # Test the connection by sending a simple request
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Say hello"}
                ]
            )
            
            if response and response.content:
                return True, "Connection to Claude API successful"
            else:
                return False, "Unable to retrieve data from Claude API"
        except Exception as e:
            return False, f"Error testing connection to Claude API: {str(e)}"
