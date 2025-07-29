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
from tree_evaluator.evaluation.runner import run_benchmark_evaluation
from tree_evaluator.evaluation.stats import calculate_summary_stats
from tree_evaluator.evaluation.io import save_results_csv, save_results_json

load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluation_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Évalue des modèles sur les benchmarks TreeEval")
    parser.add_argument("--config", type=str, default="evaluation_config.yaml",
                      help="Fichier de configuration YAML")
    parser.add_argument("--models", type=str, nargs='+',
                      help="Liste des modèles à évaluer (override la config)")
    parser.add_argument("--benchmarks", type=str, nargs='+',
                      help="Liste des benchmarks à exécuter (override la config)")
    
    args = parser.parse_args()
    
    # Charger la configuration
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Créer le dossier de sortie
    output_dir = Path(config['evaluation']['output_dir'])
    output_dir.mkdir(exist_ok=True)
    
    # Timestamp pour les fichiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Filtrer les modèles et benchmarks si spécifiés
    models_to_eval = config['models']
    if args.models:
        models_to_eval = [m for m in config['models'] if m['name'] in args.models]
    
    benchmarks_to_run = config['benchmarks']
    if args.benchmarks:
        benchmarks_to_run = [b for b in config['benchmarks'] if b['name'] in args.benchmarks]
    
    # Résultats globaux
    all_results = []
    summary_stats = {}
    
    # Évaluer chaque modèle
    for model_config in models_to_eval:
        print(f"\nÉvaluation du modèle: {model_config['name']}")
        model = ModelEvaluator(model_config)
        model_results = []
        
        # Exécuter chaque benchmark
        for benchmark in benchmarks_to_run:
            print(f"\n  Benchmark: {benchmark['name']}")
            
            # Exécuter plusieurs fois si configuré
            runs = config['evaluation'].get('runs_per_benchmark', 1)
            for run in range(runs):
                if runs > 1:
                    print(f"    Run {run + 1}/{runs}")
                
                results = await run_benchmark_evaluation(
                    model, 
                    benchmark,
                    config['evaluation'].get('timeout', 60),
                    config['evaluation'].get('batch_size', 1)
                )
                
                model_results.extend(results)
                
                # Statistiques pour ce run
                stats = calculate_summary_stats(results)
                print(f"    Accuracy: {stats['accuracy']:.2%}")
                print(f"    Avg response time: {stats['avg_response_time']:.2f}s")
        
        all_results.extend(model_results)
        
        # Statistiques par modèle
        model_stats = calculate_summary_stats(model_results)
        summary_stats[model_config['name']] = model_stats
        
        print(f"\n  Résumé pour {model_config['name']}:")
        print(f"    Total questions: {model_stats['total_questions']}")
        print(f"    Accuracy globale: {model_stats['accuracy']:.2%}")
        print(f"    Exact match rate: {model_stats['exact_match_rate']:.2%}")
        print(f"    Non-réponses: {model_stats['no_responses']} ({model_stats['no_response_rate']:.2%})")
        print(f"    Temps moyen: {model_stats['avg_response_time']:.2f}s")
        print(f"    Tokens utilisés: {model_stats['total_tokens']}")
        if model_stats['total_reasoning_tokens'] > 0:
            print(f"    Reasoning tokens: {model_stats['total_reasoning_tokens']} (avg: {model_stats['avg_reasoning_tokens']:.0f})")
        
        # Statistiques des énigmes
        if 'enigma_stats' in model_stats and model_stats['enigma_stats']:
            enigma_stats = model_stats['enigma_stats']
            print(f"\n    Statistiques énigmes:")
            print(f"      Total: {enigma_stats['total']} questions")
            print(f"      Accuracy: {enigma_stats['accuracy']:.2%}")
            if enigma_stats.get('by_complexity'):
                for complexity, stats in enigma_stats['by_complexity'].items():
                    print(f"      Complexité {complexity}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")
        
        if 'normal_stats' in model_stats and model_stats['normal_stats']:
            normal_stats = model_stats['normal_stats']
            print(f"\n    Questions normales:")
            print(f"      Total: {normal_stats['total']} questions")
            print(f"      Accuracy: {normal_stats['accuracy']:.2%}")
    
    # Sauvegarder les résultats
    print(f"\nSauvegarde des résultats dans {output_dir}...")
    
    if 'csv' in config['evaluation']['output_formats']:
        csv_path = output_dir / f"results_{timestamp}.csv"
        save_results_csv(all_results, csv_path)
        print(f"  CSV: {csv_path}")
    
    if 'json' in config['evaluation']['output_formats']:
        json_path = output_dir / f"results_{timestamp}.json"
        save_results_json(all_results, json_path)
        print(f"  JSON: {json_path}")
    
    # Sauvegarder le résumé
    summary_path = output_dir / f"summary_{timestamp}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'config': args.config,
            'models_evaluated': [m['name'] for m in models_to_eval],
            'benchmarks_run': [b['name'] for b in benchmarks_to_run],
            'summary_stats': summary_stats
        }, f, ensure_ascii=False, indent=2)
    print(f"  Résumé: {summary_path}")
    
    print("\nÉvaluation terminée!")

if __name__ == "__main__":
    asyncio.run(main())