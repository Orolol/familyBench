"""Questions énigmes : descriptions relationnelles indirectes, réponse unique garantie."""

import re
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


def _predicate(attr: str, value: str, language: str) -> str:
    key = {"hair_color": "pred_hair", "eye_color": "pred_eyes", "hat_color": "pred_hat"}[attr]
    return get_translation(key, language).format(color=value)


def _make_disc(chain_text: str, attr: str, value: str, answer: str, complexity: int, language: str) -> Dict[str, Any]:
    """Énigme "chaîne + attribut discriminant", formulée pour que l'attribut porte
    sans ambiguïté sur la personne cherchée :
      EN  "Which son of Harrison has black hair?"
      FR  "Quel fils de Harrison a les cheveux noirs ?"
    (et non "Who is the son of Harrison with black hair?", où l'attribut peut
    être lu comme portant sur Harrison)."""
    chain_text = chain_text.strip()
    if language == "en":
        rest = chain_text[4:] if chain_text.lower().startswith("the ") else chain_text
        question = f"Which {rest} {_predicate(attr, value, language)}?"
    else:
        if chain_text.startswith("la "):
            which, rest = "Quelle", chain_text[3:]
        elif chain_text.startswith("le "):
            which, rest = "Quel", chain_text[3:]
        elif chain_text.startswith("l'"):
            which, rest = "Quel", chain_text[2:]
        else:
            which, rest = "Quel", chain_text
        question = f"{which} {rest} {_predicate(attr, value, language)} ?"
    return {"question": question, "answer": answer, "type": "enigme", "complexity": complexity}


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
        relation = f"{get_translation(rel_key, language)} {parent.first_name}"
        out.append(_make_disc(relation, attr, value, target.first_name, 1, language))
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
        relation = f"{get_translation(rel_key, language)} {gp.first_name}"
        out.append(_make_disc(relation, attr, value, target.first_name, 2, language))
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
        relation = f"{get_translation(rel_key, language)} {grandparent.first_name}"
        out.append(_make_disc(relation, attr, value, target.first_name, 3, language))
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
        relation = f"{get_translation(rel_key, language)} {ref.first_name}"
        out.append(_make_disc(relation, attr, value, target.first_name, 4, language))
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
        relation = f"{get_translation(rel_key, language)} {ref.first_name}"
        out.append(_make_disc(relation, attr, value, sibling.first_name, 5, language))
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


# ---------------------------------------------------------------------------
# Moteur de chaînes de relations génériques (niveaux 7 à 9)
# ---------------------------------------------------------------------------

def _parents(p: Person, people: Dict[str, Person]) -> List[Person]:
    return [people[pid] for pid in p.parent_ids]


def _children(p: Person, people: Dict[str, Person]) -> List[Person]:
    return [people[cid] for cid in p.children_ids]


def _by_gender(persons: List[Person], gender: str) -> List[Person]:
    return [x for x in persons if x.gender == gender]


# clé de traduction -> fonction Person -> liste de personnes
CHAIN_RELATIONS = {
    "chain_father": lambda p, ppl: _by_gender(_parents(p, ppl), "M"),
    "chain_mother": lambda p, ppl: _by_gender(_parents(p, ppl), "F"),
    "chain_son": lambda p, ppl: _by_gender(_children(p, ppl), "M"),
    "chain_daughter": lambda p, ppl: _by_gender(_children(p, ppl), "F"),
    "chain_child": lambda p, ppl: _children(p, ppl),
    "chain_brother": lambda p, ppl: _by_gender(_siblings(p, ppl), "M"),
    "chain_sister": lambda p, ppl: _by_gender(_siblings(p, ppl), "F"),
    "chain_male_cousin": lambda p, ppl: _by_gender(_cousins(p, ppl), "M"),
    "chain_female_cousin": lambda p, ppl: _by_gender(_cousins(p, ppl), "F"),
    "chain_uncle": lambda p, ppl: _by_gender(_dedupe([s for par in _parents(p, ppl) for s in _siblings(par, ppl)]), "M"),
    "chain_aunt": lambda p, ppl: _by_gender(_dedupe([s for par in _parents(p, ppl) for s in _siblings(par, ppl)]), "F"),
    "chain_grandfather": lambda p, ppl: _by_gender(_dedupe([gp for par in _parents(p, ppl) for gp in _parents(par, ppl)]), "M"),
    "chain_grandmother": lambda p, ppl: _by_gender(_dedupe([gp for par in _parents(p, ppl) for gp in _parents(par, ppl)]), "F"),
    "chain_grandchild": lambda p, ppl: _grandchildren(p, ppl),
}
CHAIN_KEYS = list(CHAIN_RELATIONS)
SAME_ATTR_KEYS = {
    "hair_color": "chain_same_hair_color",
    "eye_color": "chain_same_eye_color",
    "hat_color": "chain_same_hat_color",
    "profession": "chain_same_profession",
}
CHAIN_ATTEMPTS = 120


def _apply_chain(start: Person, chain: List[str], people: Dict[str, Person]) -> List[Person]:
    """Applique chain[0] à start, puis chain[1] au résultat, etc. (union)."""
    current = [start]
    for key in chain:
        current = _dedupe([r for p in current for r in CHAIN_RELATIONS[key](p, people)])
        if not current:
            return []
    return current


def _fr_contract(text: str) -> str:
    """Contractions françaises : "de le" -> "du", "de les" -> "des"."""
    text = re.sub(r"\bde le\b", "du", text)
    text = re.sub(r"\bde les\b", "des", text)
    return text


def _render_chain(chain: List[str], start_text: str, language: str) -> str:
    """"the child of the sister of the father of X" pour chain=[father, sister, child]."""
    words = [get_translation(key, language) for key in reversed(chain)]
    text = " ".join(words + [start_text])
    return _fr_contract(text) if language == "fr" else text


def _random_chain(length: int) -> List[str]:
    chain = [random.choice(CHAIN_KEYS)]
    while len(chain) < length:
        nxt = random.choice(CHAIN_KEYS)
        # éviter les aller-retours triviaux (père de l'enfant de ...)
        if {chain[-1], nxt} in ({"chain_father", "chain_child"}, {"chain_mother", "chain_child"},
                                 {"chain_father", "chain_son"}, {"chain_father", "chain_daughter"},
                                 {"chain_mother", "chain_son"}, {"chain_mother", "chain_daughter"}):
            continue
        chain.append(nxt)
    return chain


def _chain_question(people: Dict[str, Person], start: Person, start_text: str, chain_len: int,
                    complexity: int, language: str) -> Dict[str, Any] | None:
    """Construit une énigme "chaîne de `chain_len` relations + discriminant" à réponse unique."""
    chain = _random_chain(chain_len)
    pool = _apply_chain(start, chain, people)
    if not pool or start in pool:
        return None
    target = random.choice(pool)
    relation = _render_chain(chain, start_text, language)
    if len(pool) == 1:
        # Déjà unique : on ajoute quand même un attribut pour ne pas révéler l'unicité
        attr = random.choice(DISCRIMINATOR_ATTRS)
        value = getattr(target, attr)
    else:
        disc = _unique_discriminator(target, pool)
        if disc is None:
            return None
        attr, value = disc
    return _make_disc(relation, attr, value, target.first_name, complexity, language)


def _gen_level_7(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """Chaîne de 3 relations depuis une personne nommée + attribut discriminant."""
    out: List[Dict[str, Any]] = []
    for _ in range(CHAIN_ATTEMPTS):
        start = random.choice(person_list)
        q = _chain_question(people, start, start.first_name, 3, 7, language)
        if q:
            out.append(q)
    return out


def _gen_level_8(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """Chaîne de 3 relations depuis une personne désignée par ses attributs (pas de prénom)."""
    out: List[Dict[str, Any]] = []
    for _ in range(CHAIN_ATTEMPTS):
        start = random.choice(person_list)
        start_text = get_translation("person_with_all_attrs", language).format(
            hair=start.hair_color, eyes=start.eye_color, hat=start.hat_color
        )
        q = _chain_question(people, start, start_text, 3, 8, language)
        if q:
            out.append(q)
    return out


PLURAL_CHAIN_KEYS = [
    "chain_son", "chain_daughter", "chain_child", "chain_brother", "chain_sister",
    "chain_male_cousin", "chain_female_cousin", "chain_uncle", "chain_aunt", "chain_grandchild",
]


def _gen_level_9(people: Dict[str, Person], person_list: List[Person], language: str) -> List[Dict[str, Any]]:
    """Deux chaînes jointes par une égalité d'attribut :
    "<chaîne A> X qui a la même profession que <chaîne B> Y" — unique dans le résultat de A."""
    out: List[Dict[str, Any]] = []
    for _ in range(CHAIN_ATTEMPTS * 3):
        x = random.choice(person_list)
        y = random.choice(person_list)
        # la chaîne A doit produire plusieurs candidats : sa dernière relation est plurielle
        chain_a = _random_chain(random.choice((1, 2)))
        chain_a[-1] = random.choice(PLURAL_CHAIN_KEYS)
        chain_b = _random_chain(random.choice((1, 2)))
        pool_a = _apply_chain(x, chain_a, people)
        if len(pool_a) < 2:
            continue
        pool_b = _apply_chain(y, chain_b, people)
        if len(pool_b) != 1:
            continue
        ref = pool_b[0]
        options = []
        for attr in SAME_ATTR_KEYS:
            matching = [p for p in pool_a if getattr(p, attr) == getattr(ref, attr) and p.id != ref.id]
            if len(matching) == 1:
                options.append((attr, matching[0]))
        if not options:
            continue
        attr, target = random.choice(options)
        relation = (
            f"{_render_chain(chain_a, x.first_name, language)} "
            f"{get_translation(SAME_ATTR_KEYS[attr], language)} "
            f"{_render_chain(chain_b, y.first_name, language)}"
        )
        out.append(_make(relation, target.first_name, 9, language))
        if len(out) >= ATTEMPTS_PER_LEVEL:
            break
    return out


def generate_enigma_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des énigmes à réponse unique, réparties sur 9 niveaux de complexité."""
    person_list = list(people.values())
    generators = (
        _gen_level_1,
        _gen_level_2,
        _gen_level_3,
        _gen_level_4,
        _gen_level_5,
        _gen_level_6,
        _gen_level_7,
        _gen_level_8,
        _gen_level_9,
    )
    questions: List[Dict[str, Any]] = []
    for gen in generators:
        questions.extend(gen(people, person_list, language))
    return questions
