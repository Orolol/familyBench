"""Module pour exécuter les benchmarks d'évaluation."""

import asyncio
import logging
from typing import Dict, List, Any

import aiohttp

from tree_evaluator.tree_generator import generate_tree
from tree_evaluator.text_converter import convert_tree_to_text
from tree_evaluator.question_generator import generate_questions
from .model_evaluator import ModelEvaluator
from .result import EvaluationResult

logger = logging.getLogger(__name__)


async def run_benchmark_evaluation(model: ModelEvaluator,
                                 benchmark_config: Dict[str, Any],
                                 timeout: int = 60,
                                 batch_size: int = 1) -> List[EvaluationResult]:
    """Exécute l'évaluation d'un benchmark complet."""
    
    # Générer le benchmark
    print(f"  Génération du benchmark {benchmark_config['name']}...")
    language = benchmark_config.get('language', 'fr')
    tree = generate_tree(
        total_people=benchmark_config['people'],
        max_depth=benchmark_config['depth'],
        max_children_per_person=benchmark_config.get('max_children', 3),
        seed=benchmark_config.get('seed'),
        num_root_couples=benchmark_config.get('root_couples', 1),
        language=language
    )
    
    tree_description = convert_tree_to_text(tree, shuffle=False, language=language)
    enigma_percentage = benchmark_config.get('enigma_percentage', 10)
    questions = generate_questions(tree, benchmark_config['questions'], language=language, enigma_percentage=enigma_percentage)
    
    num_enigmas = sum(1 for q in questions if q.get('type') == 'enigme')
    print(f"  Évaluation de {len(questions)} questions (dont {num_enigmas} énigmes)...")
    if batch_size > 1:
        print(f"  Utilisation du batching (taille: {batch_size})")
    
    # Créer une session HTTP
    async with aiohttp.ClientSession() as session:
        results = []
        
        if batch_size > 1:
            # Évaluation par batch
            for i in range(0, len(questions), batch_size):
                batch = questions[i:i + batch_size]
                batch_results = await model.evaluate_questions_batch(
                    tree_description, batch, session, timeout, language
                )
                results.extend(batch_results)
                
                # Afficher la progression
                if len(questions) > 10:
                    progress = min(i + batch_size, len(questions))
                    print(f"    Progress: {progress}/{len(questions)} questions")
        else:
            # Évaluation individuelle (comportement original)
            tasks = []
            for question in questions:
                task = model.evaluate_question(tree_description, question, session, timeout, language)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
    
    # Ajouter le nom du benchmark
    for result in results:
        result.benchmark_name = benchmark_config['name']
    
    return results