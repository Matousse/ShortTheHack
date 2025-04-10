#!/usr/bin/env python3
"""
GentleMate - Automated trading bot based on tweet analysis
"""
import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from loguru import logger

from app.utils.twitter_scraper import TwitterScraper
from app.utils.sentiment_analyzer import SentimentAnalyzer
from app.utils.binance_trader import BinanceTrader
from app.utils.config_manager import ConfigManager

# Load environment variables
load_dotenv()

# Logger configuration
logger.remove()
logger.add(
    "logs/gentlemate_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# Initialize Flask application
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")

# Initialize configuration manager
config_manager = ConfigManager()

# Initialize main components
twitter_scraper = None
sentiment_analyzer = None
binance_trader = None

# Global variables
bot_running = False
bot_thread = None
last_tweet = None


def initialize_components():
    """Initialize the main components of the application"""
    global twitter_scraper, sentiment_analyzer, binance_trader
    
    try:
        twitter_scraper = TwitterScraper(os.getenv("TARGET_TWITTER_ACCOUNT"))
        sentiment_analyzer = SentimentAnalyzer(os.getenv("CLAUDE_API_KEY"))
        binance_trader = BinanceTrader(
            os.getenv("BINANCE_API_KEY"),
            os.getenv("BINANCE_API_SECRET")
        )
        logger.info("All components have been successfully initialized")
        return True
    except Exception as e:
        logger.error(f"Error during component initialization: {str(e)}")
        return False


def bot_loop():
    """Main bot loop"""
    global bot_running, last_tweet
    
    logger.info("Bot started")
    
    while bot_running:
        try:
            # Get current parameters
            settings = config_manager.get_settings()
            target_account = settings.get("target_account", os.getenv("TARGET_TWITTER_ACCOUNT"))
            target_coin = settings.get("target_coin", os.getenv("DEFAULT_COIN"))
            leverage = settings.get("leverage", 1)
            
            # Check if there's a new tweet
            new_tweet = twitter_scraper.get_latest_tweet(target_account)
            
            if new_tweet and (not last_tweet or new_tweet["id"] != last_tweet["id"]):
                logger.info(f"New tweet detected: {new_tweet['text']}")
                
                # Analyze tweet sentiment
                is_hack = sentiment_analyzer.is_hack_event(new_tweet["text"])
                
                if is_hack:
                    logger.warning(f"ALERT: Hack event detected in tweet: {new_tweet['text']}")
                    
                    # Execute short order on Binance
                    if settings.get("trading_enabled", False):
                        success = binance_trader.place_short_order(
                            symbol=f"{target_coin}USDT",
                            leverage=leverage
                        )
                        
                        if success:
                            logger.success(f"Short order successfully placed for {target_coin} with leverage of {leverage}x")
                        else:
                            logger.error(f"Failed to place short order for {target_coin}")
                    else:
                        logger.info("Trading disabled in settings. No order has been placed.")
                else:
                    logger.info("The tweet does not contain a hack event")
                
                # Update the latest tweet
                last_tweet = new_tweet
                
                # Save the latest tweet
                with open("last_tweet.json", "w") as f:
                    json.dump(new_tweet, f)
            
            # Wait for the configured interval
            time.sleep(int(os.getenv("CHECK_INTERVAL", 3)))
            
        except Exception as e:
            logger.error(f"Error in bot loop: {str(e)}")
            time.sleep(5)  # Wait a bit longer in case of error


def start_bot():
    """Start the bot in a separate thread"""
    global bot_running, bot_thread
    
    if not bot_running:
        # Check if components are initialized
        if not twitter_scraper or not sentiment_analyzer or not binance_trader:
            if not initialize_components():
                return False
        
        # Load the last tweet if it exists
        global last_tweet
        if os.path.exists("last_tweet.json"):
            try:
                with open("last_tweet.json", "r") as f:
                    last_tweet = json.load(f)
                logger.info(f"Last tweet loaded: {last_tweet['text'][:50]}...")
            except Exception as e:
                logger.warning(f"Unable to load the last tweet: {str(e)}")
        
        # Start the bot
        bot_running = True
        bot_thread = threading.Thread(target=bot_loop)
        bot_thread.daemon = True
        bot_thread.start()
        logger.info("Bot successfully started")
        return True
    
    return False


def stop_bot():
    """Stop the bot"""
    global bot_running
    
    if bot_running:
        bot_running = False
        logger.info("Bot stopped")
        return True
    
    return False


@app.route("/")
def index():
    """Main route"""
    return render_template("index.html", settings=config_manager.get_settings())


@app.route("/api/status")
def get_status():
    """Return the current status of the bot"""
    return jsonify({
        "running": bot_running,
        "last_tweet": last_tweet,
        "settings": config_manager.get_settings()
    })


@app.route("/api/start", methods=["POST"])
def api_start_bot():
    """Start the bot"""
    success = start_bot()
    return jsonify({"success": success, "running": bot_running})


@app.route("/api/stop", methods=["POST"])
def api_stop_bot():
    """Stop the bot"""
    success = stop_bot()
    return jsonify({"success": success, "running": bot_running})


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update the bot settings"""
    new_settings = request.json
    config_manager.update_settings(new_settings)
    return jsonify({"success": True, "settings": config_manager.get_settings()})


@app.route("/api/test_binance", methods=["GET"])
def test_binance_connection():
    """Teste la connexion à Binance"""
    if not binance_trader:
        if not initialize_components():
            return jsonify({"success": False, "message": "Impossible d'initialiser les composants"})
    
    success, message = binance_trader.test_connection()
    return jsonify({"success": success, "message": message})


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Initialiser les composants
    initialize_components()
    
    # Démarrer l'application Flask
    app.run(debug=True, host="0.0.0.0", port=5000)
