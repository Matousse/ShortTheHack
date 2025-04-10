"""
Module pour récupérer les tweets d'un compte Twitter spécifique
"""
import os
import time
import random
import tweepy
from loguru import logger

class TwitterScraper:
    """Classe pour scraper les tweets d'un compte Twitter spécifique"""
    
    def __init__(self, target_account=None):
        """Initialise le scraper Twitter"""
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            logger.warning("Token d'authentification Twitter non trouvé dans les variables d'environnement")
        
        self.target_account = target_account or os.getenv("TARGET_TWITTER_ACCOUNT", "DamienMATHIS4")
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialise le client Twitter"""
        try:
            client = tweepy.Client(bearer_token=self.bearer_token)
            logger.info("Client Twitter initialisé avec succès")
            return client
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Twitter: {str(e)}")
            return None
    
    def _handle_rate_limit(self):
        """Gère les limites de taux - ne fait plus de retry"""
        logger.warning("Limite de requêtes Twitter atteinte. Aucune nouvelle tentative ne sera effectuée.")
        return False
    
    def get_latest_tweet(self, username=None):
        """Récupère le dernier tweet d'un compte Twitter"""
        target = username or self.target_account
        
        # Vérifier si le client est initialisé
        if not self.client:
            logger.error("Client Twitter non initialisé")
            return None
        
        try:
            # Récupérer les informations de l'utilisateur
            user = self.client.get_user(username=target)
            if not user or not user.data:
                logger.error(f"Utilisateur Twitter {target} non trouvé")
                return None
            
            user_id = user.data.id
            
            # Récupérer les tweets de l'utilisateur (max 3 pour réduire la charge)
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=3,
                tweet_fields=["created_at", "text", "public_metrics"]
            )
            
            if not tweets or not tweets.data:
                logger.warning(f"Aucun tweet trouvé pour l'utilisateur {target}")
                return None
            
            # Prendre le tweet le plus récent
            latest_tweet = tweets.data[0]
            
            # Formater les données du tweet
            tweet_data = {
                "id": latest_tweet.id,
                "text": latest_tweet.text,
                "created_at": latest_tweet.created_at.isoformat(),
                "metrics": latest_tweet.public_metrics if hasattr(latest_tweet, "public_metrics") else {}
            }
            
            logger.info(f"Tweet récupéré pour {target}: {tweet_data['text'][:50]}...")
            return tweet_data
            
        except tweepy.errors.TooManyRequests:
            self._handle_rate_limit()
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données Twitter pour {target}: {str(e)}")
            return None
    
    def test_connection(self):
        """Teste la connexion à l'API Twitter"""
        try:
            if not self.client:
                return False, "Client Twitter non initialisé"
            
            # Tester la connexion en récupérant un utilisateur aléatoire (Twitter)
            user = self.client.get_user(username="Twitter")
            if user and user.data:
                return True, "Connexion à l'API Twitter réussie"
            else:
                return False, "Impossible de récupérer des données depuis l'API Twitter"
        except Exception as e:
            return False, f"Erreur lors du test de connexion à l'API Twitter: {str(e)}"
