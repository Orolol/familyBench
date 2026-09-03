import random
from typing import Dict, List, Optional
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from tree_evaluator.questions.base import get_siblings
from tree_evaluator.questions.rewrite import fix_english_articles

RELATION_MODES = ("mixed", "parents", "children", "both")
DEFAULT_DERIVED_LINKS_PERCENTAGE = 30


def _tag(p: Person) -> str:
    return f"{p.first_name} ({p.gender})"


def _attributes_sentence(person: Person, language: str) -> str:
    conj = "and" if language == "en" else "et"
    return (
        f"{get_translation('has_hair', language).format(name=_tag(person), hair_color=person.hair_color)}, "
        f"{get_translation('has_eyes', language).format(eye_color=person.eye_color)}, "
        f"{get_translation('wears_hat', language).format(hat_color=person.hat_color)} {conj} "
        f"{get_translation('works_as', language).format(profession=person.profession)}."
    )


def _link_sentence(parent: Person, child: Person, direction: str, language: str) -> str:
    """Une phrase pour UN lien parent-enfant, côté parent ou côté enfant."""
    if direction == "parent":
        key = "is_father_of" if parent.gender == "M" else "is_mother_of"
    else:
        key = "is_son_of" if child.gender == "M" else "is_daughter_of"
    return get_translation(key, language).format(parent=_tag(parent), child=_tag(child)) + "."


def build_description_facts(
    people: Dict[str, Person],
    language: str = "fr",
    relations: str = "mixed",
    derived_links_percentage: int = 0,
    rng=random,
) -> List[dict]:
    """Construit la liste des faits à écrire, sans les ordonner.

    Chaque fait est un dict {"kind", "person_id", "text", ...}. Cette
    représentation intermédiaire sert aussi aux tests de reconstituabilité.

    relations:
      - "mixed": chaque lien parent-enfant est énoncé UNE fois, dans une
        direction tirée au hasard ("A est le père de X" ou "X est la fille de A").
        Retrouver les deux parents de X demande de recoller deux phrases.
      - "parents": "X est l'enfant de A et B" (les deux parents en une phrase)
      - "children": "A a N enfants : ..."
      - "both": parents + children (redondant, le plus facile)
    derived_links_percentage: part des personnes (ayant un frère ou une sœur
      complet dont les liens sont explicites) dont les liens parentaux sont
      remplacés par "X est la sœur de Y". L'arbre reste reconstituable : Y
      (l'ancre) garde ses liens explicites et n'est jamais lui-même dérivé.
    """
    if relations not in RELATION_MODES:
        raise ValueError(f"relations must be one of {RELATION_MODES}, got {relations!r}")
    facts: List[dict] = []
    for person in people.values():
        facts.append({"kind": "attributes", "person_id": person.id, "text": _attributes_sentence(person, language)})

    # Liens dérivés : choisir les personnes dérivées et leurs ancres
    derived: Dict[str, Person] = {}  # person_id -> ancre
    if derived_links_percentage > 0 and relations != "children":
        candidates = [p for p in people.values() if p.parent_ids]
        rng.shuffle(candidates)
        anchors: set = set()
        for person in candidates:
            if person.id in anchors or person.id in derived:
                continue
            if rng.random() * 100 >= derived_links_percentage:
                continue
            siblings = [s for s in get_siblings(person, people) if s.id not in derived]
            if not siblings:
                continue
            anchor = rng.choice(siblings)
            anchors.add(anchor.id)
            derived[person.id] = anchor

    for person in people.values():
        if person.id in derived:
            anchor = derived[person.id]
            key = "is_brother_of" if person.gender == "M" else "is_sister_of"
            facts.append({
                "kind": "derived", "person_id": person.id, "anchor_id": anchor.id,
                "text": get_translation(key, language).format(name=_tag(person), sibling=_tag(anchor)) + ".",
            })
            continue
        if person.parent_ids and relations in ("parents", "both"):
            parent_names = sorted(_tag(people[pid]) for pid in person.parent_ids)
            facts.append({
                "kind": "parents", "person_id": person.id,
                "text": get_translation("is_child_of", language).format(
                    name=_tag(person), parent1=parent_names[0], parent2=parent_names[1]) + ".",
            })
        if person.parent_ids and relations == "mixed":
            for pid in person.parent_ids:
                direction = rng.choice(("parent", "child"))
                facts.append({
                    "kind": "link", "person_id": person.id, "parent_id": pid, "direction": direction,
                    "text": _link_sentence(people[pid], person, direction, language),
                })
        if person.children_ids and relations in ("children", "both"):
            children_names = sorted(_tag(people[cid]) for cid in person.children_ids)
            if len(children_names) == 1:
                text = get_translation("has_children_singular", language).format(
                    name=_tag(person), children=children_names[0])
            else:
                text = get_translation("has_children_plural", language).format(
                    name=_tag(person), count=len(children_names), children=", ".join(children_names))
            facts.append({"kind": "children", "person_id": person.id, "text": text + "."})
    return facts


def convert_tree_to_text(
    people: Dict[str, Person],
    shuffle: bool = False,
    language: str = "fr",
    relations: str = "mixed",
    seed: Optional[int] = None,
    derived_links_percentage: int = 0,
    conventions: bool = True,
) -> str:
    """Convertit le dictionnaire de personnes en une description textuelle.

    Args:
        shuffle: mélange l'ordre des phrases. En mode "mixed", chaque phrase
            de lien est placée indépendamment (les deux liens d'une personne
            peuvent être très éloignés) ; dans les autres modes, les phrases
            d'une même personne restent groupées (attributs en premier).
            Sans mélange, l'ordre est trié par génération puis prénom.
        seed: graine du mélange et des tirages (direction des liens, liens
            dérivés). Avec la même seed la description est identique d'un run
            à l'autre (cache de prompt), quel que soit l'état de `random`.
        conventions: écrit en tête la définition de frère/sœur, demi-frère,
            oncle, cousin... (nécessaire dès qu'il y a des secondes unions).
    """
    if not people:
        return ""
    rng = random.Random(f"description-{seed}") if seed is not None else random
    facts = build_description_facts(people, language, relations, derived_links_percentage, rng)

    order = {p.id: i for i, p in enumerate(sorted(people.values(), key=lambda p: (p.generation, p.first_name)))}
    lines: List[str] = []
    if relations == "mixed" and shuffle:
        # attributs et liens dispersés indépendamment
        facts = list(facts)
        rng.shuffle(facts)
        lines = [f["text"] for f in facts]
    else:
        by_person: Dict[str, List[dict]] = {}
        for f in facts:
            by_person.setdefault(f["person_id"], []).append(f)
        person_ids = sorted(by_person, key=lambda pid: order[pid])
        if shuffle:
            rng.shuffle(person_ids)
        for pid in person_ids:
            parts = by_person[pid]
            head, rest = parts[0], parts[1:]
            if shuffle and len(rest) > 1:
                rng.shuffle(rest)
            lines.extend(f["text"] for f in [head] + rest)

    if conventions:
        lines.insert(0, get_translation("description_conventions", language))
    text = "\n".join(lines)
    return fix_english_articles(text) if language == "en" else text
