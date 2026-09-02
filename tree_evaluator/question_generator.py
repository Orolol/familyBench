"""Générateur de questions principal qui utilise les modules de questions."""

import random
import json
from typing import Dict, List, Any, Iterable, Optional

from tree_evaluator.models import Person


DIFFICULTY_TIERS: Dict[str, set[str]] = {
    "easy": {
        "relation_directe",
        "relation_inverse",
        "recherche_attributs",
        "comptage",
    },
    "medium": {
        "recherche_multi_criteres",
        "relation_complexe",
        "transversale_generation",
        "verticale_ancetre",
        "verticale_feuille",
        "verticale_racine",
        "verticale_descendant",
        "comptage_complexe",
    },
    "hard": {
        "relation_attribut_composee",
        "multihop",
        "conditional",
        "negation",
        "comparative",
        "relational_path",
        "recherche_inversee_complexe",
        "verticale_descendant_critere",
        "verticale_racine_critere",
        "demi_fratrie",
        "beaux_parents",
    },
    "enigma": {"enigme"},
}
EXPERT_ENIGMA_COMPLEXITIES = {4, 5, 6, 7, 8, 9}
EXPERT_ENIGMA_HIGH_COMPLEXITIES = {7, 8, 9}
# Réponses de plus de N prénoms converties en dénombrement (0 = désactivé)
DEFAULT_MAX_ANSWER_NAMES = 10
# Questions écartées au-delà de N prénoms : ce sont des recensements (0 = désactivé)
DEFAULT_DROP_ANSWER_NAMES_ABOVE = 40
# Part des questions dont les prénoms sont remplacés par une description par attributs
DEFAULT_ANONYMIZE_PERCENTAGE = 50
EXPERT_HARD_EXCLUDED_TYPES = {"relation_attribut_composee", "relational_path"}
EXPERT_MIN_HIGH_ENIGMA_RATIO = 0.4
VALID_DIFFICULTIES = {"all", "expert", *DIFFICULTY_TIERS.keys()}

# Import de tous les modules de questions
from tree_evaluator.questions.direct_relations import (
    generate_direct_relation_questions,
    generate_inverse_relation_questions
)
from tree_evaluator.questions.attribute_search import (
    generate_attribute_search_questions,
    generate_multi_criteria_questions
)
from tree_evaluator.questions.counting import generate_counting_questions
from tree_evaluator.questions.complex_relations import (
    generate_complex_relation_questions,
    generate_half_family_questions,
)
from tree_evaluator.questions.transversal import (
    generate_transversal_questions,
    generate_vertical_questions
)
from tree_evaluator.questions.advanced import (
    generate_compound_relation_questions,
    generate_multihop_questions,
    generate_conditional_questions,
    generate_negation_questions,
    generate_comparative_questions,
    generate_relational_path_questions
)
from tree_evaluator.questions.enigma import generate_enigma_questions
from tree_evaluator.questions.rewrite import (
    anonymize_names, convert_long_answers_to_counts, answer_format, fix_english_articles,
    drop_census_questions,
)


def _dedupe(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list({json.dumps(q, sort_keys=True): q for q in questions}.values())


_TYPE_TO_DIFFICULTY: Dict[str, str] = {
    qtype: tier for tier, types in DIFFICULTY_TIERS.items() for qtype in types
}


def difficulty_for_type(question_type: str) -> str | None:
    """Tier de difficulté (easy/medium/hard/enigma) d'un type de question."""
    return _TYPE_TO_DIFFICULTY.get(question_type)


def _stamp_difficulty(questions: List[Dict[str, Any]]) -> None:
    for q in questions:
        q["difficulty"] = difficulty_for_type(q["type"])


def _stratified_sample(questions: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    """Tire `n` questions en équilibrant les types.

    Les questions sont regroupées par type, chaque groupe est mélangé, puis on
    pioche en tourniquet (round-robin) sur les types dans un ordre aléatoire.
    Un type épuisé est simplement ignoré, ce qui remplit automatiquement avec
    les autres types. Sans cela, les types qui produisent le plus de candidats
    (relations complexes, attributs composés) écrasaient tous les autres.
    """
    if n <= 0 or not questions:
        return []
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions:
        groups.setdefault(q["type"], []).append(q)
    order = sorted(groups)  # ordre déterministe avant mélange
    random.shuffle(order)
    for qtype in order:
        random.shuffle(groups[qtype])

    selected: List[Dict[str, Any]] = []
    while len(selected) < n:
        progressed = False
        for qtype in order:
            bucket = groups[qtype]
            if bucket:
                selected.append(bucket.pop())
                progressed = True
                if len(selected) == n:
                    break
        if not progressed:
            break
    return selected


def generate_questions(
    people: Dict[str, Person],
    num_questions: int,
    language: str = "fr",
    enigma_percentage: int = 10,
    difficulty: str = "all",
    max_answer_names: int = DEFAULT_MAX_ANSWER_NAMES,
    anonymize_percentage: int = DEFAULT_ANONYMIZE_PERCENTAGE,
    drop_answer_names_above: int = DEFAULT_DROP_ANSWER_NAMES_ABOVE,
    exclude_types: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    """Génère une liste de questions de différents types.

    Args:
        difficulty: "all" (mix par défaut pondéré par enigma_percentage),
            "easy", "medium", "hard" (uniquement questions normales du tier),
            "enigma" (uniquement des énigmes),
            ou "expert" (questions normales 'hard' + énigmes de complexité 4 à 9).
        max_answer_names: au-delà de ce nombre de prénoms, la question devient
            un dénombrement ("Combien de personnes répondent à ..."). 0 = désactivé.
        anonymize_percentage: part (0-100) des questions dont les prénoms cités
            sont remplacés par une description par attributs.
        drop_answer_names_above: les questions dont la réponse dépasse ce nombre
            de prénoms sont écartées avant tirage (recensements). 0 = désactivé.
        exclude_types: types de questions à écarter (ex. relational_path).
    """
    excluded = set(exclude_types or ())
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"difficulty must be one of {sorted(VALID_DIFFICULTIES)}, got {difficulty!r}"
        )

    normal_questions: List[Dict[str, Any]] = []
    normal_questions.extend(generate_direct_relation_questions(people, language))
    normal_questions.extend(generate_inverse_relation_questions(people, language))
    normal_questions.extend(generate_attribute_search_questions(people, language))
    normal_questions.extend(generate_multi_criteria_questions(people, language))
    normal_questions.extend(generate_counting_questions(people, language))
    normal_questions.extend(generate_complex_relation_questions(people, language))
    normal_questions.extend(generate_half_family_questions(people, language))
    normal_questions.extend(generate_transversal_questions(people, language))
    normal_questions.extend(generate_vertical_questions(people, language))
    normal_questions.extend(generate_compound_relation_questions(people, language))
    normal_questions.extend(generate_multihop_questions(people, language))
    normal_questions.extend(generate_conditional_questions(people, language))
    normal_questions.extend(generate_negation_questions(people, language))
    normal_questions.extend(generate_comparative_questions(people, language))
    normal_questions.extend(generate_relational_path_questions(people, language))

    unique_normal_questions = drop_census_questions(
        _dedupe(normal_questions), people, language, drop_answer_names_above
    )
    unique_normal_questions = [q for q in unique_normal_questions if q["type"] not in excluded]
    unique_enigma_questions = _dedupe(generate_enigma_questions(people, language))
    if "enigme" in excluded:
        unique_enigma_questions = []
    _stamp_difficulty(unique_normal_questions)
    _stamp_difficulty(unique_enigma_questions)

    if difficulty == "enigma":
        pool = unique_enigma_questions
        random.shuffle(pool)
        selected = pool[:num_questions]
    elif difficulty == "expert":
        hard_types = DIFFICULTY_TIERS["hard"] - EXPERT_HARD_EXCLUDED_TYPES
        hard_pool = [q for q in unique_normal_questions if q["type"] in hard_types]
        enigma_high_pool = [
            q for q in unique_enigma_questions
            if q.get("complexity") in EXPERT_ENIGMA_HIGH_COMPLEXITIES
        ]
        enigma_low_pool = [
            q for q in unique_enigma_questions
            if q.get("complexity") in EXPERT_ENIGMA_COMPLEXITIES - EXPERT_ENIGMA_HIGH_COMPLEXITIES
        ]
        random.shuffle(hard_pool)
        random.shuffle(enigma_high_pool)
        random.shuffle(enigma_low_pool)

        min_high_enigmas = min(
            len(enigma_high_pool),
            max(1, int(num_questions * EXPERT_MIN_HIGH_ENIGMA_RATIO)),
        )
        selected = enigma_high_pool[:min_high_enigmas]
        remaining = num_questions - len(selected)

        rest_pool = hard_pool + enigma_low_pool + enigma_high_pool[min_high_enigmas:]
        random.shuffle(rest_pool)
        selected.extend(rest_pool[:remaining])
        random.shuffle(selected)
    elif difficulty in DIFFICULTY_TIERS:
        allowed = DIFFICULTY_TIERS[difficulty]
        pool = [q for q in unique_normal_questions if q["type"] in allowed]
        selected = _stratified_sample(pool, num_questions)
        random.shuffle(selected)
    else:
        num_enigmas = int(num_questions * enigma_percentage / 100)
        num_normal = num_questions - num_enigmas
        random.shuffle(unique_enigma_questions)
        selected_enigmas = unique_enigma_questions[:num_enigmas]
        # Si le pool d'énigmes est trop petit, on complète avec des questions normales
        num_normal += num_enigmas - len(selected_enigmas)
        selected = _stratified_sample(unique_normal_questions, num_normal) + selected_enigmas
        random.shuffle(selected)

    # Réécritures de difficulté (après sélection, sur des copies)
    selected = [dict(q) for q in selected]
    convert_long_answers_to_counts(selected, people, language, max_answer_names)
    anonymize_names(selected, people, language, random, anonymize_percentage)

    known_names = {p.first_name for p in people.values()}
    for i, q in enumerate(selected):
        q["id"] = i + 1
        q.setdefault("anonymized", False)
        q.setdefault("converted_to_count", False)
        q["answer_format"] = answer_format(q["answer"], known_names, language)
        if language == "en":
            q["question"] = fix_english_articles(q["question"])

    return selected


# Pour la compatibilité avec l'ancien code, exporter les helpers qui étaient dans ce fichier
from tree_evaluator.questions.base import (
    format_answer as _format_answer,
    get_common_attributes as _get_common_attributes,
    get_father as _get_father,
    get_mother as _get_mother
)