#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Le script CLI pour créer un nouveau benchmark."""

import argparse
import json
import datetime
from typing import Dict, List, Any

from tree_evaluator.tree_generator import generate_tree
from tree_evaluator.text_converter import convert_tree_to_text
from tree_evaluator.question_generator import generate_questions

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
    parser.add_argument("--shuffle", action="store_true", help="Mélanger l'ordre des personnes dans la description.")
    parser.add_argument("--root-couples", type=int, default=1, help="Nombre de couples racines (plusieurs arbres).")
    parser.add_argument("--language", type=str, default="fr", choices=["fr", "en"], help="Langue du benchmark (fr ou en).")
    parser.add_argument("--enigma-percentage", type=int, default=10, help="Pourcentage de questions énigmes (défaut: 10%%)")

    args = parser.parse_args()

    print(f"Génération de l'arbre avec {args.people} personnes, profondeur {args.depth}, {args.root_couples} couple(s) racine(s), langue: {args.language}...")
    tree = generate_tree(
        total_people=args.people,
        max_depth=args.depth,
        max_children_per_person=args.max_children,
        seed=args.seed,
        num_root_couples=args.root_couples,
        language=args.language
    )

    print("Conversion de l'arbre en texte...")
    description = convert_tree_to_text(tree, shuffle=args.shuffle, language=args.language)

    print(f"Génération de {args.questions} questions (dont {args.enigma_percentage}% d'énigmes)...")
    questions = generate_questions(tree, args.questions, language=args.language, enigma_percentage=args.enigma_percentage)

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
            "tree_depth": args.depth,
            "max_children_per_person": args.max_children,
            "seed": args.seed,
            "language": args.language,
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

    print("Terminé !")

if __name__ == "__main__":
    main()
