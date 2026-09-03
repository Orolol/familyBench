"""Fonctions pour calculer les statistiques d'évaluation."""

from typing import Dict, List, Any, Optional
from .result import EvaluationResult


def _accuracy_block(results: List[EvaluationResult]) -> Dict[str, Any]:
    total = len(results)
    correct = sum(1 for r in results if r.is_correct)
    return {
        'total': total,
        'correct': correct,
        'accuracy': correct / total if total else 0.0,
    }


def _group_stats(results: List[EvaluationResult], key) -> Dict[str, Dict[str, Any]]:
    """Statistiques d'accuracy groupées par une clé (type, difficulté, ...)."""
    groups: Dict[str, List[EvaluationResult]] = {}
    for r in results:
        k = key(r)
        if k is None:
            continue
        groups.setdefault(str(k), []).append(r)
    return {k: _accuracy_block(v) for k, v in sorted(groups.items())}


def calculate_summary_stats(results: List[EvaluationResult]) -> Dict[str, Any]:
    """Calcule les statistiques résumées."""
    if not results:
        return {}
    
    total = len(results)
    correct = sum(1 for r in results if r.is_correct)
    exact_matches = sum(1 for r in results if r.is_exact_match)
    avg_partial_score = sum(r.partial_match_score for r in results) / total
    avg_response_time = sum(r.response_time for r in results) / total
    total_tokens = sum(r.tokens_used for r in results)
    total_prompt_tokens = sum(r.prompt_tokens for r in results)
    total_completion_tokens = total_tokens  # `tokens_used` is completion tokens
    total_cached_tokens = sum(r.cached_tokens for r in results)
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    total_cost_usd = sum(costs) if costs else None
    avg_cost_usd = (sum(costs) / len(costs)) if costs else None
    errors = sum(1 for r in results if r.error)
    no_responses = sum(1 for r in results if r.no_response)
    total_reasoning_tokens = sum(r.reasoning_tokens for r in results)
    questions_with_reasoning = sum(1 for r in results if r.reasoning_tokens > 0)

    # Hallucinations : réponses (non vides, sans erreur) contenant au moins un
    # prénom absent de l'arbre.
    answered = [r for r in results if not r.error and not r.no_response and r.model_answer]
    answers_with_hallucination = sum(1 for r in answered if r.hallucinated_names > 0)
    total_hallucinated_names = sum(r.hallucinated_names for r in results)
    
    # Statistiques pour les énigmes
    enigma_results = [r for r in results if r.is_enigma]
    normal_results = [r for r in results if not r.is_enigma]
    
    enigma_stats = {}
    if enigma_results:
        enigma_stats = _accuracy_block(enigma_results)
        enigma_stats['by_complexity'] = {}
        complexities = sorted({r.enigma_complexity for r in enigma_results if r.enigma_complexity is not None})
        for complexity in complexities:
            complex_results = [r for r in enigma_results if r.enigma_complexity == complexity]
            enigma_stats['by_complexity'][complexity] = _accuracy_block(complex_results)
    
    normal_stats = _accuracy_block(normal_results) if normal_results else {}
    
    return {
        'total_questions': total,
        'correct_answers': correct,
        'accuracy': correct / total,
        'exact_matches': exact_matches,
        'exact_match_rate': exact_matches / total,
        'avg_partial_score': avg_partial_score,
        'avg_response_time': avg_response_time,
        'total_tokens': total_tokens,
        'total_prompt_tokens': total_prompt_tokens,
        'total_completion_tokens': total_completion_tokens,
        'avg_completion_tokens': total_completion_tokens / total if total > 0 else 0,
        'total_cached_tokens': total_cached_tokens,
        'total_cost_usd': total_cost_usd,
        'avg_cost_usd': avg_cost_usd,
        'errors': errors,
        'error_rate': errors / total,
        'no_responses': no_responses,
        'no_response_rate': no_responses / total if total > 0 else 0,
        'total_reasoning_tokens': total_reasoning_tokens,
        'questions_with_reasoning': questions_with_reasoning,
        'avg_reasoning_tokens': total_reasoning_tokens / questions_with_reasoning if questions_with_reasoning > 0 else 0,
        'hallucination_rate': answers_with_hallucination / len(answered) if answered else 0.0,
        'answers_with_hallucination': answers_with_hallucination,
        'total_hallucinated_names': total_hallucinated_names,
        'by_question_type': _group_stats(results, lambda r: r.question_type),
        'by_difficulty': _group_stats(results, lambda r: r.difficulty),
        'enigma_stats': enigma_stats,
        'normal_stats': normal_stats
    }
