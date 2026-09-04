"""Générateur 4.1 : errata dispersés, énumérations complètes, liste blanche de types, scoring exact."""
import collections
import random

import pytest

from tree_evaluator.tree_generator import generate_tree
from tree_evaluator.text_converter import build_description_facts, convert_tree_to_text_with_facts
from tree_evaluator.question_generator import generate_questions
from tree_evaluator.questions.enumeration import generate_enumeration_questions, MIN_NAMES, MAX_NAMES
from tree_evaluator.evaluation.model_evaluator import ModelEvaluator


@pytest.fixture(scope="module")
def tree():
    return generate_tree(300, 7, 2, seed=21, num_root_couples=3, language="en")


def test_errata_are_wrong_then_corrected_and_tree_is_recoverable(tree):
    rng = random.Random(3)
    facts = build_description_facts(tree, "en", "mixed", derived_links_percentage=30, rng=rng, errata_percentage=25)
    errata = [f for f in facts if f["kind"] == "erratum"]
    corrupted = [f for f in facts if f.get("corrupted")]
    assert errata and len(errata) == len(corrupted)
    for f in corrupted:
        assert f["parent_id"] not in tree[f["person_id"]].parent_ids, "the stated link must be false"
        assert tree[f["parent_id"]].gender == tree[f["true_parent_id"]].gender
    # reconstruction : liens directs, liens faux remplacés par la correction, liens dérivés via l'ancre
    parents = collections.defaultdict(set)
    for f in facts:
        if f["kind"] == "link":
            parents[f["person_id"]].add(f["true_parent_id"] if f.get("corrupted") else f["parent_id"])
    for f in facts:
        if f["kind"] == "derived":
            parents[f["person_id"]] = set(parents[f["anchor_id"]])
    for p in tree.values():
        assert parents.get(p.id, set()) == set(p.parent_ids), p.first_name
    text, facts2 = convert_tree_to_text_with_facts(tree, shuffle=True, language="en", seed=5, derived_links_percentage=30, errata_percentage=25)
    assert text.count("Correction:") == len([f for f in facts2 if f["kind"] == "erratum"]) > 0
    assert "the correction prevails" in text.splitlines()[0]
    assert "Correction:" not in convert_tree_to_text_with_facts(tree, language="en", errata_percentage=0)[0]


def test_enumeration_questions_have_medium_sized_exact_answers(tree):
    qs = generate_enumeration_questions(tree, "en")
    assert qs
    known = {p.first_name for p in tree.values()}
    for q in qs:
        names = q["answer"].split(",")
        assert MIN_NAMES <= len(names) <= MAX_NAMES and set(names) <= known and names == sorted(names)
        assert q["type"] == "enumeration"


def test_include_types_and_no_count_conversion_for_enumeration(tree):
    qs = generate_questions(tree, 60, language="en", difficulty="hard", include_types=["enumeration", "multihop"],
                            max_answer_names=12, anonymize_percentage=0)
    assert {q["type"] for q in qs} <= {"enumeration", "multihop"} and len(qs) == 60
    assert not any(q["converted_to_count"] for q in qs if q["type"] == "enumeration")


def test_partial_threshold_exact_only():
    m = ModelEvaluator({"name": "x", "api_base": "https://openrouter.ai/api/v1", "api_key": "k", "model": "m", "partial_threshold": 1.0})
    assert m.partial_threshold == 1.0 and m.entry_metadata()["partial_threshold"] == 1.0
    assert ModelEvaluator({"name": "y", "api_base": "https://openrouter.ai/api/v1", "api_key": "k", "model": "m"}).partial_threshold == 0.9
