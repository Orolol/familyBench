import collections
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tree_evaluator.tree_generator import generate_tree
from tree_evaluator.question_generator import (
    generate_questions, DIFFICULTY_TIERS, VALID_DIFFICULTIES, difficulty_for_type,
    EXPERT_ENIGMA_COMPLEXITIES,
)


@pytest.fixture(scope="module")
def tree():
    return generate_tree(120, 5, 3, seed=42, num_root_couples=3, language="en")


# Types dont la réponse n'est pas une liste de prénoms (attribut ou libellé de relation)
NON_NAME_ANSWER_TYPES = {"multihop", "relational_path"}


def _names_in_answer(answer):
    if answer in ("None", "Aucun") or answer.isdigit():
        return []
    return answer.split(",")


def test_requested_count_is_delivered(tree):
    qs = generate_questions(tree, 150, language="en", enigma_percentage=10)
    assert len(qs) == 150
    assert [q["id"] for q in qs] == list(range(1, 151))


def test_every_question_has_a_valid_answer(tree):
    known = {p.first_name for p in tree.values()}
    qs = generate_questions(tree, 200, language="en", enigma_percentage=20, max_answer_names=0)
    for q in qs:
        assert q["answer"], q
        if q["type"] in NON_NAME_ANSWER_TYPES:
            continue
        for name in _names_in_answer(q["answer"]):
            assert name in known, f"answer references unknown name {name!r} in {q}"
        if "," in q["answer"]:
            parts = q["answer"].split(",")
            assert parts == sorted(parts) and len(set(parts)) == len(parts)


def test_difficulty_is_stamped_on_every_question(tree):
    qs = generate_questions(tree, 100, language="en")
    for q in qs:
        assert q["difficulty"] in DIFFICULTY_TIERS
        assert q["difficulty"] == difficulty_for_type(q["type"])
        if q["type"] == "enigme":
            assert q["difficulty"] == "enigma"


def test_all_mode_is_balanced_across_types(tree):
    qs = generate_questions(tree, 200, language="en", enigma_percentage=10)
    counts = collections.Counter(q["type"] for q in qs if q["type"] != "enigme")
    assert len(counts) >= 12, "most question types should be represented"
    assert max(counts.values()) <= 0.2 * 180, f"one type dominates: {counts.most_common(3)}"
    assert sum(1 for q in qs if q["type"] == "enigme") == 20


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_tier_mode_only_returns_that_tier(tree, tier):
    qs = generate_questions(tree, 40, language="en", difficulty=tier)
    assert qs
    assert {q["type"] for q in qs} <= DIFFICULTY_TIERS[tier]
    assert {q["difficulty"] for q in qs} == {tier}


def test_expert_mode(tree):
    qs = generate_questions(tree, 60, language="en", difficulty="expert")
    assert len(qs) == 60
    enigmas = [q for q in qs if q["type"] == "enigme"]
    assert enigmas and all(q["complexity"] in EXPERT_ENIGMA_COMPLEXITIES for q in enigmas)
    assert len([q for q in enigmas if q["complexity"] >= 7]) >= 0.4 * 60 * 0.5  # au moins une part de niveaux 7-9
    normal_types = {q["type"] for q in qs if q["type"] != "enigme"}
    assert normal_types <= DIFFICULTY_TIERS["hard"]


def test_invalid_difficulty(tree):
    with pytest.raises(ValueError):
        generate_questions(tree, 10, difficulty="impossible")
    assert "all" in VALID_DIFFICULTIES


def test_french_generation_works():
    tree = generate_tree(60, 4, 3, seed=5, num_root_couples=2, language="fr")
    qs = generate_questions(tree, 50, language="fr")
    assert len(qs) == 50
    assert all(q["answer"] for q in qs)


def test_relational_path_answers_are_translated():
    tree = generate_tree(60, 4, 3, seed=3, num_root_couples=1, language="en")
    qs = [q for q in generate_questions(tree, 300, language="en") if q["type"] == "relational_path"]
    assert qs
    labels = {q["answer"] for q in qs if not q["answer"].isdigit()}
    assert labels <= {"parent-child", "cousins"}, labels


def _questions_hash_in_subprocess(hash_seed: str) -> str:
    code = (
        "import json, hashlib;"
        "from tree_evaluator.tree_generator import generate_tree;"
        "from tree_evaluator.question_generator import generate_questions;"
        "t = generate_tree(60, 4, 3, seed=11, num_root_couples=1, language='en');"
        "qs = generate_questions(t, 40, language='en');"
        "print(hashlib.md5(json.dumps([q['question'] for q in qs]).encode()).hexdigest())"
    )
    env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def test_generation_is_reproducible_across_processes():
    """Même seed => mêmes questions, quel que soit le hash seed Python du process."""
    assert _questions_hash_in_subprocess("0") == _questions_hash_in_subprocess("1")
