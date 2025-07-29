"""Questions sur les relations directes (parents, enfants)."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import format_answer, get_father, get_mother


def generate_direct_relation_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions sur les relations directes (parents, enfants)."""
    questions = []
    for person in people.values():
        if person.children_ids:
            children_names = [people[cid].first_name for cid in person.children_ids]
            questions.append({
                "question": get_translation("q_children_of", language).format(name=person.first_name),
                "answer": format_answer(children_names, language),
                "type": "relation_directe",
            })

        if len(person.parent_ids) == 2:
            parent_names = [people[pid].first_name for pid in person.parent_ids]
            questions.append({
                "question": get_translation("q_parents_of", language).format(name=person.first_name),
                "answer": format_answer(parent_names, language),
                "type": "relation_directe",
            })
            
            father = get_father(person, people)
            if father:
                questions.append({
                    "question": get_translation("q_father_of", language).format(name=person.first_name),
                    "answer": father.first_name,
                    "type": "relation_directe",
                })

            mother = get_mother(person, people)
            if mother:
                questions.append({
                    "question": get_translation("q_mother_of", language).format(name=person.first_name),
                    "answer": mother.first_name,
                    "type": "relation_directe",
                })

    return questions


def generate_inverse_relation_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions sur les relations inverses."""
    questions = []
    for person in people.values():
        if person.parent_ids:
            parent_names = [people[pid].first_name for pid in person.parent_ids]
            pronoun = get_translation("pronoun_m" if person.gender == 'M' else "pronoun_f", language)
            questions.append({
                "question": get_translation("q_child_of_whom", language).format(name=person.first_name, pronoun=pronoun),
                "answer": format_answer(parent_names, language),
                "type": "relation_inverse",
            })

        if person.children_ids:
            children_names = [people[cid].first_name for cid in person.children_ids]
            pronoun = get_translation("pronoun_m" if person.gender == 'M' else "pronoun_f", language)
            questions.append({
                "question": get_translation("q_parent_of_whom", language).format(name=person.first_name, pronoun=pronoun),
                "answer": format_answer(children_names, language),
                "type": "relation_inverse",
            })
    return questions