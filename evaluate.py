#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Script d'évaluation automatique des modèles sur les benchmarks TreeEval."""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import yaml
from dotenv import load_dotenv

from tree_evaluator.evaluation.model_evaluator import ModelEvaluator
from tree_evaluator.evaluation.runner import run_benchmark_evaluation, BenchmarkRun
from tree_evaluator.evaluation.stats import calculate_summary_stats
from tree_evaluator.evaluation.io import save_results_csv, save_results_json
from tree_evaluator.evaluation.display import EvalProgress, print_final_summary, console

load_dotenv()

logger = logging.getLogger(__name__)


def setup_logging(debug: bool, log_file: str = "evaluation_debug.log") -> None:
    """Logging fichier uniquement (rich gère la console), avec rotation.

    INFO par défaut ; --debug active DEBUG (requêtes et réponses complètes,
    très volumineux : chaque requête contient l'arbre entier).
    """
    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(
        log_file, maxBytes=20 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)


def _build_detailed_json(
    model_name: str,
    benchmark_run: BenchmarkRun,
    benchmark_config: Dict,
) -> Dict:
    """Construit le JSON détaillé avec prompt et Q&A pour un run."""
    qa_list = []
    for result in benchmark_run.results:
        # Trouver la question source pour récupérer les métadonnées
        q_meta = next(
            (q for q in benchmark_run.questions if q["id"] == result.question_id),
            {},
        )
        qa_list.append({
            "question_id": result.question_id,
            "question": result.question,
            "question_type": result.question_type,
            "is_enigma": result.is_enigma,
            "enigma_complexity": result.enigma_complexity,
            "expected_answer": result.expected_answer,
            "model_answer": result.model_answer,
            "is_correct": result.is_correct,
            "is_exact_match": result.is_exact_match,
            "partial_match_score": result.partial_match_score,
            "response_time": result.response_time,
            "prompt_tokens": result.prompt_tokens,
            "tokens_used": result.tokens_used,
            "cached_tokens": result.cached_tokens,
            "cost_usd": result.cost_usd,
            "reasoning_tokens": result.reasoning_tokens,
            "no_response": result.no_response,
            "error": result.error,
        })

    return {
        "model": model_name,
        "benchmark": benchmark_config["name"],
        "language": benchmark_config.get("language", "fr"),
        "timestamp": datetime.now().isoformat(),
        "benchmark_fingerprint": benchmark_run.benchmark_fingerprint,
        "generator_version": benchmark_run.generator_version,
        "difficulty": benchmark_run.difficulty,
        "tree_people": benchmark_run.tree_people,
        "tree_depth_requested": benchmark_run.tree_depth_requested,
        "tree_depth_actual": benchmark_run.tree_depth_actual,
        "batch_size": benchmark_run.batch_size,
        "system_prompt": benchmark_run.system_prompt,
        "tree_description": benchmark_run.tree_description,
        "questions_answers": qa_list,
    }


async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Évalue des modèles sur les benchmarks TreeEval"
    )
    parser.add_argument(
        "--config", type=str, default="evaluation_config.yaml",
        help="Fichier de configuration YAML",
    )
    parser.add_argument(
        "--models", type=str, nargs="+",
        help="Liste des modèles à évaluer (override la config)",
    )
    parser.add_argument(
        "--benchmarks", type=str, nargs="+",
        help="Liste des benchmarks à exécuter (override la config)",
    )

    parser.add_argument("--batch-size", type=int, help="Override evaluation.batch_size (questions par requête)")
    parser.add_argument("--runs", type=int, help="Override evaluation.runs_per_benchmark")
    parser.add_argument("--max-concurrent", type=int, help="Override evaluation.max_concurrent_requests")
    parser.add_argument("--output-dir", type=str, help="Override evaluation.output_dir")
    parser.add_argument(
        "--debug", action="store_true",
        help="Active le logging DEBUG (requêtes/réponses complètes) dans evaluation_debug.log",
    )
    args = parser.parse_args()
    setup_logging(args.debug)

    # Charger la configuration
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Créer le dossier de sortie
    if args.output_dir:
        config["evaluation"]["output_dir"] = args.output_dir
    output_dir = Path(config["evaluation"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Filtrer modèles / benchmarks
    models_to_eval = config["models"]
    if args.models:
        models_to_eval = [m for m in config["models"] if m["name"] in args.models]

    benchmarks_to_run = config["benchmarks"]
    if args.benchmarks:
        benchmarks_to_run = [
            b for b in config["benchmarks"] if b["name"] in args.benchmarks
        ]

    if args.batch_size is not None:
        config["evaluation"]["batch_size"] = args.batch_size
    if args.runs is not None:
        config["evaluation"]["runs_per_benchmark"] = args.runs
    if args.max_concurrent is not None:
        config["evaluation"]["max_concurrent_requests"] = args.max_concurrent
    runs_per_benchmark = config["evaluation"].get("runs_per_benchmark", 1)
    max_concurrent = config["evaluation"].get("max_concurrent_requests", 10)
    batch_size = config["evaluation"].get("batch_size", 1)

    # --- Rich progress ---
    progress = EvalProgress(
        models=[m["name"] for m in models_to_eval],
        benchmarks=[b["name"] for b in benchmarks_to_run],
        runs_per_benchmark=runs_per_benchmark,
    )
    progress.start()

    all_results = []
    summary_stats = {}
    detailed_runs: List[Dict] = []
    benchmark_meta: Dict[str, Dict] = {}

    try:
        for model_config in models_to_eval:
            model = ModelEvaluator(model_config)
            model_results = []
            progress.begin_model(model_config["name"])

            for benchmark in benchmarks_to_run:
                runs = runs_per_benchmark
                for run_idx in range(runs):
                    total_q = benchmark["questions"]
                    progress.begin_run(
                        benchmark["name"], run_idx + 1, total_q
                    )

                    benchmark_run = await run_benchmark_evaluation(
                        model,
                        benchmark,
                        config["evaluation"].get("timeout", 60),
                        batch_size,
                        max_concurrent=max_concurrent,
                        on_question_done=progress.update_question,
                        on_batch_done=progress.update_questions_batch,
                    )

                    results = benchmark_run.results
                    model_results.extend(results)

                    stats = calculate_summary_stats(results)
                    progress.end_run(
                        stats["accuracy"], stats["avg_response_time"]
                    )

                    benchmark_meta[benchmark["name"]] = {
                        "fingerprint": benchmark_run.benchmark_fingerprint,
                        "generator_version": benchmark_run.generator_version,
                        "difficulty": benchmark_run.difficulty,
                        "people": benchmark_run.tree_people,
                        "depth_requested": benchmark_run.tree_depth_requested,
                        "depth_actual": benchmark_run.tree_depth_actual,
                        "questions": len(benchmark_run.questions),
                        "batch_size": benchmark_run.batch_size,
                    }
                    # Collecter le JSON détaillé
                    detailed_runs.append(
                        _build_detailed_json(
                            model_config["name"], benchmark_run, benchmark
                        )
                    )

            all_results.extend(model_results)
            model_stats = calculate_summary_stats(model_results)
            summary_stats[model_config["name"]] = model_stats

    finally:
        progress.stop()

    # --- Sauvegarde des résultats ---
    output_paths: Dict[str, str] = {}

    if "csv" in config["evaluation"]["output_formats"]:
        csv_path = output_dir / f"results_{timestamp}.csv"
        save_results_csv(all_results, csv_path)
        output_paths["CSV"] = str(csv_path)

    if "json" in config["evaluation"]["output_formats"]:
        json_path = output_dir / f"results_{timestamp}.json"
        save_results_json(all_results, json_path)
        output_paths["JSON (résultats)"] = str(json_path)

    # JSON détaillé avec prompts + Q&A
    detailed_path = output_dir / f"detailed_{timestamp}.json"
    with open(detailed_path, "w", encoding="utf-8") as f:
        json.dump(detailed_runs, f, ensure_ascii=False, indent=2)
    output_paths["JSON (détaillé prompt+Q&A)"] = str(detailed_path)

    # Résumé
    summary_path = output_dir / f"summary_{timestamp}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "config": args.config,
                "models_evaluated": [m["name"] for m in models_to_eval],
                "benchmarks_run": [b["name"] for b in benchmarks_to_run],
                "benchmarks": benchmark_meta,
                "summary_stats": summary_stats,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    output_paths["Résumé"] = str(summary_path)

    # Affichage final
    print_final_summary(summary_stats, output_paths)


if __name__ == "__main__":
    asyncio.run(main())
