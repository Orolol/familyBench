"""Classe pour stocker les résultats d'évaluation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EvaluationResult:
    """Résultat d'une évaluation individuelle."""
    model_name: str
    benchmark_name: str
    question_id: int
    question: str
    expected_answer: str
    model_answer: str
    is_correct: bool
    is_exact_match: bool
    partial_match_score: float
    response_time: float
    tokens_used: int
    error: Optional[str] = None
    no_response: bool = False
    reasoning_tokens: int = 0
    prompt_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: Optional[float] = None
    reasoning_text: Optional[str] = None
    question_type: Optional[str] = None
    # Tier de difficulté de la question (easy / medium / hard / enigma)
    difficulty: Optional[str] = None
    # Nombre de prénoms de la réponse qui n'existent pas dans l'arbre
    hallucinated_names: int = 0
    is_enigma: bool = False
    enigma_complexity: Optional[int] = None
    # Taille du batch dans lequel la question a été posée (1 = une requête par question)
    batch_size: int = 1
    # finish_reason renvoyé par l'API ("stop", "length" = coupé par max_tokens...)
    finish_reason: Optional[str] = None
    # Fournisseur réel (OpenRouter renvoie `provider`) : utile pour le cache de prompt
    provider: Optional[str] = None
    # Niveau de thinking de l'entrée du leaderboard (paire modèle + niveau)
    thinking_level: Optional[str] = None
