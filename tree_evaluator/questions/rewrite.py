"""Réécritures appliquées aux questions après sélection.

- `anonymize_names` : remplace les prénoms cités dans la question par une
  description par attributs ("la personne aux cheveux roux, aux yeux bleus et
  au chapeau vert"), unique par construction. Le modèle doit d'abord retrouver
  la personne avant de raisonner sur ses liens.
- `convert_long_answers_to_counts` : les questions dont la réponse dépasse
  `max_names` prénoms deviennent des questions de dénombrement. Une réponse de
  200 noms mesure l'endurance d'énumération, pas le raisonnement, et le crédit
  partiel y offrait des points gratuits.
"""

import re
from typing import Dict, List, Any, Iterable

from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation

# Mots pouvant suivre "{name}'s" dans les templates anglais et former le
# groupe nominal possédé ("children", "uncles or aunts", "mother's father"...)
_EN_RELATION_WORDS = {
    "child", "children", "mother", "father", "parent", "parents", "sibling", "siblings",
    "brother", "brothers", "sister", "sisters", "cousin", "cousins", "uncle", "uncles",
    "aunt", "aunts", "nephew", "nephews", "niece", "nieces", "grandparent", "grandparents",
    "grandmother", "grandmothers", "grandfather", "grandfathers", "grandchild", "grandchildren",
    "grandson", "grandsons", "granddaughter", "granddaughters", "great-grandparent",
    "great-grandparents", "great-grandmother", "great-grandmothers", "great-grandfather",
    "great-grandfathers", "great-grandchild", "great-grandchildren", "great-grandson",
    "great-grandsons", "great-granddaughter", "great-granddaughters", "descendant",
    "descendants", "ancestor", "ancestors", "in-laws", "generation", "son", "sons",
    "daughter", "daughters", "spouse", "partner", "family",
}
_EN_MODIFIERS = {"male", "female", "oldest", "youngest", "eldest", "own", "direct"}
_EN_CONNECTORS = {"or", "and"}
_TRAILING_PUNCT = "?,.;:!\"»)"
# Les énigmes ne sont pas anonymisées : leur formulation "Quel fils de X a ..."
# deviendrait ambiguë avec une seconde description par attributs.
_SKIP_ANONYMIZE_TYPES = {"enigme"}

# Mots capitalisés qui ne sont jamais des prénoms à remplacer
_STOPWORDS = {
    "Who", "Which", "What", "How", "Among", "Is", "Are", "Does", "Do", "In", "Of", "The",
    "Qui", "Quel", "Quels", "Quelle", "Quelles", "Combien", "Parmi", "De", "Est", "Sont",
    "Dans", "Le", "La", "Les", "Un", "Une", "None", "Aucun",
}


def describe_person(person: Person, language: str) -> str:
    """Description par attributs, unique dans l'arbre."""
    return get_translation("person_with_all_attrs", language).format(
        hair=person.hair_color, eyes=person.eye_color, hat=person.hat_color
    )


def _rewrite_en_possessive(text: str, name: str, desc: str) -> str:
    """"Marie's uncles or aunts" -> "the uncles or aunts of <desc>";
    "Lucy's mother's father" -> "the father of the mother of <desc>"."""
    pattern = re.compile(r"\b" + re.escape(name) + r"'s\b")
    while True:
        m = pattern.search(text)
        if not m:
            return text
        rest = text[m.end():]
        tokens = rest.split(" ")
        # tokens[0] est "" (l'espace juste après "'s")
        segments: List[List[str]] = [[]]
        consumed = 0  # nombre de tokens (après le premier vide) intégrés
        for tok in tokens[1:]:
            word = tok.rstrip(_TRAILING_PUNCT)
            trailing = tok[len(word):]
            base = word[:-2] if word.endswith("'s") else (word[:-1] if word.endswith("'") else word)
            if base in _EN_RELATION_WORDS or base in _EN_MODIFIERS:
                segments[-1].append(base)
                consumed += 1
                if word.endswith("'s") or (word.endswith("'") and base.endswith("s")):
                    segments.append([])  # nouveau niveau de possession
                    continue
                if trailing:  # ponctuation : fin du groupe
                    break
            elif word in _EN_CONNECTORS and segments[-1]:
                segments[-1].append(word)
                consumed += 1
            else:
                break
        # retirer un connecteur pendant en fin de segment
        while segments and segments[-1] and segments[-1][-1] in _EN_CONNECTORS:
            segments[-1].pop()
            consumed -= 1
        segments = [seg for seg in segments if seg]
        if not segments:
            # Pas de groupe reconnu : possessif sur la description elle-même
            text = text[:m.start()] + desc + "'s" + rest
            continue
        phrase = desc
        for seg in segments:
            phrase = f"the {' '.join(seg)} of {phrase}"
        # reconstruire : on remplace "Name's" + les `consumed` tokens suivants
        remaining_tokens = tokens[1 + consumed:]
        # conserver la ponctuation collée au dernier token consommé
        last = tokens[consumed] if consumed >= 1 else ""
        punct = last[len(last.rstrip(_TRAILING_PUNCT)):] if last else ""
        text = text[:m.start()] + phrase + punct + (" " + " ".join(remaining_tokens) if remaining_tokens else "")


def anonymize_question(question: Dict[str, Any], people_by_name: Dict[str, Person], language: str) -> bool:
    """Remplace les prénoms cités dans la question. Retourne True si modifié."""
    text = question["question"]
    names = [
        n for n in people_by_name
        if n not in _STOPWORDS and re.search(r"\b" + re.escape(n) + r"\b", text)
    ]
    if not names:
        return False
    # Les noms les plus longs d'abord (évite qu'un prénom court en remplace un long)
    for name in sorted(names, key=len, reverse=True):
        desc = describe_person(people_by_name[name], language)
        if language == "en":
            text = _rewrite_en_possessive(text, name, desc)
        text = re.sub(r"\b" + re.escape(name) + r"\b", desc, text)
        if language == "fr":
            # "d'Alice" n'existe pas dans les templates, mais au cas où
            text = text.replace(f"d'{desc}", f"de {desc}")
    if text == question["question"]:
        return False
    question["question"] = text
    question["anonymized"] = True
    question["anonymized_names"] = sorted(names)
    return True


def anonymize_names(questions: List[Dict[str, Any]], people: Dict[str, Person], language: str,
                    rng, percentage: int) -> int:
    """Anonymise `percentage` % des questions (tirage par question). Retourne le nombre modifié."""
    if percentage <= 0:
        return 0
    people_by_name = {p.first_name: p for p in people.values()}
    count = 0
    for q in questions:
        q.setdefault("anonymized", False)
        if q["type"] in _SKIP_ANONYMIZE_TYPES:
            continue
        if rng.random() * 100 < percentage and anonymize_question(q, people_by_name, language):
            count += 1
    return count


def fix_english_articles(text: str) -> str:
    """"a orange hat" -> "an orange hat", "a artist" -> "an artist"."""
    return re.sub(r"\b([Aa]) (?=[aeiouAEIOU])", lambda m: m.group(1) + "n ", text)


def answer_format(answer: str, known_names: Iterable[str], language: str) -> str:
    """"count", "none", "names" ou "label" (attribut / libellé de relation)."""
    if answer.isdigit():
        return "count"
    if answer == get_translation("none", language):
        return "none"
    known = set(known_names)
    tokens = [t for t in answer.split(",") if t]
    if tokens and all(t in known for t in tokens):
        return "names"
    return "label"


def convert_long_answers_to_counts(questions: List[Dict[str, Any]], people: Dict[str, Person],
                                   language: str, max_names: int) -> int:
    """Transforme les questions à plus de `max_names` prénoms en dénombrement."""
    if max_names <= 0:
        return 0
    known = {p.first_name for p in people.values()}
    count = 0
    for q in questions:
        if answer_format(q["answer"], known, language) != "names":
            continue
        names = q["answer"].split(",")
        if len(names) <= max_names:
            continue
        original = q["question"]
        q["question"] = get_translation("q_count_wrapper", language).format(question=original)
        q["original_question"] = original
        q["original_answer_size"] = len(names)
        q["answer"] = str(len(names))
        q["converted_to_count"] = True
        count += 1
    return count
