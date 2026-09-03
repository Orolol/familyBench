import sys
from pathlib import Path

# Rendre le paquet importable quel que soit le répertoire d'exécution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
