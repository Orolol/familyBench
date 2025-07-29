"""Fonctions pour calculer les statistiques d'évaluation."""

from typing import Dict, List, Any
from .result import EvaluationResult


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
    errors = sum(1 for r in results if r.error)
    no_responses = sum(1 for r in results if r.no_response)
    total_reasoning_tokens = sum(r.reasoning_tokens for r in results)
    questions_with_reasoning = sum(1 for r in results if r.reasoning_tokens > 0)
    
    # Statistiques pour les énigmes
    enigma_results = [r for r in results if r.is_enigma]
    normal_results = [r for r in results if not r.is_enigma]
    
    enigma_stats = {}
    if enigma_results:
        enigma_total = len(enigma_results)
        enigma_correct = sum(1 for r in enigma_results if r.is_correct)
        enigma_stats = {
            'total': enigma_total,
            'correct': enigma_correct,
            'accuracy': enigma_correct / enigma_total,
            'by_complexity': {}
        }
        
        # Statistiques par niveau de complexité
        for complexity in [1, 2, 3]:
            complex_results = [r for r in enigma_results if r.enigma_complexity == complexity]
            if complex_results:
                complex_correct = sum(1 for r in complex_results if r.is_correct)
                enigma_stats['by_complexity'][complexity] = {
                    'total': len(complex_results),
                    'correct': complex_correct,
                    'accuracy': complex_correct / len(complex_results)
                }
    
    normal_stats = {}
    if normal_results:
        normal_total = len(normal_results)
        normal_correct = sum(1 for r in normal_results if r.is_correct)
        normal_stats = {
            'total': normal_total,
            'correct': normal_correct,
            'accuracy': normal_correct / normal_total
        }
    
    return {
        'total_questions': total,
        'correct_answers': correct,
        'accuracy': correct / total,
        'exact_matches': exact_matches,
        'exact_match_rate': exact_matches / total,
        'avg_partial_score': avg_partial_score,
        'avg_response_time': avg_response_time,
        'total_tokens': total_tokens,
        'errors': errors,
        'error_rate': errors / total,
        'no_responses': no_responses,
        'no_response_rate': no_responses / total if total > 0 else 0,
        'total_reasoning_tokens': total_reasoning_tokens,
        'questions_with_reasoning': questions_with_reasoning,
        'avg_reasoning_tokens': total_reasoning_tokens / questions_with_reasoning if questions_with_reasoning > 0 else 0,
        'enigma_stats': enigma_stats,
        'normal_stats': normal_stats
    }