"""Questions de comptage."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation


def generate_counting_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions de comptage."""
    questions = []
    for person in people.values():
        questions.append({
            "question": get_translation("q_how_many_children", language).format(name=person.first_name),
            "answer": str(len(person.children_ids)),
            "type": "comptage"
        })

    # Triés : l'ordre d'un set dépend du hash Python (reproductibilité par seed)
    eye_colors = sorted({p.eye_color for p in people.values()})
    for color in eye_colors:
        count = len([p for p in people.values() if p.eye_color == color])
        questions.append({
            "question": get_translation("q_how_many_with_eyes", language).format(color=color),
            "answer": str(count),
            "type": "comptage"
        })

    professions = sorted({p.profession for p in people.values()})
    for profession in professions:
        count = len([p for p in people.values() if p.profession == profession])
        questions.append({
            "question": get_translation("q_how_many_profession", language).format(profession=profession),
            "answer": str(count),
            "type": "comptage"
        })
    return questions