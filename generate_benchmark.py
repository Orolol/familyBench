#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Le script CLI pour créer un nouveau benchmark."""

import argparse
import json
import datetime
import logging
from typing import Dict, List, Any

from tree_evaluator.tree_generator import generate_tree, actual_depth
from tree_evaluator.text_converter import convert_tree_to_text
from tree_evaluator.question_generator import generate_questions, VALID_DIFFICULTIES
from tree_evaluator.versioning import benchmark_fingerprint, GENERATOR_VERSION

def generate_markdown_output(description: str, questions: List[Dict[str, Any]], language: str = "fr") -> str:
    """Génère le contenu du fichier Markdown pour le LLM."""
    
    md_parts = []
    
    # 1. Le pré-prompt
    if language == "en":
        md_parts.append("# Relational Reasoning Evaluation Exercise")
        md_parts.append("## Instructions")
        md_parts.append("You are an expert text analysis assistant. Your task is to answer a series of questions based on the family description provided below.")
        md_parts.append("Read the family description carefully, then answer each question as accurately as possible.")
        md_parts.append("## Response Format")
        md_parts.append("Please provide your answers as a JSON array containing a list of strings. Each string should correspond to the answer for the corresponding question. Respect the order of questions.")
        md_parts.append("")
        md_parts.append("**IMPORTANT**: Your response must be ONLY the JSON array, without any text before or after.")
        md_parts.append("")
        md_parts.append("Expected format:")
        md_parts.append("```json")
        md_parts.append("[")
        md_parts.append("  \"Answer to question 1\",")
        md_parts.append("  \"Answer to question 2\",")
        md_parts.append("  \"Answer to question 3\"")
        md_parts.append("]")
        md_parts.append("```")
        md_parts.append("")
        md_parts.append("Important rules:")
        md_parts.append("- For lists of names, separate them with commas without spaces (e.g., \"Mary,Paul,Sophie\")")
        md_parts.append("- If no one matches, answer \"None\"")
        md_parts.append("- For numbers, respond with the digit only (e.g., \"3\")")
    else:
        md_parts.append("# Exercice d'évaluation de raisonnement relationnel")
        md_parts.append("## Instructions")
        md_parts.append("Vous êtes un assistant expert en analyse de texte. Votre tâche est de répondre à une série de questions basées sur la description d'une famille fournie ci-dessous.")
        md_parts.append("Lisez attentivement la description de la famille, puis répondez à chaque question de la manière la plus précise possible.")
        md_parts.append("## Format de réponse")
        md_parts.append("Veuillez fournir vos réponses sous la forme d'un tableau JSON contenant une liste de chaînes de caractères. Chaque chaîne de caractères doit correspondre à la réponse pour la question correspondante. Respectez l'ordre des questions.")
        md_parts.append("")
        md_parts.append("**IMPORTANT**: Votre réponse doit être UNIQUEMENT le tableau JSON, sans aucun texte avant ou après.")
        md_parts.append("")
        md_parts.append("Format attendu:")
        md_parts.append("```json")
        md_parts.append("[")
        md_parts.append("  \"Réponse à la question 1\",")
        md_parts.append("  \"Réponse à la question 2\",")
        md_parts.append("  \"Réponse à la question 3\"")
        md_parts.append("]")
        md_parts.append("```")
        md_parts.append("")
        md_parts.append("Règles importantes:")
        md_parts.append("- Pour les listes de noms, séparez-les par des virgules sans espaces (ex: \"Marie,Paul,Sophie\")")
        md_parts.append("- Si aucune personne ne correspond, répondez \"Aucun\"")
        md_parts.append("- Pour les nombres, répondez avec le chiffre uniquement (ex: \"3\")")
    
    # 2. La description de l'arbre
    if language == "en":
        md_parts.append("## Family Description")
    else:
        md_parts.append("## Description de la famille")
    md_parts.append(description)
    
    # 3. La liste des questions
    md_parts.append("## Questions")
    for q in questions:
        md_parts.append(f"{q['id']}. {q['question']}")
        
    return "\n\n".join(md_parts)

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Génère un benchmark d'évaluation LLM basé sur un arbre généalogique.")
    parser.add_argument("--depth", type=int, default=3, help="Profondeur maximale de l'arbre.")
    parser.add_argument("--people", type=int, default=20, help="Nombre total de personnes à générer.")
    parser.add_argument("--questions", type=int, default=50, help="Nombre de questions à générer.")
    parser.add_argument("--output", type=str, default="benchmark.json", help="Fichier de sortie pour le benchmark JSON.")
    parser.add_argument("--md-output", type=str, help="Fichier de sortie optionnel pour le prompt Markdown.")
    parser.add_argument("--seed", type=int, help="Graine pour la reproductibilité.")
    parser.add_argument("--max-children", type=int, default=3, help="Nombre maximum d'enfants par personne.")
    parser.add_argument("--no-shuffle", dest="shuffle", action="store_false",
                        help="Ne pas mélanger la description (par défaut elle est mélangée, de façon seedée ; l'ordre trié révèle la génération).")
    parser.add_argument("--relations", type=str, default="parents", choices=["parents", "children", "both"],
                        help="Phrases de lien écrites dans la description : parents (défaut, 'X est l'enfant de A et B'), children ('A a N enfants'), both (redondant, plus facile).")
    parser.add_argument("--max-answer-names", type=int, default=10,
                        help="Au-delà de ce nombre de prénoms, la question devient un dénombrement (0 = désactivé, défaut 10).")
    parser.add_argument("--anonymize-percentage", type=int, default=50,
                        help="Part des questions (0-100) dont les prénoms sont remplacés par une description par attributs (défaut 50).")
    parser.add_argument("--root-couples", type=int, default=1, help="Nombre de couples racines (plusieurs arbres).")
    parser.add_argument("--language", type=str, default="fr", choices=["fr", "en"], help="Langue du benchmark (fr ou en).")
    parser.add_argument("--visualize", action="store_true", help="Générer une visualisation de l'arbre (PNG).")
    parser.add_argument("--enigma-percentage", type=int, default=10, help="Pourcentage de questions énigmes (défaut: 10%%). Ignoré si --difficulty est différent de 'all'.")
    parser.add_argument(
        "--difficulty",
        type=str,
        default="all",
        choices=sorted(VALID_DIFFICULTIES),
        help="Filtre les questions par difficulté: easy, medium, hard, enigma (uniquement énigmes), expert (hard + énigmes c4/5/6) ou all (défaut, mix pondéré par --enigma-percentage).",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    print(f"Génération de l'arbre avec {args.people} personnes, profondeur {args.depth}, {args.root_couples} couple(s) racine(s), langue: {args.language}...")
    tree = generate_tree(
        total_people=args.people,
        max_depth=args.depth,
        max_children_per_person=args.max_children,
        seed=args.seed,
        num_root_couples=args.root_couples,
        language=args.language
    )

    depth_actual = actual_depth(tree)
    if depth_actual < args.depth:
        print(f"Attention : profondeur demandée {args.depth}, profondeur obtenue {depth_actual} "
              f"(augmentez --people ou réduisez --max-children / --root-couples).")

    print("Conversion de l'arbre en texte...")
    description = convert_tree_to_text(tree, shuffle=args.shuffle, language=args.language,
                                       relations=args.relations, seed=args.seed)

    if args.difficulty == "all":
        print(f"Génération de {args.questions} questions (dont {args.enigma_percentage}% d'énigmes)...")
    else:
        print(f"Génération de {args.questions} questions (difficulté: {args.difficulty})...")
    questions = generate_questions(
        tree,
        args.questions,
        language=args.language,
        enigma_percentage=args.enigma_percentage,
        difficulty=args.difficulty,
        max_answer_names=args.max_answer_names,
        anonymize_percentage=args.anonymize_percentage,
    )

    if args.language == "en":
        prompt_template = "You are an assistant who must answer questions about a family. Here is the family description. Respond only with the name or list of names requested."
    else:
        prompt_template = "Tu es un assistant qui doit répondre à des questions sur une famille. Voici la description de la famille. Réponds uniquement avec le nom ou la liste de noms demandée."
    
    benchmark = {
        "tree_description": description,
        "prompt_template": prompt_template,
        "questions": questions,
        "metadata": {
            "total_people": args.people,
            "people_in_tree": len(tree),
            "tree_depth": args.depth,
            "tree_depth_actual": depth_actual,
            "max_children_per_person": args.max_children,
            "root_couples": args.root_couples,
            "seed": args.seed,
            "language": args.language,
            "difficulty": args.difficulty,
            "enigma_percentage": args.enigma_percentage,
            "shuffle": args.shuffle,
            "relations": args.relations,
            "max_answer_names": args.max_answer_names,
            "anonymize_percentage": args.anonymize_percentage,
            "questions_requested": args.questions,
            "questions_generated": len(questions),
            "generator_version": GENERATOR_VERSION,
            "benchmark_fingerprint": benchmark_fingerprint({
                "people": args.people,
                "depth": args.depth,
                "questions": args.questions,
                "seed": args.seed,
                "language": args.language,
                "max_children": args.max_children,
                "root_couples": args.root_couples,
                "enigma_percentage": args.enigma_percentage,
                "difficulty": args.difficulty,
                "shuffle": args.shuffle,
                "relations": args.relations,
                "max_answer_names": args.max_answer_names,
                "anonymize_percentage": args.anonymize_percentage,
            }),
            "generation_timestamp": datetime.datetime.now().isoformat(),
        }
    }

    print(f"Sauvegarde du benchmark dans {args.output}...")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=4)

    if args.md_output:
        print(f"Génération du fichier Markdown dans {args.md_output}...")
        markdown_content = generate_markdown_output(description, questions, language=args.language)
        with open(args.md_output, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    if args.visualize:
        from tree_evaluator.visualizer import visualize_tree  # import paresseux : graphviz optionnel
        print("Génération de la visualisation...")
        viz_output = args.output.rsplit('.', 1)[0]
        visualize_tree(tree, viz_output)

    print("Terminé !")

if __name__ == "__main__":
    main()
