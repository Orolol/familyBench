import pytest

from tree_evaluator.evaluation.answer_cleaner import AnswerCleaner


c = AnswerCleaner()


@pytest.mark.parametrize("raw, expected", [
    ("Alice, Bob and Carol", "Alice,Bob,Carol"),
    ('"Alice,Bob".', "Alice,Bob"),
    ("<answer>Alice,Bob</answer>", "Alice,Bob"),
    ("Some reasoning...\n**Answer:** Alice", "Alice"),
    ("|begin_of_box|>Alice,Bob<|end_of_box|>", "Alice,Bob"),
    ("The answer is: Alice", "Alice"),
    ("three", "3"),
    ("nobody", "None"),
])
def test_clean_answer_en(raw, expected):
    assert c.clean_answer(raw, "en") == expected


def test_clean_answer_fr_none():
    assert c.clean_answer("None", "fr") == "Aucun"
    assert c.clean_answer("personne", "fr") == "Aucun"


@pytest.mark.parametrize("answer, expected", [
    ("", True), ("...", True), ("I don't know", True), ("Based on the text, nobody", True),
    ("3", False), ("Alice", False), ("Alice,Bob", False), ("None", False),
])
def test_is_no_response(answer, expected):
    assert c.is_no_response(answer) is expected


def test_exact_match_ignores_order_and_spaces():
    assert c.check_exact_match("Bob, Alice", "Alice,Bob")
    assert not c.check_exact_match("Alice", "Alice,Bob")


def test_partial_match_is_jaccard():
    assert c.calculate_partial_match("Alice,Bob", "Alice,Bob,Carol") == pytest.approx(2 / 3)
    assert c.calculate_partial_match("Alice", "alice") == 1.0
    assert c.calculate_partial_match("Alice", "Bob") == 0.0


def test_expected_answers_get_the_same_normalisation_as_model_answers():
    # le nettoyage transforme "salt and pepper" en "salt,pepper" côté modèle
    model = c.clean_answer("jet black, salt and pepper, black", "en")
    assert model == "jet black,salt,pepper,black"
    assert c.check_exact_match(model, "black,jet black,salt and pepper")
    assert c.calculate_partial_match(model, "black,jet black,salt and pepper") == 1.0
    assert c.check_exact_match("alice,BOB", "Bob,Alice")
