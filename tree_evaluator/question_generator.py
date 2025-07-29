"""Générateur de questions principal qui utilise les modules de questions."""

import random
import json
from typing import Dict, List, Any

from tree_evaluator.models import Person

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


def generate_questions(people: Dict[str, Person], num_questions: int, language: str = "fr", enigma_percentage: int = 10) -> List[Dict[str, Any]]:
    """Génère une liste de questions de différents types."""
    
    # Générer d'abord les questions normales
    normal_questions = []
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
    
    # Éliminer les doublons des questions normales
    unique_questions_map = {json.dumps(q, sort_keys=True): q for q in normal_questions}
    unique_normal_questions = list(unique_questions_map.values())
    
    # Générer les énigmes séparément
    enigma_questions = generate_enigma_questions(people, language)
    unique_enigma_map = {json.dumps(q, sort_keys=True): q for q in enigma_questions}
    unique_enigma_questions = list(unique_enigma_map.values())
    
    # Calculer le nombre d'énigmes à inclure
    num_enigmas = int(num_questions * enigma_percentage / 100)
    num_normal = num_questions - num_enigmas
    
    # Sélectionner les questions
    random.shuffle(unique_normal_questions)
    random.shuffle(unique_enigma_questions)
    
    selected_normal = unique_normal_questions[:num_normal]
    selected_enigmas = unique_enigma_questions[:num_enigmas]
    
    # Combiner et mélanger
    all_selected = selected_normal + selected_enigmas
    random.shuffle(all_selected)
    
    # Assigner les IDs
    for i, q in enumerate(all_selected):
        q["id"] = i + 1
    
    return all_selected


# Pour la compatibilité avec l'ancien code, exporter les helpers qui étaient dans ce fichier
from tree_evaluator.questions.base import (
    format_answer as _format_answer,
    get_common_attributes as _get_common_attributes,
    get_father as _get_father,
    get_mother as _get_mother
)