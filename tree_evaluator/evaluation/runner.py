"""Module pour exécuter les benchmarks d'évaluation."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable

import aiohttp

from tree_evaluator.tree_generator import generate_tree
from tree_evaluator.text_converter import convert_tree_to_text
from tree_evaluator.question_generator import generate_questions
from .model_evaluator import ModelEvaluator
from .result import EvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkRun:
    """Résultat complet d'un run de benchmark."""
    results: List[EvaluationResult]
    tree_description: str
    system_prompt: str
    questions: List[Dict[str, Any]]


async def run_benchmark_evaluation(
    model: ModelEvaluator,
    benchmark_config: Dict[str, Any],
    timeout: int = 60,
    batch_size: int = 1,
    max_concurrent: int = 10,
    on_question_done: Optional[Callable[[EvaluationResult], None]] = None,
    on_batch_done: Optional[Callable[[List[EvaluationResult]], None]] = None,
) -> BenchmarkRun:
    """Exécute l'évaluation d'un benchmark complet.

    Args:
        max_concurrent: nombre max de requêtes simultanées (défaut 10).
        on_question_done: callback appelé après chaque question (mode single).
        on_batch_done: callback appelé après chaque batch.
    """

    # Générer le benchmark
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
    difficulty = benchmark_config.get('difficulty', 'all')
    questions = generate_questions(
        tree, benchmark_config['questions'],
        language=language, enigma_percentage=enigma_percentage,
        difficulty=difficulty,
    )

    system_prompt = model.prompt_builder.get_system_prompt(language, batch_size > 1)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _limited_evaluate_question(question):
        async with semaphore:
            return await model.evaluate_question(
                tree_description, question, session, timeout, language
            )

    async def _limited_evaluate_batch(batch):
        async with semaphore:
            return await model.evaluate_questions_batch(
                tree_description, batch, session, timeout, language
            )

    # Wrapper pour notifier la progression au fur et à mesure
    async def _eval_question_with_callback(question):
        result = await _limited_evaluate_question(question)
        if on_question_done:
            on_question_done(result)
        return result

    async def _eval_batch_with_callback(batch):
        batch_results = await _limited_evaluate_batch(batch)
        if on_batch_done:
            on_batch_done(batch_results)
        return batch_results

    # Créer une session HTTP
    async with aiohttp.ClientSession() as session:
        results = []

        if batch_size > 1:
            if model.request_delay_ms > 0:
                # Traitement séquentiel des batches avec délai
                for i in range(0, len(questions), batch_size):
                    batch = questions[i:i + batch_size]
                    batch_results = await _limited_evaluate_batch(batch)
                    results.extend(batch_results)

                    if on_batch_done:
                        on_batch_done(batch_results)

                    if i + batch_size < len(questions):
                        delay_seconds = model.request_delay_ms / 1000.0
                        await asyncio.sleep(delay_seconds)
            else:
                # Traitement parallèle des batches (limité par semaphore)
                batches = [
                    questions[i:i + batch_size]
                    for i in range(0, len(questions), batch_size)
                ]
                batch_tasks = [_eval_batch_with_callback(b) for b in batches]
                batch_results_list = await asyncio.gather(*batch_tasks)
                for batch_results in batch_results_list:
                    results.extend(batch_results)
        else:
            if model.request_delay_ms > 0:
                # Évaluation séquentielle avec délai
                for i, question in enumerate(questions):
                    result = await model.evaluate_question(
                        tree_description, question, session, timeout, language
                    )
                    results.append(result)

                    if on_question_done:
                        on_question_done(result)

                    if i < len(questions) - 1:
                        delay_seconds = model.request_delay_ms / 1000.0
                        await asyncio.sleep(delay_seconds)
            else:
                # Évaluation parallèle (limitée par semaphore)
                tasks = [_eval_question_with_callback(q) for q in questions]
                results = await asyncio.gather(*tasks)

    # Ajouter le nom du benchmark
    for result in results:
        result.benchmark_name = benchmark_config['name']

    return BenchmarkRun(
        results=list(results),
        tree_description=tree_description,
        system_prompt=system_prompt,
        questions=questions,
    )
