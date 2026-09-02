"""Empreinte (fingerprint) des benchmarks pour garantir la comparabilité.

Deux runs ne sont comparables que s'ils ont été générés avec la même version
du générateur, les mêmes fichiers de données (prénoms, professions, couleurs)
et les mêmes paramètres. Cette empreinte est écrite dans les métadonnées des
benchmarks et dans les résumés d'évaluation.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

# À incrémenter à chaque changement qui modifie les arbres ou les questions
# produits pour une seed donnée (algorithme de génération, ordre des tirages
# aléatoires, nouveaux types de questions, échantillonnage...).
GENERATOR_VERSION = "3.1"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_FILES = ["first_names.txt", "professions.txt", "hair_colors.txt", "eye_colors.txt", "hat_colors.txt"]


def data_files_hash(language: str) -> str:
    """Hash SHA-256 (tronqué) du contenu des fichiers de données d'une langue."""
    h = hashlib.sha256()
    for name in DATA_FILES:
        path = DATA_DIR / language / name
        h.update(name.encode("utf-8"))
        h.update(path.read_bytes() if path.exists() else b"<missing>")
    return h.hexdigest()[:12]


def benchmark_fingerprint(params: Dict[str, Any]) -> str:
    """Empreinte d'un benchmark à partir de ses paramètres de génération.

    `params` doit contenir au minimum: people, depth, questions, seed, language.
    Les clés optionnelles (max_children, root_couples, enigma_percentage,
    difficulty) sont incluses si présentes.
    """
    language = params.get("language", "fr")
    payload = {
        "generator_version": GENERATOR_VERSION,
        "data_hash": data_files_hash(language),
        "params": {k: params[k] for k in sorted(params) if params[k] is not None},
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def benchmark_params_from_config(benchmark_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extrait les paramètres pertinents d'une entrée `benchmarks:` du YAML."""
    return {
        "people": benchmark_config["people"],
        "depth": benchmark_config["depth"],
        "questions": benchmark_config["questions"],
        "seed": benchmark_config.get("seed"),
        "language": benchmark_config.get("language", "fr"),
        "max_children": benchmark_config.get("max_children", 3),
        "root_couples": benchmark_config.get("root_couples", 1),
        "enigma_percentage": benchmark_config.get("enigma_percentage", 10),
        "difficulty": benchmark_config.get("difficulty", "all"),
        "shuffle": benchmark_config.get("shuffle", True),
        "relations": benchmark_config.get("relations", "parents"),
        "max_answer_names": benchmark_config.get("max_answer_names", 10),
        "anonymize_percentage": benchmark_config.get("anonymize_percentage", 50),
        "drop_answer_names_above": benchmark_config.get("drop_answer_names_above", 40),
    }
