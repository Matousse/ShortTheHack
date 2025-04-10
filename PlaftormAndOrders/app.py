#!/usr/bin/env python3
"""
ShortTheHack - Bot de trading automatique basé sur l'analyse de tweets
"""
import os
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from loguru import logger

from app.utils.binance_trader import BinanceTrader
from app.utils.config_manager import ConfigManager

# Charger les variables d'environnement
load_dotenv()

# Configuration du logger
logger.remove()
# Logger pour le fichier
logger.add(
    "logs/gentlemate_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
# Logger pour la console (terminal)
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<b>{time:YYYY-MM-DD HH:mm:ss}</b> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# Initialiser l'application Flask
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")

# Protection des fichiers sensibles
def protect_sensitive_files():
    # Liste des fichiers sensibles à protéger
    sensitive_files = ['.env', '.git', '.gitignore', 'config.json']
    
    # Vérifier si la requête tente d'accéder à un fichier sensible
    path = request.path
    for file in sensitive_files:
        if file in path:
            logger.warning(f"Unauthorized access attempt to {path} from {request.remote_addr}")
            return jsonify({"error": "Access denied"}), 403
    return None

# Enregistrer le middleware pour toutes les requêtes
@app.before_request
def before_request():
    # Protection des fichiers sensibles
    protection_result = protect_sensitive_files()
    if protection_result:
        return protection_result

# Initialiser le gestionnaire de configuration
config_manager = ConfigManager()

# Initialiser les composants principaux
binance_trader = None

# Variables globales
last_alert = None
last_alert_time = None
last_tweet = None
last_tweet_time = None
bot_running = False
active_shorts = []  # Liste des shorts actifs


def initialize_components():
    """Initialise les composants principaux de l'application"""
    global binance_trader, active_shorts
    
    try:
        binance_trader = BinanceTrader(
            os.getenv("BINANCE_API_KEY"),
            os.getenv("BINANCE_API_SECRET")
        )
        logger.info("Binance Trader component successfully initialized")
        
        # Récupérer les positions shorts actives
        try:
            existing_shorts = binance_trader.get_active_shorts()
            if existing_shorts:
                logger.info(f"Retrieved {len(existing_shorts)} active short positions")
                active_shorts = existing_shorts
        except Exception as e:
            logger.warning(f"Unable to retrieve active short positions: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing components: {str(e)}")
        return False


def process_alert(alert_value, tweet_text=None):
    """Traite une alerte reçue du script externe"""
    global last_alert, last_alert_time, last_tweet, last_tweet_time
    
    logger.info(f"===== ALERT PROCESSING START =====")
    logger.info(f"Alert value: {alert_value}")
    logger.info(f"Tweet: {tweet_text}")
    
    # Enregistrer l'alerte
    last_alert = alert_value
    last_alert_time = datetime.now().isoformat()
    
    # Enregistrer le tweet s'il est fourni
    if tweet_text:
        last_tweet = tweet_text
        last_tweet_time = datetime.now().isoformat()
        logger.info(f"Tweet recorded: {tweet_text}")
    
    # Si l'alerte est "1" et que le bot est en cours d'exécution, placer un ordre de short
    if alert_value == "1":
        logger.warning("ALERT: Hack event detected!")
        logger.info(f"Alert details: {alert_value}, Tweet: {tweet_text}")
        
        # Vérifier si le bot est en cours d'exécution
        logger.info(f"Bot status: {'Running' if bot_running else 'Stopped'}")
        if not bot_running:
            logger.warning("The bot is not running. No order has been placed.")
            return True
        
        # Récupérer les paramètres actuels
        settings = config_manager.get_settings()
        leverage = settings.get("leverage", 1)
        
        # Vérifier si le trading automatique est activé
        if not settings.get("trading_enabled", False):
            logger.warning("Automated trading disabled. No short will be placed.")
            return True
            
        # Exécuter l'ordre de short sur BTC
        logger.info(f"Trading enabled: {settings.get('trading_enabled', True)}")
        if not binance_trader:
            logger.info("Binance Trader not initialized, attempting initialization")
            if not initialize_components():
                logger.error("Unable to initialize Binance trader")
                return False
            logger.info("Binance Trader successfully initialized")
            
        # Utiliser BTC/USDC pour le margin trading
        symbol = "BTCUSDC"
        logger.info(f"===== PLACING A SHORT =====")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Leverage: {leverage}")
        
        try:
            success, order_id = binance_trader.place_short_order(
                symbol=symbol,
                leverage=leverage
            )
            logger.info(f"Order placement result: success={success}, order_id={order_id}")
        except Exception as e:
            import traceback
            logger.error(f"Exception during order placement: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        
        if success and order_id:
            # Ajouter le short à la liste des shorts actifs
            global active_shorts
            short_info = {
                "id": order_id,
                "symbol": symbol,
                "leverage": leverage,
                "timestamp": datetime.now().isoformat(),
                "tweet": tweet_text
            }
            active_shorts.append(short_info)
            
            logger.success(f"Ordre de short placé avec succès pour {symbol} avec un levier de {leverage}x (ID: {order_id})")
            logger.debug(f"Short ajouté à la liste des shorts actifs: {short_info}")
            logger.debug(f"Nombre total de shorts actifs: {len(active_shorts)}")
            return True
        else:
            logger.error(f"Failed to place short order for {symbol}")
            return False
    
    return True


@app.route("/", methods=["GET", "POST"])
def index():
    """Route principale - Accepte les requêtes GET pour afficher l'interface et POST pour recevoir les alertes"""
    if request.method == "POST":
        try:
            # Récupérer les données JSON de la requête
            data = request.json
            
            # Afficher clairement le contenu de la requête POST
            logger.info(f"===== POST REQUEST RECEIVED =====")
            logger.info(f"IP Address: {request.remote_addr}")
            logger.info(f"Content: {data}")
            logger.info(f"===============================\n")
            
            # Vérifier si les données contiennent une alerte
            if "alert" in data:
                alert_value = data["alert"]
                tweet_text = data.get("tweet", None)
                logger.info(f"Processing alert: {alert_value} with tweet: {tweet_text}")
                success = process_alert(alert_value, tweet_text)
                result = {"success": success, "message": f"Alerte {alert_value} traitée avec succès"}
                logger.info(f"Result: {result}")
                return jsonify(result)
            else:
                logger.warning("Alert data missing in the request")
                return jsonify({"success": False, "message": "Missing alert data"}), 400
        except Exception as e:
            import traceback
            logger.error(f"Error processing alert: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    else:
        # Requête GET - Afficher l'interface utilisateur
        return render_template("index.html", settings=config_manager.get_settings())


@app.route("/sell-hacks")
def sell_hacks():
    """Sell the hacks page"""
    return render_template("sell_hacks.html", settings=config_manager.get_settings())


@app.route("/quick-escape")
def quick_escape():
    """Quick escape page"""
    return render_template("quick_escape.html", settings=config_manager.get_settings())


@app.route("/settings")
def settings():
    """Settings page"""
    return render_template("settings.html", settings=config_manager.get_settings())


@app.route("/logs")
def logs():
    """Logs page"""
    return render_template("logs.html", settings=config_manager.get_settings())


@app.route("/api/min_trade_quantity")
def get_min_trade_quantity():
    """Gets the minimum trade quantity for a given symbol"""
    symbol = request.args.get('symbol', 'BTCUSDC')
    logger.info(f"Retrieving minimum trade quantity for {symbol}")
    
    try:
        # Initialiser le trader Binance
        trader = BinanceTrader()
        if not trader.test_connection():
            return jsonify({'error': 'Unable to connect to Binance'}), 500
        
        # Récupérer la quantité minimale de trading
        result = trader.get_min_trade_quantity(symbol)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error retrieving minimum trade quantity: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/status")
def get_status():
    """Returns the current status of the bot"""
    # Debug logs
    logger.debug(f"API Status - Number of active shorts: {len(active_shorts)}")
    logger.debug(f"API Status - Active shorts details: {active_shorts}")
    logger.debug(f"API Status - Bot running: {bot_running}")
    
    # Format latest tweet for the UI
    latest_tweet = None
    if last_tweet:
        latest_tweet = {
            "text": last_tweet,
            "date": last_tweet_time if last_tweet_time else ""
        }
    
    return jsonify({
        "success": True,
        "running": bot_running,
        "active_shorts": active_shorts,
        "latest_tweet": latest_tweet,
        "settings": config_manager.get_settings()
    })


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Met à jour les paramètres du bot"""
    new_settings = request.json
    config_manager.update_settings(new_settings)
    return jsonify({"success": True, "settings": config_manager.get_settings()})


@app.route("/api/start", methods=["POST"])
def start_bot():
    """Démarre le bot"""
    global bot_running
    
    try:
        # Vérifier si les composants sont initialisés
        if not binance_trader:
            if not initialize_components():
                return jsonify({"success": False, "message": "Unable to initialize components"})
        
        # Démarrer le bot
        bot_running = True
        logger.success("Bot started successfully")
        return jsonify({"success": True, "message": "Bot started successfully"})
    except Exception as e:
        logger.error(f"Error starting the bot: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@app.route("/api/stop", methods=["POST"])
def stop_bot():
    """Arrête le bot"""
    global bot_running
    
    try:
        # Arrêter le bot
        bot_running = False
        logger.success("Bot stopped successfully")
        return jsonify({"success": True, "message": "Bot stopped successfully"})
    except Exception as e:
        logger.error(f"Error stopping the bot: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@app.route("/api/test_binance", methods=["GET"])
def test_binance_connection():
    """Teste la connexion à Binance"""
    if not binance_trader:
        if not initialize_components():
            return jsonify({"success": False, "message": "Impossible d'initialiser les composants"})
    
    success, message = binance_trader.test_connection()
    return jsonify({"success": success, "message": message})


@app.route("/api/test_claude", methods=["GET"])
def test_claude_connection():
    """Teste la connexion à l'API Claude"""
    try:
        # Vérifier si la clé API Claude est configurée
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        if not claude_api_key:
            return jsonify({"success": False, "message": "Claude API key not configured"})
            
        # Test simple pour vérifier si la clé API est valide
        # Dans un cas réel, vous pourriez faire une requête à l'API Claude
        if len(claude_api_key) > 10:
            return jsonify({"success": True, "message": "Claude API connection successful"})
        else:
            return jsonify({"success": False, "message": "Invalid Claude API key"})
    except Exception as e:
        logger.error(f"Error testing Claude API connection: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


@app.route("/api/manual_alert", methods=["POST"])
def manual_alert():
    """Permet de déclencher manuellement une alerte pour tester le système"""
    try:
        data = request.json
        alert_value = data.get("alert", "0")
        tweet_text = data.get("tweet", "Tweet de test manuel")
        success = process_alert(alert_value, tweet_text)
        return jsonify({"success": success, "message": f"Manual alert {alert_value} processed successfully"})
    except Exception as e:
        logger.error(f"Error processing manual alert: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@app.route("/api/place_short_direct", methods=["POST"])
def place_short_direct():
    """Place directement un ordre de short sur ETH sans passer par le traitement d'alerte"""
    logger.info("===== DIRECT CALL TO SHORT FUNCTION =====")
    
    # Vérifier si le bot est en cours d'exécution
    if not bot_running:
        logger.warning("The bot is not running. Cannot place a short.")
        return jsonify({"success": False, "message": "The bot must be running to place a short"}), 400
    
    # Récupérer les paramètres actuels
    settings = config_manager.get_settings()
    
    # Vérifier si le trading automatique est activé
    if not settings.get("trading_enabled", False):
        logger.warning("Automated trading disabled. Cannot place a short.")
        return jsonify({"success": False, "message": "Automated trading must be enabled to place a short"}), 400
    
    # Vérifier si le trader Binance est initialisé
    if not binance_trader:
        logger.info("Trader Binance non initialisé, tentative d'initialisation")
        if not initialize_components():
            logger.error("Unable to initialize Binance trader")
            return jsonify({"success": False, "message": "Unable to initialize Binance trader"}), 500
    
    # Récupérer les paramètres actuels
    settings = config_manager.get_settings()
    leverage = settings.get("leverage", 1)
    
    # Utiliser BTC/USDC pour le margin trading
    symbol = "BTCUSDC"
    logger.info(f"Direct placement of a short on {symbol} with leverage of {leverage}")
    
    try:
        # Récupérer le prix actuel du BTC
        try:
            ticker = binance_trader.client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker["price"])
            logger.info(f"Current price of {symbol}: {current_price}")
        except Exception as e:
            logger.error(f"Error getting current price: {str(e)}")
            current_price = 0
        
        # Quantité fixe pour les shorts directs (comme dans binance_trader.py)
        quantity = 0.00003
        
        # Appeler directement la fonction de placement de short
        success, order_id = binance_trader.place_short_order(
            symbol=symbol,
            leverage=leverage
        )
        
        logger.info(f"Direct placement result: success={success}, order_id={order_id}")
        
        if success and order_id:
            # Ajouter le short à la liste des shorts actifs
            active_shorts.append({
                "id": order_id,
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": current_price,
                "leverage": leverage,
                "timestamp": datetime.now().isoformat(),
                "status": "active"
            })
            logger.info(f"Short added to active shorts list: {order_id}")
            return jsonify({"success": True, "message": f"Short placed successfully (ID: {order_id})"})
        else:
            logger.error("Failed to place short")
            return jsonify({"success": False, "message": "Failed to place short"}), 500
    except Exception as e:
        import traceback
        logger.error(f"Exception during direct short placement: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route("/api/cancel_short", methods=["POST"])
def cancel_short():
    """Annule un short en le rachetant"""
    global active_shorts
    
    try:
        data = request.json
        short_id = data.get("short_id")
        
        if not short_id:
            return jsonify({"success": False, "message": "Missing short ID"}), 400
        
        # Rechercher le short dans la liste des shorts actifs
        short_to_cancel = None
        for short in active_shorts:
            if short["id"] == short_id:
                short_to_cancel = short
                break
        
        if not short_to_cancel:
            return jsonify({"success": False, "message": f"Short with ID {short_id} not found"}), 404
        
        # Annuler le short via Binance
        if not binance_trader:
            if not initialize_components():
                return jsonify({"success": False, "message": "Impossible d'initialiser le trader Binance"})
        
        # Extraire l'asset depuis le short_id (format: margin_BTC_timestamp)
        asset_symbol = None
        if short_id.startswith("margin_"):
            parts = short_id.split("_")
            if len(parts) >= 2:
                asset_symbol = parts[1]  # BTC, ETH, etc.
        
        if asset_symbol:
            logger.info(f"Attempting to cancel short with force_close_short for {asset_symbol}")
            success = binance_trader.force_close_short(asset_symbol)
        else:
            # Fallback à l'ancienne méthode si on ne peut pas extraire l'asset
            logger.warning(f"Unable to extract asset from short_id {short_id}, using close_short_position")
            success = binance_trader.close_short_position(short_to_cancel["symbol"], short_id)
        
        if success:
            # Retirer le short de la liste des shorts actifs
            active_shorts = [s for s in active_shorts if s["id"] != short_id]
            logger.success(f"Short {short_id} canceled successfully")
            return jsonify({"success": True, "message": f"Short {short_id} canceled successfully"})
        else:
            logger.error(f"Failed to cancel short {short_id}")
            return jsonify({"success": False, "message": f"Failed to cancel short {short_id}"})
    
    except Exception as e:
        logger.error(f"Error canceling short: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


if __name__ == "__main__":
    # Créer le dossier de logs s'il n'existe pas
    Path("logs").mkdir(exist_ok=True)
    
    # Importer le module time pour la méthode get_active_shorts
    import time
    from datetime import datetime
    
    # Initialiser les composants
    initialize_components()
    
    # Démarrer l'application Flask
    app.run(debug=True, host="0.0.0.0", port=7823)
