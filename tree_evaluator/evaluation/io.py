"""Module pour la sauvegarde des résultats d'évaluation."""

import csv
import json
from pathlib import Path
from typing import List
from dataclasses import asdict

from .result import EvaluationResult


def save_results_csv(results: List[EvaluationResult], output_path: Path):
    """Sauvegarde les résultats au format CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'model_name', 'benchmark_name', 'question_id', 'question',
            'expected_answer', 'model_answer', 'is_correct', 'is_exact_match',
            'partial_match_score', 'response_time', 'tokens_used', 'error', 
            'no_response', 'reasoning_tokens', 'question_type', 'is_enigma', 'enigma_complexity'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            row_data = asdict(result)
            # Exclure reasoning_text du CSV
            row_data.pop('reasoning_text', None)
            writer.writerow(row_data)


def save_results_json(results: List[EvaluationResult], output_path: Path):
    """Sauvegarde les résultats au format JSON."""
    data = [asdict(r) for r in results]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)