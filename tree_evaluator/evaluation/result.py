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
    reasoning_text: Optional[str] = None
    question_type: Optional[str] = None
    is_enigma: bool = False
    enigma_complexity: Optional[int] = None