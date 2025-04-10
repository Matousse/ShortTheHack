"""
Module pour interagir avec l'API Binance et placer des ordres de trading
"""
import os
import time
from datetime import datetime
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
                # Vérifier l'accès au compte margin
                try:
                    self.client.get_margin_account()
                    return True, "Connexion à l'API Binance réussie (spot et margin)"
                except BinanceAPIException as e:
                    # Ne pas considérer l'échec de l'accès au margin comme une erreur critique
                    logger.warning(f"Accès au compte margin impossible: {str(e)}. Fonctionnement en mode spot uniquement.")
                    return True, "Connexion à l'API Binance réussie (spot uniquement, margin non disponible)"
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
    
    def get_margin_balance(self, asset="USDT"):
        """Récupère le solde du compte margin pour un asset spécifique"""
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return None
            
            account = self.client.get_margin_account()
            
            # Récupérer le solde de l'asset spécifié
            asset_balance = next((a for a in account["userAssets"] if a["asset"] == asset), None)
            
            if asset_balance:
                available_balance = float(asset_balance["free"])
                logger.info(f"Solde margin disponible: {available_balance} {asset}")
                return available_balance
            else:
                logger.warning(f"Aucun solde {asset} trouvé dans le compte margin")
                return 0
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du solde margin: {str(e)}")
            return None
            
    def get_usdc_margin_balance(self):
        """Récupère le solde USDC du compte margin"""
        return self.get_margin_balance("USDC")
            
    def place_short_order(self, symbol, leverage=1):
        """
        Place un ordre de vente à découvert (short) sur le marché margin
        
        Args:
            symbol (str): Le symbole à shorter (ex: "BTCUSDT")
            leverage (int): Le levier à utiliser (1-10)
            
        Returns:
            tuple: (success, order_id) où success est un booléen indiquant si l'ordre a été placé avec succès,
                  et order_id est l'identifiant de l'ordre (ou None en cas d'échec)
        """
        logger.info(f"\n\n===== DÉBUT PLACE_SHORT_ORDER =====")
        logger.info(f"Symbole: {symbol}")
        logger.info(f"Levier: {leverage}")
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Vérifier si le margin trading est disponible
            try:
                # Tester l'accès au compte margin
                logger.info("Vérification de l'accès au compte margin...")
                margin_account = self.client.get_margin_account()
                logger.info("Accès au compte margin vérifié")
                logger.info(f"Type de compte: {margin_account.get('accountType', 'Inconnu')}")
                logger.info(f"Niveau de risque: {margin_account.get('marginLevel', 'Inconnu')}")
            except Exception as e:
                logger.error(f"Impossible d'accéder au compte margin: {str(e)}")
                logger.error("L'ordre de short ne peut pas être placé sans accès au margin trading")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False, None
            
            # Récupérer le solde USDC pour l'utiliser comme collatéral
            logger.info("Récupération du solde USDC margin disponible...")
            usdc_balance = self.get_usdc_margin_balance()
            logger.info(f"Solde USDC margin disponible: {usdc_balance} USDC")
            
            # Récupérer aussi le solde USDT
            usdt_balance = self.get_margin_balance("USDT")
            logger.info(f"Solde USDT margin disponible: {usdt_balance} USDT")
            
            # Vérifier les soldes disponibles
            if usdt_balance > 0:
                logger.info("Utilisation du solde USDT pour le trading")
                available_balance = usdt_balance
                quote_asset = "USDT"
            elif usdc_balance > 0:
                logger.info("Utilisation du solde USDC comme collatéral, mais trading sur ETHUSDT")
                available_balance = usdc_balance
                quote_asset = "USDT"  # On utilise quand même USDT pour le symbole
            else:
                logger.error("Aucun solde USDC ou USDT disponible pour placer un ordre")
                return False, None
                
            # Utiliser BTCUSDC pour le trading
            symbol = "BTCUSDC"
            logger.info(f"Utilisation du symbole {symbol} pour le margin trading")
                
            # Limiter le montant à 3 USDC/USDT maximum
            if available_balance > 3.0:
                logger.info(f"Limitation du montant à 3 {quote_asset} comme demandé")
                available_balance = 3.0
            
            # Récupérer le prix actuel du symbole
            logger.info(f"Récupération du prix actuel de {symbol}...")
            try:
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker["price"])
                logger.info(f"Prix actuel de {symbol}: {current_price} USDC")
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du prix pour {symbol}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False, None
            
            # Fixer la quantité de BTC à 0.00003
            quantity = 0.00003
            # Calculer le montant de la transaction
            trade_amount = quantity * current_price
            logger.info(f"Quantité fixée à {quantity} BTC (valeur: {trade_amount} {quote_asset})")
            
            # Augmenter la quantité pour éviter l'erreur NOTIONAL (valeur minimale)
            # La plupart des paires ont une valeur minimale de 10 USDT
            min_notional = 10.0  # Valeur minimale typique pour Binance
            if trade_amount < min_notional:
                logger.warning(f"Montant de trading ({trade_amount} {quote_asset}) inférieur au minimum recommandé ({min_notional} {quote_asset})")
                logger.warning("Augmentation de la quantité pour atteindre le minimum requis")
                quantity = min_notional / current_price
                trade_amount = min_notional
                
            logger.info(f"Quantité calculée pour le short: {quantity} BTC (valeur: {trade_amount} {quote_asset})")
            
            # Ajuster la quantité selon les règles de LOT_SIZE
            try:
                # Récupérer les informations sur le symbole
                symbol_info = self.client.get_symbol_info(symbol)
                if not symbol_info:
                    logger.error(f"Symbole {symbol} non trouvé dans les informations de l'échange")
                    return False, None
                    
                # Trouver le filtre LOT_SIZE
                lot_size_filter = next((f for f in symbol_info["filters"] if f["filterType"] == "LOT_SIZE"), None)
                if lot_size_filter:
                    min_qty = float(lot_size_filter["minQty"])
                    step_size = float(lot_size_filter["stepSize"])
                    
                    # Vérifier si la quantité est supérieure au minimum requis
                    if quantity < min_qty:
                        logger.warning(f"Quantité {quantity} inférieure au minimum requis {min_qty}")
                        quantity = min_qty
                        logger.info(f"Quantité ajustée au minimum: {quantity}")
                    
                    # Arrondir selon le step_size
                    from decimal import Decimal, ROUND_DOWN
                    
                    def adjust_to_step(qty, step):
                        step_str = f"{step:g}"  # Convertir en notation scientifique pour éliminer les zéros de fin
                        precision = len(step_str.split('.')[-1]) if '.' in step_str else 0
                        return float(Decimal(qty).quantize(Decimal(step_str), rounding=ROUND_DOWN))
                    
                    original_quantity = quantity
                    quantity = adjust_to_step(quantity, step_size)
                    logger.info(f"Quantité ajustée selon step_size: {original_quantity} -> {quantity}")
            except Exception as e:
                logger.warning(f"Erreur lors de l'ajustement de la quantité: {str(e)}")
                # Arrondir à 4 décimales par défaut si l'ajustement échoue
                quantity = round(quantity, 4)
            
            # La quantité a déjà été ajustée selon les règles de LOT_SIZE plus haut
            
            # 1. Emprunter la crypto que nous voulons shorter
            try:
                # Pour un short, on emprunte seulement la partie base (BTC), pas le symbole complet
                # Extraire BTC de BTCUSDC
                asset = "BTC"
                logger.info(f"\n===== EMPRUNT DE CRYPTO =====")
                logger.info(f"Asset: {asset}")
                logger.info(f"Quantité: {quantity}")
                
                # Vérifier si l'asset est disponible pour l'emprunt
                margin_account = self.client.get_margin_account()
                available_assets = {asset_data["asset"]: asset_data for asset_data in margin_account["userAssets"]}
                
                logger.info(f"Recherche de l'asset {asset} dans le compte margin")
                
                if asset in available_assets:
                    asset_info = available_assets[asset]
                    logger.info(f"Informations sur l'asset {asset}:")
                    logger.info(f"  - Free: {asset_info.get('free', 'N/A')}")
                    logger.info(f"  - Locked: {asset_info.get('locked', 'N/A')}")
                    logger.info(f"  - Borrowed: {asset_info.get('borrowed', 'N/A')}")
                    logger.info(f"  - Interest: {asset_info.get('interest', 'N/A')}")
                else:
                    logger.warning(f"L'asset {asset} n'est pas disponible dans le compte margin")
                    # Afficher tous les assets disponibles pour aider au débogage
                    logger.info("Assets disponibles dans le compte margin:")
                    for available_asset in available_assets.keys():
                        logger.info(f"  - {available_asset}")
                
                # Vérifier les assets disponibles pour l'emprunt
                logger.info("Vérification des assets disponibles pour l'emprunt...")
                try:
                    max_borrowable = self.client.get_max_margin_loan(asset=asset)
                    logger.info(f"Montant maximum empruntable pour {asset}: {max_borrowable}")
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification du montant maximum empruntable: {str(e)}")
                    max_borrowable = {"amount": "0", "borrowLimit": "0"}
                
                # Ajuster la quantité si nécessaire
                try:
                    max_amount = float(max_borrowable.get('amount', 0))
                    if max_amount <= 0:
                        logger.warning(f"Impossible d'emprunter {asset} (montant maximum: {max_amount})")
                        logger.info("Tentative avec un autre symbole...")
                        return False, None
                    
                    if max_amount < quantity:
                        logger.warning(f"Quantité ajustée de {quantity} à {max_amount} (maximum empruntable)")
                        quantity = max_amount
                except Exception as e:
                    logger.warning(f"Impossible de déterminer le montant maximum empruntable: {str(e)}")
                
                # Effectuer l'emprunt
                logger.info(f"Tentative d'emprunt de {quantity} {asset}...")
                loan = self.client.create_margin_loan(
                    asset=asset,
                    amount=quantity
                )
                logger.info(f"Emprunt réussi: {loan}")
            except Exception as e:
                logger.error(f"Erreur lors de l'emprunt pour le short: {str(e)}")
                import traceback
                logger.error(f"Traceback de l'erreur d'emprunt: {traceback.format_exc()}")
                return False, None
            
            # 2. Vendre la crypto empruntée (ordre de marché)
            try:
                logger.info(f"\n===== VENTE DE LA CRYPTO EMPRUNTÉE =====")
                logger.info(f"Symbole: {symbol}")
                logger.info(f"Quantité: {quantity}")
                logger.info(f"Type d'ordre: MARKET")
                
                # Vérifier les règles de trading pour ce symbole
                try:
                    exchange_info = self.client.get_exchange_info()
                    symbol_info = next((s for s in exchange_info["symbols"] if s["symbol"] == symbol), None)
                    if symbol_info:
                        logger.info(f"Règles de trading pour {symbol}:")
                        logger.info(f"  - Status: {symbol_info.get('status', 'N/A')}")
                        logger.info(f"  - Permissions: {symbol_info.get('permissions', 'N/A')}")
                        
                        # Vérifier si le margin trading est autorisé
                        if 'MARGIN' not in symbol_info.get('permissions', []):
                            logger.warning(f"Le margin trading n'est pas autorisé pour {symbol}!")
                except Exception as e:
                    logger.warning(f"Impossible de vérifier les règles de trading: {str(e)}")
                
                # Essayer d'abord de vendre sur le marché margin
                logger.info(f"Tentative de vente sur {symbol} (marché MARGIN)...")
                try:
                    # Vérifier si le symbole existe sur Binance
                    exchange_info = self.client.get_exchange_info()
                    symbol_exists = any(s["symbol"] == symbol for s in exchange_info["symbols"])
                    
                    if not symbol_exists:
                        logger.error(f"Le symbole {symbol} n'existe pas sur Binance")
                        return False, None
                    
                    # Ajouter un délai pour s'assurer que l'ETH emprunté est disponible
                    import time
                    logger.info("Attente de 2 secondes pour s'assurer que le BTC emprunté est disponible...")
                    time.sleep(2)
                    
                    # Vérifier que le BTC est bien disponible dans le compte margin
                    margin_account = self.client.get_margin_account()
                    btc_asset = next((asset for asset in margin_account["userAssets"] if asset["asset"] == "BTC"), None)
                    
                    if btc_asset:
                        free_btc = float(btc_asset["free"])
                        logger.info(f"BTC disponible dans le compte margin: {free_btc}")
                        
                        if free_btc < quantity:
                            logger.warning(f"BTC disponible ({free_btc}) inférieur à la quantité à vendre ({quantity})")
                            quantity = free_btc
                            logger.info(f"Quantité ajustée au BTC disponible: {quantity}")
                    
                    # Vendre directement sur le marché margin
                    logger.info(f"Vente de {quantity} BTC sur le marché margin...")
                    order = self.client.create_margin_order(
                        symbol=symbol,
                        side="SELL",
                        type="MARKET",
                        quantity=quantity,
                        sideEffectType="NO_SIDE_EFFECT"  # Pas d'emprunt automatique
                    )
                    logger.info(f"Vente réussie sur le marché margin: {order}")
                except Exception as e:
                    logger.error(f"Erreur lors de la création de l'ordre: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return False, None
                
                # Récupérer l'ID de l'ordre
                order_id = order.get("orderId", str(order.get("clientOrderId", "unknown")))
                
                logger.info(f"Ordre de short placé avec succès pour {symbol}")
                logger.info(f"  - Quantité: {quantity} {symbol.replace('USDT', '')}")
                logger.info(f"  - Prix: ~{current_price} USDT")
                logger.info(f"  - ID de l'ordre: {order_id}")
                logger.info(f"  - Détails: {order}")
                
                return True, order_id
            except Exception as e:
                logger.error(f"Erreur lors du placement de l'ordre de short pour {symbol}: {str(e)}")
                # Afficher plus de détails sur l'erreur
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False, None
                
        except Exception as e:
            logger.error(f"\n===== ERREUR GÉNÉRALE =====")
            logger.error(f"Erreur lors du placement de l'ordre de short pour {symbol}: {str(e)}")
            # Afficher plus de détails sur l'erreur
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, None
        finally:
            logger.info(f"===== FIN PLACE_SHORT_ORDER =====\n")
    
    def get_active_shorts(self):
        """
        Récupère la liste des positions shorts actives sur le compte margin
        
        Returns:
            list: Liste des positions shorts actives, chaque position étant un dictionnaire
                 contenant les informations sur la position
        """
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return []
            
            # Récupérer les positions ouvertes
            account = self.client.get_margin_account()
            borrowed_assets = [asset for asset in account["userAssets"] if float(asset["borrowed"]) > 0]
            
            active_shorts = []
            
            for asset in borrowed_assets:
                asset_symbol = asset["asset"]
                borrowed_amount = float(asset["borrowed"])
                
                if borrowed_amount > 0:
                    # Générer un ID unique pour cette position
                    position_id = f"margin_{asset_symbol}_{int(time.time())}"
                    
                    # Récupérer le prix actuel
                    try:
                        ticker = self.client.get_symbol_ticker(symbol=f"{asset_symbol}USDT")
                        current_price = float(ticker["price"])
                    except:
                        current_price = 0
                    
                    # Créer une entrée pour cette position
                    short_info = {
                        "id": position_id,
                        "symbol": f"{asset_symbol}USDT",
                        "leverage": 1,  # Par défaut, nous ne pouvons pas connaître le levier utilisé
                        "timestamp": datetime.now().isoformat(),
                        "quantity": borrowed_amount,
                        "entry_price": current_price
                    }
                    
                    active_shorts.append(short_info)
            
            return active_shorts
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des positions shorts actives: {str(e)}")
            return []
    
    def force_close_short(self, asset_symbol="BTC"):
        """
        Force la fermeture d'un short en remboursant directement l'emprunt
        
        Args:
            asset_symbol (str): Le symbole de l'actif emprunté (ex: "BTC")
            
        Returns:
            bool: True si la position a été fermée avec succès, False sinon
        """
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Récupérer les positions ouvertes
            account = self.client.get_margin_account()
            borrowed_assets = [asset for asset in account["userAssets"] if float(asset["borrowed"]) > 0]
            
            # Vérifier si nous avons une position ouverte pour cet actif
            borrowed_asset = next((asset for asset in borrowed_assets if asset["asset"] == asset_symbol), None)
            
            if not borrowed_asset:
                logger.warning(f"Aucune position short trouvée pour {asset_symbol}")
                return True  # Considérer comme un succès si aucune position n'est trouvée
            
            # Récupérer la quantité empruntée
            borrowed_amount = float(borrowed_asset["borrowed"])
            
            if borrowed_amount <= 0:
                logger.warning(f"Aucune quantité empruntée pour {asset_symbol}")
                return True
            
            logger.info(f"Tentative de fermeture forcée du short sur {asset_symbol}")
            logger.info(f"Montant emprunté: {borrowed_amount} {asset_symbol}")
            
            # 1. Vérifier si nous avons assez de l'actif pour rembourser directement
            free_amount = float(borrowed_asset["free"])
            logger.info(f"Montant disponible: {free_amount} {asset_symbol}")
            
            if free_amount < borrowed_amount:
                # Nous devons acheter l'actif pour rembourser
                symbol = f"{asset_symbol}USDC"  # Utiliser USDC au lieu de USDT
                logger.info(f"Achat de {borrowed_amount} {asset_symbol} pour rembourser l'emprunt")
                
                try:
                    # Vérifier le prix actuel
                    ticker = self.client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker["price"])
                    logger.info(f"Prix actuel de {symbol}: {current_price} USDT")
                    
                    # Acheter l'actif
                    order = self.client.create_margin_order(
                        symbol=symbol,
                        side="BUY",
                        type="MARKET",
                        quantity=borrowed_amount,
                        sideEffectType="NO_SIDE_EFFECT"
                    )
                    
                    logger.success(f"Achat réussi de {borrowed_amount} {asset_symbol}")
                    logger.info(f"Détails de l'ordre: {order}")
                except Exception as e:
                    logger.error(f"Erreur lors de l'achat de {asset_symbol}: {str(e)}")
                    logger.warning("Tentative de remboursement direct avec le solde disponible")
            
            # 2. Rembourser l'emprunt
            try:
                # Utiliser le montant disponible si insuffisant
                repay_amount = min(borrowed_amount, free_amount) if free_amount > 0 else borrowed_amount
                
                repay = self.client.repay_margin_loan(
                    asset=asset_symbol,
                    amount=repay_amount
                )
                
                logger.success(f"Remboursement réussi pour {asset_symbol}: {repay_amount}")
                logger.info(f"Détails du remboursement: {repay}")
                
                return True
            except Exception as e:
                logger.error(f"Erreur lors du remboursement de l'emprunt pour {asset_symbol}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture forcée du short sur {asset_symbol}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def close_short_position(self, symbol, order_id):
        """
        Ferme une position short en rachetant la crypto empruntée
        
        Args:
            symbol (str): Le symbole de la position à fermer (ex: "BTCUSDT")
            order_id (str): L'identifiant de l'ordre à fermer
            
        Returns:
            bool: True si la position a été fermée avec succès, False sinon
        """
        try:
            if not self.client:
                logger.error("Client Binance non initialisé")
                return False
            
            # Récupérer les positions ouvertes
            account = self.client.get_margin_account()
            borrowed_assets = [asset for asset in account["userAssets"] if float(asset["borrowed"]) > 0]
            
            # Vérifier si nous avons une position ouverte pour ce symbole
            asset_symbol = symbol.replace("USDT", "")
            borrowed_asset = next((asset for asset in borrowed_assets if asset["asset"] == asset_symbol), None)
            
            if not borrowed_asset:
                logger.warning(f"Aucune position short trouvée pour {symbol}")
                return True  # Considérer comme un succès si aucune position n'est trouvée
            
            # Récupérer la quantité empruntée
            borrowed_amount = float(borrowed_asset["borrowed"])
            
            if borrowed_amount <= 0:
                logger.warning(f"Aucune quantité empruntée pour {asset_symbol}")
                return True
            
            # 1. Acheter la crypto pour rembourser l'emprunt
            try:
                order = self.client.create_margin_order(
                    symbol=symbol,
                    side="BUY",  # BUY pour fermer le short
                    type="MARKET",
                    quantity=borrowed_amount,
                    sideEffectType="NO_SIDE_EFFECT"
                )
                
                logger.success(f"Ordre d'achat placé avec succès pour fermer le short sur {symbol}: {borrowed_amount}")
                logger.info(f"Détails de l'ordre: {order}")
            except Exception as e:
                logger.error(f"Erreur lors du placement de l'ordre d'achat pour fermer le short sur {symbol}: {str(e)}")
                return False
            
            # 2. Rembourser l'emprunt
            try:
                repay = self.client.repay_margin_loan(
                    asset=asset_symbol,
                    amount=borrowed_amount
                )
                
                logger.success(f"Remboursement réussi pour {asset_symbol}: {borrowed_amount}")
                logger.info(f"Détails du remboursement: {repay}")
                
                return True
            except Exception as e:
                logger.error(f"Erreur lors du remboursement de l'emprunt pour {asset_symbol}: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de la position short pour {symbol}: {str(e)}")
            return False
            
    def get_min_trade_quantity(self, symbol='BTCUSDC'):
        """
        Obtient la quantité minimale de trading pour un symbole donné
        
        Args:
            symbol (str): Le symbole pour lequel obtenir la quantité minimale (ex: "BTCUSDC")
            
        Returns:
            dict: Dictionnaire contenant les informations sur les limites de trading
        """
        try:
            # Essayer d'abord avec l'API margin pour être sûr
            try:
                margin_pairs = self.client.get_margin_all_pairs()
                for pair in margin_pairs:
                    if pair['symbol'] == symbol:
                        # Récupérer les détails spécifiques au margin
                        margin_pair = self.client.get_margin_pair(symbol=symbol)
                        logger.info(f"Informations margin pour {symbol}: {margin_pair}")
                        return {
                            'margin_info': margin_pair,
                            'min_qty': None  # À compléter si l'API retourne cette info
                        }
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération des infos margin: {str(e)}")
            
            # Utiliser l'API spot comme fallback
            symbol_info = self.client.get_symbol_info(symbol)
            if not symbol_info:
                raise Exception(f"Symbole {symbol} non trouvé.")
                
            min_qty = None
            min_notional = None
            lot_size_info = None
            min_notional_info = None
            
            for filt in symbol_info['filters']:
                if filt['filterType'] == 'LOT_SIZE':
                    min_qty = float(filt['minQty'])
                    lot_size_info = filt
                elif filt['filterType'] == 'MIN_NOTIONAL':
                    min_notional = float(filt['minNotional'])
                    min_notional_info = filt
            
            if min_qty is None:
                raise Exception(f"Filtre LOT_SIZE non trouvé pour {symbol}")
                
            return {
                'symbol': symbol,
                'min_qty': min_qty,
                'min_notional': min_notional,
                'lot_size_filter': lot_size_info,
                'min_notional_filter': min_notional_info,
                'all_filters': symbol_info['filters']
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la quantité minimale: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'error': str(e)}
