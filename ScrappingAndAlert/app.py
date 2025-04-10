#!/usr/bin/env python3
"""
GentleMate - Bot de trading automatique basé sur l'analyse de tweets
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

# Charger les variables d'environnement
load_dotenv()

# Configuration du logger
logger.remove()
logger.add(
    "logs/gentlemate_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# Initialiser l'application Flask
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")

# Initialiser le gestionnaire de configuration
config_manager = ConfigManager()

# Initialiser les composants principaux
twitter_scraper = None
sentiment_analyzer = None
binance_trader = None

# Variables globales
bot_running = False
bot_thread = None
last_tweet = None


def initialize_components():
    """Initialise les composants principaux de l'application"""
    global twitter_scraper, sentiment_analyzer, binance_trader
    
    try:
        twitter_scraper = TwitterScraper(os.getenv("TARGET_TWITTER_ACCOUNT"))
        sentiment_analyzer = SentimentAnalyzer(os.getenv("CLAUDE_API_KEY"))
        binance_trader = BinanceTrader(
            os.getenv("BINANCE_API_KEY"),
            os.getenv("BINANCE_API_SECRET")
        )
        logger.info("Tous les composants ont été initialisés avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des composants: {str(e)}")
        return False


def bot_loop():
    """Boucle principale du bot"""
    global bot_running, last_tweet
    
    logger.info("Bot démarré")
    
    while bot_running:
        try:
            # Récupérer les paramètres actuels
            settings = config_manager.get_settings()
            target_account = settings.get("target_account", os.getenv("TARGET_TWITTER_ACCOUNT"))
            target_coin = settings.get("target_coin", os.getenv("DEFAULT_COIN"))
            leverage = settings.get("leverage", 1)
            
            # Vérifier s'il y a un nouveau tweet
            new_tweet = twitter_scraper.get_latest_tweet(target_account)
            
            if new_tweet and (not last_tweet or new_tweet["id"] != last_tweet["id"]):
                logger.info(f"Nouveau tweet détecté: {new_tweet['text']}")
                
                # Analyser le sentiment du tweet
                is_hack = sentiment_analyzer.is_hack_event(new_tweet["text"])
                
                if is_hack:
                    logger.warning(f"ALERTE: Événement de hack détecté dans le tweet: {new_tweet['text']}")
                    
                    # Exécuter l'ordre de short sur Binance
                    if settings.get("trading_enabled", False):
                        success = binance_trader.place_short_order(
                            symbol=f"{target_coin}USDT",
                            leverage=leverage
                        )
                        
                        if success:
                            logger.success(f"Ordre de short placé avec succès pour {target_coin} avec un levier de {leverage}x")
                        else:
                            logger.error(f"Échec du placement de l'ordre de short pour {target_coin}")
                    else:
                        logger.info("Trading désactivé dans les paramètres. Aucun ordre n'a été placé.")
                else:
                    logger.info("Le tweet ne contient pas d'événement de hack")
                
                # Mettre à jour le dernier tweet
                last_tweet = new_tweet
                
                # Sauvegarder le dernier tweet
                with open("last_tweet.json", "w") as f:
                    json.dump(new_tweet, f)
            
            # Attendre l'intervalle configuré
            time.sleep(int(os.getenv("CHECK_INTERVAL", 3)))
            
        except Exception as e:
            logger.error(f"Erreur dans la boucle du bot: {str(e)}")
            time.sleep(5)  # Attendre un peu plus longtemps en cas d'erreur


def start_bot():
    """Démarre le bot dans un thread séparé"""
    global bot_running, bot_thread
    
    if not bot_running:
        # Vérifier si les composants sont initialisés
        if not twitter_scraper or not sentiment_analyzer or not binance_trader:
            if not initialize_components():
                return False
        
        # Charger le dernier tweet s'il existe
        global last_tweet
        if os.path.exists("last_tweet.json"):
            try:
                with open("last_tweet.json", "r") as f:
                    last_tweet = json.load(f)
                logger.info(f"Dernier tweet chargé: {last_tweet['text'][:50]}...")
            except Exception as e:
                logger.warning(f"Impossible de charger le dernier tweet: {str(e)}")
        
        # Démarrer le bot
        bot_running = True
        bot_thread = threading.Thread(target=bot_loop)
        bot_thread.daemon = True
        bot_thread.start()
        logger.info("Bot démarré avec succès")
        return True
    
    return False


def stop_bot():
    """Arrête le bot"""
    global bot_running
    
    if bot_running:
        bot_running = False
        logger.info("Bot arrêté")
        return True
    
    return False


@app.route("/")
def index():
    """Route principale"""
    return render_template("index.html", settings=config_manager.get_settings())


@app.route("/api/status")
def get_status():
    """Retourne l'état actuel du bot"""
    return jsonify({
        "running": bot_running,
        "last_tweet": last_tweet,
        "settings": config_manager.get_settings()
    })


@app.route("/api/start", methods=["POST"])
def api_start_bot():
    """Démarre le bot"""
    success = start_bot()
    return jsonify({"success": success, "running": bot_running})


@app.route("/api/stop", methods=["POST"])
def api_stop_bot():
    """Arrête le bot"""
    success = stop_bot()
    return jsonify({"success": success, "running": bot_running})


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Met à jour les paramètres du bot"""
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
    # Créer le dossier de logs s'il n'existe pas
    Path("logs").mkdir(exist_ok=True)
    
    # Initialiser les composants
    initialize_components()
    
    # Démarrer l'application Flask
    app.run(debug=True, host="0.0.0.0", port=5000)
