"""
Module de gestion de la configuration de l'application
"""
import os
import json
from pathlib import Path
from loguru import logger

class ConfigManager:
    """Gestionnaire de configuration pour l'application GentleMate"""
    
    def __init__(self, config_file="config.json"):
        """Initialise le gestionnaire de configuration"""
        self.config_file = config_file
        self.default_settings = {
            "trading_enabled": False,
            "target_account": os.getenv("TARGET_TWITTER_ACCOUNT", "DamienMATHIS4"),
            "target_coin": os.getenv("DEFAULT_COIN", "USDC"),
            "leverage": 1,
            "check_interval": int(os.getenv("CHECK_INTERVAL", 3))
        }
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Charge les paramètres depuis le fichier de configuration"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, "r") as f:
                    settings = json.load(f)
                logger.info(f"Paramètres chargés depuis {self.config_file}")
                return settings
            else:
                logger.info(f"Fichier de configuration {self.config_file} non trouvé, utilisation des paramètres par défaut")
                self._save_settings(self.default_settings)
                return self.default_settings
        except Exception as e:
            logger.error(f"Erreur lors du chargement des paramètres: {str(e)}")
            return self.default_settings
    
    def _save_settings(self, settings):
        """Sauvegarde les paramètres dans le fichier de configuration"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(settings, f, indent=4)
            logger.info(f"Paramètres sauvegardés dans {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paramètres: {str(e)}")
            return False
    
    def get_settings(self):
        """Retourne les paramètres actuels"""
        return self.settings
    
    def update_settings(self, new_settings):
        """Met à jour les paramètres"""
        self.settings.update(new_settings)
        self._save_settings(self.settings)
        logger.info(f"Paramètres mis à jour: {new_settings}")
        return self.settings
