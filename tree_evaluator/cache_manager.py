"""Gestionnaire de cache pour les appels API.

Utilise `diskcache` si disponible (cache persistant dans .cache/). Sinon,
bascule sur un cache mémoire non persistant avec un avertissement.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import diskcache  # type: ignore
    HAS_DISKCACHE = True
except ImportError:  # pragma: no cover - dépend de l'environnement
    diskcache = None
    HAS_DISKCACHE = False

logger = logging.getLogger(__name__)


class CacheManager:
    """Gère le cache des réponses API sur le disque."""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.persistent = HAS_DISKCACHE
        if HAS_DISKCACHE:
            self.cache = diskcache.Cache(str(self.cache_dir))
            logger.info(f"Cache initialized at {self.cache_dir}")
        else:
            self.cache = {}
            logger.warning(
                "diskcache is not installed: API responses will only be cached in memory "
                "for this run. Install it with `pip install diskcache` for a persistent cache."
            )
        
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
        if self.persistent:
            self.cache.close()
