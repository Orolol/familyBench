"""Fonctions de base pour la génération de questions."""

import json
from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation


def format_answer(names: List[str], language: str = "fr") -> str:
    """Formate une liste de noms en une chaîne de réponse."""
    if not names:
        return get_translation("none", language)
    return ",".join(sorted(names))


def get_common_attributes(people: Dict[str, Person], attribute: str, min_count: int = 2) -> List[str]:
    """Retourne les valeurs d'attribut qui apparaissent au moins min_count fois."""
    counts = {}
    for person in people.values():
        value = getattr(person, attribute)
        counts[value] = counts.get(value, 0) + 1
    return [value for value, count in counts.items() if count >= min_count]


def get_father(person: Person, people: Dict[str, Person]) -> Person | None:
    """Retourne le père d'une personne."""
    for pid in person.parent_ids:
        if people[pid].gender == 'M':
            return people[pid]
    return None


def get_mother(person: Person, people: Dict[str, Person]) -> Person | None:
    """Retourne la mère d'une personne."""
    for pid in person.parent_ids:
        if people[pid].gender == 'F':
            return people[pid]
    return None