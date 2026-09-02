"""Leviers de difficulté : description mélangée/unidirectionnelle, conversion
des réponses longues en dénombrement, anonymisation des prénoms, énigmes 7-9."""
import collections
import random
import re

import pytest

from tree_evaluator.models import Person
from tree_evaluator.tree_generator import generate_tree
from tree_evaluator.text_converter import convert_tree_to_text
from tree_evaluator.question_generator import generate_questions, EXPERT_ENIGMA_COMPLEXITIES
from tree_evaluator.questions import enigma as E
from tree_evaluator.questions.rewrite import (
    _rewrite_en_possessive, anonymize_question, convert_long_answers_to_counts,
    fix_english_articles, describe_person,
)


@pytest.fixture(scope="module")
def tree():
    return generate_tree(300, 5, 3, seed=8, num_root_couples=3, language="en")


# ---------------------------------------------------------------- description
def test_shuffle_is_seeded_and_independent_of_global_random(tree):
    random.seed(1)
    a = convert_tree_to_text(tree, shuffle=True, language="en", seed=8)
    random.seed(2)
    b = convert_tree_to_text(tree, shuffle=True, language="en", seed=8)
    c = convert_tree_to_text(tree, shuffle=True, language="en", seed=9)
    sorted_desc = convert_tree_to_text(tree, shuffle=False, language="en")
    assert a == b, "same seed -> identical description (prompt cache)"
    assert a != c and a != sorted_desc
    assert sorted(a.splitlines()) == sorted(sorted_desc.splitlines()), "shuffle only reorders"


def test_relations_modes(tree):
    both = convert_tree_to_text(tree, language="en", relations="both")
    parents = convert_tree_to_text(tree, language="en", relations="parents")
    children = convert_tree_to_text(tree, language="en", relations="children")
    assert "is the child of" in parents and "children:" not in parents and " child:" not in parents
    assert "is the child of" not in children and ("children:" in children or " child:" in children)
    assert len(both.splitlines()) > len(parents.splitlines())
    n_people = len(tree)
    assert sum(1 for l in parents.splitlines() if "is the child of" in l) == sum(1 for p in tree.values() if p.parent_ids)
    with pytest.raises(ValueError):
        convert_tree_to_text(tree, language="en", relations="spouses")


# ---------------------------------------------------------------- comptage
def test_long_answers_become_counts(tree):
    qs = generate_questions(tree, 150, language="en", max_answer_names=10, anonymize_percentage=0)
    for q in qs:
        if q["answer_format"] == "names":
            assert len(q["answer"].split(",")) <= 10
        if q["converted_to_count"]:
            assert q["answer"].isdigit() and int(q["answer"]) == q["original_answer_size"] > 10
            assert q["question"].startswith("How many people answer the following question")
            assert q["original_question"] in q["question"]
    assert any(q["converted_to_count"] for q in qs)
    off = generate_questions(tree, 150, language="en", max_answer_names=0, anonymize_percentage=0)
    assert not any(q["converted_to_count"] for q in off)
    assert any(len(q["answer"].split(",")) > 10 for q in off)


# ---------------------------------------------------------------- anonymisation
def _p(name, hair="red", eyes="blue", hat="green"):
    return Person(id=name, first_name=name, gender="F", profession="x", hair_color=hair, eye_color=eyes, hat_color=hat)


@pytest.mark.parametrize("text, expected", [
    ("Who are Marie's children?", "Who are the children of DESC?"),
    ("Which of Marie's uncles or aunts have red hair?", "Which of the uncles or aunts of DESC have red hair?"),
    ("Who has the same hair color as Marie's mother's father?", "Who has the same hair color as the father of the mother of DESC?"),
    ("Who are Marie's grandparents' siblings?", "Who are the siblings of the grandparents of DESC?"),
    ("Who are Marie's male cousins?", "Who are the male cousins of DESC?"),
    ("Who in Marie's generation works as a doctor?", "Who in the generation of DESC works as a doctor?"),
    ('Count: "Who are all of Marie\'s descendants?"', 'Count: "Who are all of the descendants of DESC?"'),
    ("Who are Marie's children's in-laws?", "Who are the in-laws of the children of DESC?"),
])
def test_english_possessive_rewrite(text, expected):
    assert _rewrite_en_possessive(text, "Marie", "DESC") == expected


def test_anonymize_question_replaces_every_name_and_keeps_answer():
    people = {"Marie": _p("Marie"), "Paul": _p("Paul", hair="black"), "Anna": _p("Anna", hat="red")}
    q = {"question": "What is the family relationship between Marie and Paul?", "answer": "cousins", "type": "relational_path"}
    assert anonymize_question(q, people, "en")
    assert "Marie" not in q["question"] and "Paul" not in q["question"]
    assert q["question"].count("the person with") == 2 and q["answer"] == "cousins"
    assert q["anonymized_names"] == ["Marie", "Paul"]
    fr = {"question": "Qui sont les enfants de Anna ?", "answer": "Marie", "type": "relation_directe"}
    assert anonymize_question(fr, people, "fr")
    assert fr["question"] == "Qui sont les enfants de la personne aux cheveux red, aux yeux blue et au chapeau red ?"
    untouched = {"question": "Who has red hair?", "answer": "Marie", "type": "recherche_attributs"}
    assert not anonymize_question(untouched, people, "en")


def test_anonymization_share_and_uniqueness(tree):
    known = {p.first_name for p in tree.values()}
    descs = [describe_person(p, "en") for p in tree.values()]
    assert len(set(descs)) == len(descs), "attribute descriptors must be unique"
    qs = generate_questions(tree, 200, language="en", anonymize_percentage=100)
    for q in qs:
        if q["type"] == "enigme":
            assert not q["anonymized"]
            continue
        names_in_text = [n for n in known if re.search(r"\b" + re.escape(n) + r"\b", q["question"])]
        assert not names_in_text, (q["question"], names_in_text)
    assert sum(q["anonymized"] for q in qs) >= 0.7 * sum(1 for q in qs if q["type"] != "enigme")
    none = generate_questions(tree, 100, language="en", anonymize_percentage=0)
    assert not any(q["anonymized"] for q in none)
    half = generate_questions(tree, 200, language="en", anonymize_percentage=50)
    share = sum(q["anonymized"] for q in half) / len(half)
    assert 0.25 < share < 0.75


def test_no_dangling_possessive_or_bad_article(tree):
    qs = generate_questions(tree, 200, language="en", anonymize_percentage=100)
    for q in qs:
        assert "hat's" not in q["question"], q["question"]
        assert not re.search(r"\ba [aeiou]", q["question"]), q["question"]


def test_fix_english_articles():
    assert fix_english_articles("works as a artist with a orange hat and a red one") == "works as an artist with an orange hat and a red one"


# ---------------------------------------------------------------- énigmes 7-9
def test_enigma_levels_1_to_9_are_generated_and_unambiguous(tree):
    qs = generate_questions(tree, 200, language="en", difficulty="enigma")
    levels = collections.Counter(q["complexity"] for q in qs)
    assert set(levels) >= {1, 2, 3, 4, 5, 6, 7, 8, 9}, levels
    known = {p.first_name for p in tree.values()}
    for q in qs:
        assert q["answer"] in known
        if q["complexity"] in (1, 2, 3, 4, 5, 7, 8):
            assert q["question"].startswith("Which "), q["question"]
            assert re.search(r" (has [a-z -]+ (hair|eyes)|wears an? [a-z -]+ hat)\?$", q["question"]), q["question"]
        if q["complexity"] == 8:
            assert "the person with" in q["question"]
        if q["complexity"] == 9:
            assert "the same" in q["question"]


def test_chain_engine_answers_are_correct(tree):
    """Vérification indépendante : la cible est bien dans le résultat de la chaîne."""
    random.seed(4)
    people = list(tree.values())
    for _ in range(50):
        start = random.choice(people)
        chain = E._random_chain(3)
        pool = E._apply_chain(start, chain, tree)
        # recalcul naïf
        current = {start.id}
        for key in chain:
            current = {r.id for pid in current for r in E.CHAIN_RELATIONS[key](tree[pid], tree)}
        assert {p.id for p in pool} == current


def test_french_chain_contractions():
    assert E._render_chain(["chain_son", "chain_child"], "Marc", "fr") == "l'enfant du fils de Marc"
    assert E._render_chain(["chain_father", "chain_daughter"], "Marc", "fr") == "la fille du père de Marc"
    assert E._render_chain(["chain_father", "chain_daughter"], "Marc", "en") == "the daughter of the father of Marc"


def test_expert_uses_high_levels(tree):
    qs = generate_questions(tree, 60, language="en", difficulty="expert")
    en = [q for q in qs if q["type"] == "enigme"]
    assert en and all(q["complexity"] in EXPERT_ENIGMA_COMPLEXITIES for q in en)
    assert sum(1 for q in en if q["complexity"] >= 7) >= 0.4 * 60 * 0.5


def test_census_questions_are_dropped(tree):
    qs = generate_questions(tree, 150, language="en", anonymize_percentage=0, drop_answer_names_above=40)
    assert all(not q["converted_to_count"] or q["original_answer_size"] <= 40 for q in qs)
    keep = generate_questions(tree, 150, language="en", anonymize_percentage=0, drop_answer_names_above=0)
    assert any(q["converted_to_count"] and q["original_answer_size"] > 40 for q in keep)
