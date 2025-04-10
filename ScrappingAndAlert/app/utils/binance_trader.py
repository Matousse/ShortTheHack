"""
Module pour interagir avec l'API Binance et placer des ordres de trading
"""
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from loguru import logger

class BinanceTrader:
    """Classe pour interagir avec l'API Binance et placer des ordres de trading"""
    
    def __init__(self, api_key=None, api_secret=None):
        """Initialise le trader Binance"""
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Clés API Binance non trouvées dans les variables d'environnement")
        
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialise le client Binance"""
        try:
            client = Client(self.api_key, self.api_secret)
            logger.info("Client Binance initialisé avec succès")
            return client
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Binance: {str(e)}")
            return None
    
    def test_connection(self):
        """Teste la connexion à l'API Binance"""
        try:
            if not self.client:
                return False, "Client Binance non initialisé"
            
            # Tester la connexion en récupérant le statut du système
            status = self.client.get_system_status()
            
            if status and status.get("status") == 0:
                # Vérifier également l'accès au compte futures
                try:
                    self.client.futures_account_balance()
                    return True, "Connexion à l'API Binance réussie (spot et futures)"
                except BinanceAPIException as e:
                    return False, f"Connexion au compte spot réussie, mais erreur avec le compte futures: {str(e)}"
            else:
                return False, f"Système Binance indisponible: {status}"
        except Exception as e:
            return False, f"Erreur lors du test de connexion à l'API Binance: {str(e)}"
    
    def get_futures_balance(self):
        """Récupère le solde du compte futures"""
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return None
            
            balances = self.client.futures_account_balance()
            
            # Filtrer pour obtenir le solde USDT
            usdt_balance = next((b for b in balances if b["asset"] == "USDT"), None)
            
            if usdt_balance:
                available_balance = float(usdt_balance["withdrawAvailable"])
                logger.info(f"Solde futures disponible: {available_balance} USDT")
                return available_balance
            else:
                logger.warning("Aucun solde USDT trouvé dans le compte futures")
                return 0
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du solde futures: {str(e)}")
            return None
    
    def set_leverage(self, symbol, leverage):
        """Définit le levier pour un symbole donné"""
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Limiter le levier à 20x (maximum généralement autorisé sur Binance)
            leverage = min(leverage, 20)
            
            # Définir le levier
            response = self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            logger.info(f"Levier défini pour {symbol}: {leverage}x")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la définition du levier pour {symbol}: {str(e)}")
            return False
    
    def set_margin_type(self, symbol, margin_type="CROSSED"):
        """
        Définit le type de marge pour un symbole donné (CROSSED pour Cross Margin, ISOLATED pour Isolated Margin)
        """
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Définir le type de marge
            try:
                response = self.client.futures_change_margin_type(symbol=symbol, marginType=margin_type)
                logger.info(f"Type de marge défini pour {symbol}: {margin_type}")
                return True
            except BinanceAPIException as e:
                # Si l'erreur est que le type de marge est déjà défini, c'est OK
                if "Already" in str(e):
                    logger.info(f"Le type de marge {margin_type} est déjà défini pour {symbol}")
                    return True
                else:
                    raise e
        except Exception as e:
            logger.error(f"Erreur lors de la définition du type de marge pour {symbol}: {str(e)}")
            return False
    
    def place_short_order(self, symbol, leverage=1):
        """
        Place un ordre de vente à découvert (short) sur le marché futures
        
        Args:
            symbol (str): Le symbole à shorter (ex: "BTCUSDT")
            leverage (int): Le levier à utiliser (1-20)
            
        Returns:
            bool: True si l'ordre a été placé avec succès, False sinon
        """
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Définir le type de marge à CROSSED (Cross Margin)
            self.set_margin_type(symbol, "CROSSED")
            
            # Définir le levier
            self.set_leverage(symbol, leverage)
            
            # Récupérer le solde disponible
            available_balance = self.get_futures_balance()
            
            if not available_balance or available_balance <= 0:
                logger.error("Solde futures insuffisant pour placer un ordre")
                return False
            
            # Récupérer le prix actuel du symbole
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker["price"])
            
            # Calculer la quantité à shorter (en tenant compte du levier)
            # Utiliser 95% du solde disponible pour éviter les erreurs de marge insuffisante
            quantity = (available_balance * 0.95 * leverage) / current_price
            
            # Arrondir la quantité à la précision appropriée
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info["symbols"] if s["symbol"] == symbol), None)
            
            if not symbol_info:
                logger.error(f"Symbole {symbol} non trouvé dans les informations de l'échange")
                return False
            
            # Trouver la précision de la quantité
            quantity_precision = symbol_info["quantityPrecision"]
            quantity = round(quantity, quantity_precision)
            
            # Placer l'ordre de vente à découvert
            order = self.client.futures_create_order(
                symbol=symbol,
                side="SELL",  # SELL pour shorter
                type="MARKET",
                quantity=quantity
            )
            
            logger.success(f"Ordre de short placé avec succès pour {symbol}: {quantity} à {current_price} USDT avec un levier de {leverage}x")
            logger.info(f"Détails de l'ordre: {order}")
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors du placement de l'ordre de short pour {symbol}: {str(e)}")
            return False
