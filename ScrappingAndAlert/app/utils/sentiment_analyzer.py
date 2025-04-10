"""
Module pour analyser le sentiment des tweets à l'aide de l'API Claude
"""
import os
import json
from anthropic import Anthropic
from loguru import logger

class SentimentAnalyzer:
    """Classe pour analyser le sentiment des tweets à l'aide de l'API Claude"""
    
    def __init__(self, api_key=None):
        """Initialise l'analyseur de sentiment"""
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            logger.warning("Clé API Claude non trouvée dans les variables d'environnement")
        
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialise le client Claude"""
        try:
            client = Anthropic(api_key=self.api_key)
            logger.info("Client Claude initialisé avec succès")
            return client
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Claude: {str(e)}")
            return None
    
    def is_hack_event(self, text):
        """
        Détermine si un texte contient des informations sur un événement de hack
        
        Args:
            text (str): Le texte à analyser
            
        Returns:
            bool: True si le texte contient des informations sur un hack, False sinon
        """
        try:
            if not self.client:
                logger.error("Client Claude non initialisé")
                return False
            
            # Construire le prompt pour Claude
            prompt = f"""
            Analyse le tweet suivant et détermine s'il contient le mot "hack" ET s'il suggère qu'un hack est survenu.
            
            Tweet: "{text}"
            
            Réponds uniquement par un JSON avec une clé "is_hack" qui contient un booléen (true/false).
            Réponds true uniquement si le tweet contient le mot "hack" ET suggère qu'un hack a réellement eu lieu.
            """
            
            # Appeler l'API Claude
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=100,
                temperature=0,
                system="Tu es un assistant qui analyse des tweets pour détecter des événements de hack. Réponds uniquement par un JSON avec une clé 'is_hack' qui contient un booléen.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extraire la réponse
            content = response.content[0].text
            
            # Essayer de parser la réponse JSON
            try:
                result = json.loads(content)
                is_hack = result.get("is_hack", False)
                logger.info(f"Analyse du tweet: is_hack={is_hack}")
                return is_hack
            except json.JSONDecodeError:
                # Si la réponse n'est pas un JSON valide, vérifier si elle contient "true"
                logger.warning(f"Réponse Claude non JSON: {content}")
                return "true" in content.lower()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du tweet: {str(e)}")
            return False
    
    def test_connection(self):
        """Teste la connexion à l'API Claude"""
        try:
            if not self.client:
                return False, "Client Claude non initialisé"
            
            # Tester la connexion en envoyant une requête simple
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Dis bonjour"}
                ]
            )
            
            if response and response.content:
                return True, "Connexion à l'API Claude réussie"
            else:
                return False, "Impossible de récupérer des données depuis l'API Claude"
        except Exception as e:
            return False, f"Erreur lors du test de connexion à l'API Claude: {str(e)}"
