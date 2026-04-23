"""Générateur de questions principal qui utilise les modules de questions."""

import random
import json
from typing import Dict, List, Any

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
    },
    "enigma": {"enigme"},
}
EXPERT_ENIGMA_COMPLEXITIES = {4, 5, 6}
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
from tree_evaluator.questions.complex_relations import generate_complex_relation_questions
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


def _dedupe(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list({json.dumps(q, sort_keys=True): q for q in questions}.values())


def generate_questions(
    people: Dict[str, Person],
    num_questions: int,
    language: str = "fr",
    enigma_percentage: int = 10,
    difficulty: str = "all",
) -> List[Dict[str, Any]]:
    """Génère une liste de questions de différents types.

    Args:
        difficulty: "all" (mix par défaut pondéré par enigma_percentage),
            "easy", "medium", "hard" (uniquement questions normales du tier),
            "enigma" (uniquement des énigmes),
            ou "expert" (questions normales 'hard' + énigmes de complexité 4/5/6).
    """
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
    normal_questions.extend(generate_transversal_questions(people, language))
    normal_questions.extend(generate_vertical_questions(people, language))
    normal_questions.extend(generate_compound_relation_questions(people, language))
    normal_questions.extend(generate_multihop_questions(people, language))
    normal_questions.extend(generate_conditional_questions(people, language))
    normal_questions.extend(generate_negation_questions(people, language))
    normal_questions.extend(generate_comparative_questions(people, language))
    normal_questions.extend(generate_relational_path_questions(people, language))

    unique_normal_questions = _dedupe(normal_questions)
    unique_enigma_questions = _dedupe(generate_enigma_questions(people, language))

    if difficulty == "enigma":
        pool = unique_enigma_questions
        random.shuffle(pool)
        selected = pool[:num_questions]
    elif difficulty == "expert":
        hard_types = DIFFICULTY_TIERS["hard"]
        hard_pool = [q for q in unique_normal_questions if q["type"] in hard_types]
        enigma_pool = [
            q for q in unique_enigma_questions
            if q.get("complexity") in EXPERT_ENIGMA_COMPLEXITIES
        ]
        pool = hard_pool + enigma_pool
        random.shuffle(pool)
        selected = pool[:num_questions]
    elif difficulty in DIFFICULTY_TIERS:
        allowed = DIFFICULTY_TIERS[difficulty]
        pool = [q for q in unique_normal_questions if q["type"] in allowed]
        random.shuffle(pool)
        selected = pool[:num_questions]
    else:
        num_enigmas = int(num_questions * enigma_percentage / 100)
        num_normal = num_questions - num_enigmas
        random.shuffle(unique_normal_questions)
        random.shuffle(unique_enigma_questions)
        selected = unique_normal_questions[:num_normal] + unique_enigma_questions[:num_enigmas]
        random.shuffle(selected)

    for i, q in enumerate(selected):
        q["id"] = i + 1

    return selected


# Pour la compatibilité avec l'ancien code, exporter les helpers qui étaient dans ce fichier
from tree_evaluator.questions.base import (
    format_answer as _format_answer,
    get_common_attributes as _get_common_attributes,
    get_father as _get_father,
    get_mother as _get_mother
)