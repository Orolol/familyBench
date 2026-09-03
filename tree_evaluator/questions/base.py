"""Fonctions de base pour la génération de questions."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation


def format_answer(names: List[str], language: str = "fr") -> str:
    """Formate une liste de noms en une chaîne de réponse."""
    if not names:
        return get_translation("none", language)
    # dict.fromkeys preserves insertion order while deduplicating
    unique_names = list(dict.fromkeys(names))
    return ",".join(sorted(unique_names))


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

# ---------------------------------------------------------------------------
# Relations de parenté. Avec les secondes unions, une personne peut avoir des
# enfants avec deux partenaires : on distingue la fratrie (deux parents en
# commun) de la demi-fratrie (un seul). Oncles, tantes, cousins, neveux sont
# définis à partir de la fratrie complète, conformément à la convention
# énoncée en tête de chaque description.
# ---------------------------------------------------------------------------

def _unique(persons: List[Person]) -> List[Person]:
    seen, out = set(), []
    for p in persons:
        if p.id not in seen:
            seen.add(p.id)
            out.append(p)
    return out


def get_siblings(person: Person, people: Dict[str, Person]) -> List[Person]:
    """Frères et sœurs : mêmes deux parents (exclut les demi-frères/sœurs)."""
    if len(person.parent_ids) < 2:
        return []
    parents = set(person.parent_ids)
    return _unique([
        people[cid] for pid in person.parent_ids for cid in people[pid].children_ids
        if cid != person.id and set(people[cid].parent_ids) == parents
    ])


def get_half_siblings(person: Person, people: Dict[str, Person]) -> List[Person]:
    """Demi-frères et demi-sœurs : exactement un parent en commun."""
    parents = set(person.parent_ids)
    return _unique([
        people[cid] for pid in person.parent_ids for cid in people[pid].children_ids
        if cid != person.id and len(set(people[cid].parent_ids) & parents) == 1
    ])


def get_uncles_aunts(person: Person, people: Dict[str, Person]) -> List[Person]:
    """Frères et sœurs (complets) des parents."""
    return _unique([s for pid in person.parent_ids for s in get_siblings(people[pid], people)])


def get_cousins(person: Person, people: Dict[str, Person]) -> List[Person]:
    """Enfants des oncles et tantes."""
    return _unique([people[cid] for ua in get_uncles_aunts(person, people) for cid in ua.children_ids])


def get_nephews_nieces(person: Person, people: Dict[str, Person]) -> List[Person]:
    """Enfants des frères et sœurs (complets)."""
    return _unique([people[cid] for s in get_siblings(person, people) for cid in s.children_ids])


def get_co_parents(person: Person, people: Dict[str, Person]) -> List[Person]:
    """Partenaires : les autres parents de ses enfants."""
    return _unique([
        people[pid] for cid in person.children_ids for pid in people[cid].parent_ids if pid != person.id
    ])


def get_step_parents(person: Person, people: Dict[str, Person]) -> List[Person]:
    """Beaux-parents : partenaires d'un parent qui ne sont pas parents de la personne."""
    parents = set(person.parent_ids)
    return _unique([
        cp for pid in person.parent_ids for cp in get_co_parents(people[pid], people) if cp.id not in parents
    ])
