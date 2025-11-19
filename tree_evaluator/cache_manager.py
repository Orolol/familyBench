"""Gestionnaire de cache pour les appels API."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import diskcache

logger = logging.getLogger(__name__)

class CacheManager:
    """Gère le cache des réponses API sur le disque."""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache = diskcache.Cache(str(self.cache_dir))
        logger.info(f"Cache initialized at {self.cache_dir}")
        
    def get(self, key_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Récupère une réponse du cache."""
        key = self._generate_key(key_data)
        if key in self.cache:
            logger.debug("Cache hit")
            return self.cache[key]
        return None
        
    def set(self, key_data: Dict[str, Any], value: Dict[str, Any]) -> None:
        """Sauvegarde une réponse dans le cache."""
        key = self._generate_key(key_data)
        self.cache[key] = value
        
    def _generate_key(self, data: Dict[str, Any]) -> str:
        """Génère une clé unique basée sur les données."""
        # On trie les clés pour garantir la cohérence
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        
    def clear(self):
        """Vide le cache."""
        self.cache.clear()
        
    def close(self):
        """Ferme le cache."""
        self.cache.close()
