"""
Module for interacting with the Binance API and placing trading orders
"""
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from loguru import logger

class BinanceTrader:
    """Class for interacting with the Binance API and placing trading orders"""
    
    def __init__(self, api_key=None, api_secret=None):
        """Initialize the Binance trader"""
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance API keys not found in environment variables")
        
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialize the Binance client"""
        try:
            client = Client(self.api_key, self.api_secret)
            logger.info("Binance client successfully initialized")
            return client
        except Exception as e:
            logger.error(f"Error initializing Binance client: {str(e)}")
            return None
    
    def test_connection(self):
        """Test the connection to the Binance API"""
        try:
            if not self.client:
                return False, "Binance client not initialized"
            
            # Test the connection by retrieving the system status
            status = self.client.get_system_status()
            
            if status and status.get("status") == 0:
                # Also check access to futures account
                try:
                    self.client.futures_account_balance()
                    return True, "Connection to Binance API successful (spot and futures)"
                except BinanceAPIException as e:
                    return False, f"Connection to spot account successful, but error with futures account: {str(e)}"
            else:
                return False, f"Binance system unavailable: {status}"
        except Exception as e:
            return False, f"Error testing connection to Binance API: {str(e)}"
    
    def get_futures_balance(self):
        """Retrieve the futures account balance"""
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return None
            
            balances = self.client.futures_account_balance()
            
            # Filter to get USDT balance
            usdt_balance = next((b for b in balances if b["asset"] == "USDT"), None)
            
            if usdt_balance:
                available_balance = float(usdt_balance["withdrawAvailable"])
                logger.info(f"Available futures balance: {available_balance} USDT")
                return available_balance
            else:
                logger.warning("No USDT balance found in futures account")
                return 0
        except Exception as e:
            logger.error(f"Error retrieving futures balance: {str(e)}")
            return None
    
    def set_leverage(self, symbol, leverage):
        """Set the leverage for a given symbol"""
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Limit leverage to 20x (maximum generally allowed on Binance)
            leverage = min(leverage, 20)
            
            # Définir le levier
            response = self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            logger.info(f"Leverage set for {symbol}: {leverage}x")
            return True
        except Exception as e:
            logger.error(f"Error setting leverage for {symbol}: {str(e)}")
            return False
    
    def set_margin_type(self, symbol, margin_type="CROSSED"):
        """
        Set the margin type for a given symbol (CROSSED for Cross Margin, ISOLATED for Isolated Margin)
        """
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Définir le type de marge
            try:
                response = self.client.futures_change_margin_type(symbol=symbol, marginType=margin_type)
                logger.info(f"Margin type set for {symbol}: {margin_type}")
                return True
            except BinanceAPIException as e:
                # If the error is that the margin type is already set, that's OK
                if "Already" in str(e):
                    logger.info(f"Margin type {margin_type} is already set for {symbol}")
                    return True
                else:
                    raise e
        except Exception as e:
            logger.error(f"Error setting margin type for {symbol}: {str(e)}")
            return False
    
    def place_short_order(self, symbol, leverage=1):
        """
        Place a short sell order on the futures market
        
        Args:
            symbol (str): The symbol to short (e.g., "BTCUSDT")
            leverage (int): The leverage to use (1-20)
            
        Returns:
            bool: True if the order was successfully placed, False otherwise
        """
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Set margin type to CROSSED (Cross Margin)
            self.set_margin_type(symbol, "CROSSED")
            
            # Définir le levier
            self.set_leverage(symbol, leverage)
            
            # Get available balance
            available_balance = self.get_futures_balance()
            
            if not available_balance or available_balance <= 0:
                logger.error("Insufficient futures balance to place an order")
                return False
            
            # Get current symbol price
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker["price"])
            
            # Calculate quantity to short (taking leverage into account)
            # Use 95% of available balance to avoid insufficient margin errors
            quantity = (available_balance * 0.95 * leverage) / current_price
            
            # Round the quantity to the appropriate precision
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info["symbols"] if s["symbol"] == symbol), None)
            
            if not symbol_info:
                logger.error(f"Symbol {symbol} not found in exchange information")
                return False
            
            # Find the quantity precision
            quantity_precision = symbol_info["quantityPrecision"]
            quantity = round(quantity, quantity_precision)
            
            # Place the short sell order
            order = self.client.futures_create_order(
                symbol=symbol,
                side="SELL",  # SELL for shorting
                type="MARKET",
                quantity=quantity
            )
            
            logger.success(f"Short order successfully placed for {symbol}: {quantity} at {current_price} USDT with leverage of {leverage}x")
            logger.info(f"Order details: {order}")
            
            return True
        except Exception as e:
            logger.error(f"Error placing short order for {symbol}: {str(e)}")
            return False
