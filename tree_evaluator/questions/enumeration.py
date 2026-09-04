"""Énumérations complètes : réponses de 5 à 12 prénoms exigeant un balayage
complet de la description. Les modèles frontière ne raisonnent pas faux sur ce
benchmark, ils oublient un élément : ce type les note sur le rappel complet.
"""

from typing import Dict, List, Any

from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import format_answer, get_nephews_nieces, get_cousins, get_common_attributes

MIN_NAMES = 5
MAX_NAMES = 12


def _descendants(p: Person, people: Dict[str, Person]) -> List[Person]:
    out, stack, seen = [], list(p.children_ids), set()
    while stack:
        cid = stack.pop()
        if cid in seen:
            continue
        seen.add(cid)
        out.append(people[cid])
        stack.extend(people[cid].children_ids)
    return out


def _grandchildren(p: Person, people: Dict[str, Person]) -> List[Person]:
    return [people[g] for c in p.children_ids for g in people[c].children_ids]


def generate_enumeration_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []

    def add(key: str, names: List[str], **fmt):
        uniq = sorted(set(names))
        if MIN_NAMES <= len(uniq) <= MAX_NAMES:
            questions.append({
                "question": get_translation(key, language).format(**fmt),
                "answer": format_answer(uniq, language),
                "type": "enumeration",
            })

    for person in people.values():
        add("q_enum_descendants", [d.first_name for d in _descendants(person, people)], name=person.first_name)
        add("q_enum_grandchildren", [g.first_name for g in _grandchildren(person, people)], name=person.first_name)
        add("q_enum_nephews", [n.first_name for n in get_nephews_nieces(person, people)], name=person.first_name)
        add("q_enum_cousins", [c.first_name for c in get_cousins(person, people)], name=person.first_name)

    roots = [p for p in people.values() if not p.parent_ids]
    for profession in get_common_attributes(people, "profession", min_count=2):
        names = [people[c].first_name for r in roots if r.profession == profession for c in r.children_ids]
        add("q_enum_roots_children", names, profession=profession)
    return questions
