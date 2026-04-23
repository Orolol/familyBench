"""Questions énigmes : descriptions relationnelles indirectes, réponse unique garantie."""

import random
from typing import Dict, List, Any, Tuple

from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import get_father, get_mother


DISCRIMINATOR_ATTRS = ("hair_color", "eye_color", "hat_color")
ATTEMPTS_PER_LEVEL = 25


def _attr_phrase(attr: str, value: str, language: str) -> str:
    if attr == "hair_color":
        return get_translation("with_hair", language).format(color=value)
    if attr == "eye_color":
        return get_translation("with_eyes", language).format(color=value)
    if attr == "hat_color":
        return get_translation("wearing_hat", language).format(color=value)
    raise ValueError(f"Unknown discriminator attribute: {attr!r}")


def _dedupe(people_list: List[Person]) -> List[Person]:
    seen: set[str] = set()
    out: List[Person] = []
    for p in people_list:
        if p.id not in seen:
            seen.add(p.id)
            out.append(p)
    return out


def _unique_discriminator(target: Person, pool: List[Person]) -> Tuple[str, str] | None:
    """Return (attr, value) that identifies target uniquely within pool, else None."""
    pool_ids = {p.id for p in pool}
    if target.id not in pool_ids:
        return None
    for attr in DISCRIMINATOR_ATTRS:
        value = getattr(target, attr)
        matching = [p for p in pool if getattr(p, attr) == value]
        if len(matching) == 1 and matching[0].id == target.id:
            return attr, value
    return None


def _siblings(person: Person, people: Dict[str, Person]) -> List[Person]:
    out = []
    for pid in person.parent_ids:
        for cid in people[pid].children_ids:
            if cid != person.id:
                out.append(people[cid])
    return _dedupe(out)


def _cousins(person: Person, people: Dict[str, Person]) -> List[Person]:
    out = []
    for pid in person.parent_ids:
        parent = people[pid]
        for gpid in parent.parent_ids:
            for auid in people[gpid].children_ids:
                if auid == pid:
                    continue
                out.extend(people[cid] for cid in people[auid].children_ids)
    return _dedupe(out)


def _grandchildren(person: Person, people: Dict[str, Person]) -> List[Person]:
    out = []
    for cid in person.children_ids:
        out.extend(people[gcid] for gcid in people[cid].children_ids)
    return _dedupe(out)


def _make(relation: str, answer: str, complexity: int, language: str) -> Dict[str, Any]:
    return {
        "question": get_translation("q_enigma_base", language).format(relation_chain=relation),
        "answer": answer,
        "type": "enigme",
        "complexity": complexity,
    }


def _gen_level_1(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """son/daughter of X with <attr> — unique among X's children."""
    out: List[Dict[str, Any]] = []
    parents_with_kids = [p for p in person_list if len(p.children_ids) >= 2]
    if not parents_with_kids:
        return out
    for _ in range(ATTEMPTS_PER_LEVEL):
        parent = random.choice(parents_with_kids)
        children = [people[cid] for cid in parent.children_ids]
        target = random.choice(children)
        disc = _unique_discriminator(target, children)
        if disc is None:
            continue
        attr, value = disc
        rel_key = "the_son_of" if target.gender == "M" else "the_daughter_of"
        relation = (
            f"{get_translation(rel_key, language)} {parent.first_name} "
            f"{_attr_phrase(attr, value, language)}"
        )
        out.append(_make(relation, target.first_name, 1, language))
    return out


def _gen_level_2(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """child of the son/daughter of X with <attr> — unique among same-side grandchildren."""
    out: List[Dict[str, Any]] = []
    grandparents = [p for p in person_list if _grandchildren(p, people)]
    if not grandparents:
        return out
    for _ in range(ATTEMPTS_PER_LEVEL):
        gp = random.choice(grandparents)
        all_gcs = _grandchildren(gp, people)
        target = random.choice(all_gcs)
        intermediate = next(
            (people[pid] for pid in target.parent_ids if pid in gp.children_ids),
            None,
        )
        if intermediate is None:
            continue
        pool = _dedupe([
            people[gcid]
            for cid in gp.children_ids
            if people[cid].gender == intermediate.gender
            for gcid in people[cid].children_ids
        ])
        disc = _unique_discriminator(target, pool)
        if disc is None:
            continue
        attr, value = disc
        rel_key = "the_child_of_the_son_of" if intermediate.gender == "M" else "the_child_of_the_daughter_of"
        relation = (
            f"{get_translation(rel_key, language)} {gp.first_name} "
            f"{_attr_phrase(attr, value, language)}"
        )
        out.append(_make(relation, target.first_name, 2, language))
    return out


def _gen_level_3(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """(male|female) cousin of the son/daughter of <grandparent> with <attr> — unique among cousins."""
    out: List[Dict[str, Any]] = []
    candidates = [p for p in person_list if p.parent_ids and _cousins(p, people)]
    if not candidates:
        return out
    for _ in range(ATTEMPTS_PER_LEVEL):
        intermediate = random.choice(candidates)
        cousins = _cousins(intermediate, people)
        target = random.choice(cousins)
        disc = _unique_discriminator(target, cousins)
        if disc is None:
            continue
        attr, value = disc
        grandparent = people[random.choice(intermediate.parent_ids)]
        if target.gender == "M":
            rel_key = (
                "the_cousin_of_the_son_of"
                if intermediate.gender == "M"
                else "the_cousin_of_the_daughter_of"
            )
        else:
            rel_key = (
                "the_female_cousin_of_the_son_of"
                if intermediate.gender == "M"
                else "the_female_cousin_of_the_daughter_of"
            )
        relation = (
            f"{get_translation(rel_key, language)} {grandparent.first_name} "
            f"{_attr_phrase(attr, value, language)}"
        )
        out.append(_make(relation, target.first_name, 3, language))
    return out


def _gen_level_4(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """grandchild of the brother/sister of X with <attr> — unique among same-gender siblings' grandchildren."""
    out: List[Dict[str, Any]] = []
    candidates: List[Tuple[Person, Person]] = []
    for p in person_list:
        for s in _siblings(p, people):
            if _grandchildren(s, people):
                candidates.append((p, s))
    if not candidates:
        return out
    for _ in range(ATTEMPTS_PER_LEVEL):
        ref, sibling = random.choice(candidates)
        target = random.choice(_grandchildren(sibling, people))
        pool = _dedupe([
            g
            for s in _siblings(ref, people)
            if s.gender == sibling.gender
            for g in _grandchildren(s, people)
        ])
        disc = _unique_discriminator(target, pool)
        if disc is None:
            continue
        attr, value = disc
        rel_key = (
            "the_grandchild_of_the_brother_of"
            if sibling.gender == "M"
            else "the_grandchild_of_the_sister_of"
        )
        relation = (
            f"{get_translation(rel_key, language)} {ref.first_name} "
            f"{_attr_phrase(attr, value, language)}"
        )
        out.append(_make(relation, target.first_name, 4, language))
    return out


def _gen_level_5(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """brother/sister of the father/mother of X with <attr> — unique among same-side in-laws."""
    out: List[Dict[str, Any]] = []
    candidates: List[Tuple[Person, Person, Person, str]] = []
    for p in person_list:
        for via, resolver in (("father", get_father), ("mother", get_mother)):
            parent = resolver(p, people)
            if parent is None:
                continue
            for s in _siblings(parent, people):
                candidates.append((p, parent, s, via))
    if not candidates:
        return out
    for _ in range(ATTEMPTS_PER_LEVEL):
        ref, parent, sibling, via = random.choice(candidates)
        pool = [s for s in _siblings(parent, people) if s.gender == sibling.gender]
        disc = _unique_discriminator(sibling, pool)
        if disc is None:
            continue
        attr, value = disc
        if via == "father":
            rel_key = "the_brother_of_the_father_of" if sibling.gender == "M" else "the_sister_of_the_father_of"
        else:
            rel_key = "the_brother_of_the_mother_of" if sibling.gender == "M" else "the_sister_of_the_mother_of"
        relation = (
            f"{get_translation(rel_key, language)} {ref.first_name} "
            f"{_attr_phrase(attr, value, language)}"
        )
        out.append(_make(relation, sibling.first_name, 5, language))
    return out


def _gen_level_6(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """father/mother of the person with (hair, eyes, hat) — attribute combo is unique per tree constraint."""
    out: List[Dict[str, Any]] = []
    candidates = [p for p in person_list if p.parent_ids]
    if not candidates:
        return out
    for _ in range(ATTEMPTS_PER_LEVEL):
        child = random.choice(candidates)
        parent = people[random.choice(child.parent_ids)]
        parent_key = "the_father_of" if parent.gender == "M" else "the_mother_of"
        person_desc = get_translation("person_with_all_attrs", language).format(
            hair=child.hair_color,
            eyes=child.eye_color,
            hat=child.hat_color,
        )
        relation = f"{get_translation(parent_key, language)} {person_desc}"
        out.append(_make(relation, parent.first_name, 6, language))
    return out


def generate_enigma_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des énigmes à réponse unique, réparties sur 6 niveaux de complexité."""
    person_list = list(people.values())
    generators = (
        _gen_level_1,
        _gen_level_2,
        _gen_level_3,
        _gen_level_4,
        _gen_level_5,
        _gen_level_6,
    )
    questions: List[Dict[str, Any]] = []
    for gen in generators:
        questions.extend(gen(people, person_list, language))
    return questions
