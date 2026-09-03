import pytest

from tree_evaluator.evaluation.model_evaluator import ModelEvaluator
from tree_evaluator.evaluation.prompt_builder import PromptBuilder

parse = ModelEvaluator.parse_batch_answers


def test_json_object_keyed_by_number():
    assert parse('{"1": "Alice,Bob", "2": "3", "3": "None"}', 3) == ["Alice,Bob", "3", "None"]


def test_json_object_missing_key_does_not_shift():
    assert parse('{"1": "Alice", "3": "Carol"}', 3) == ["Alice", "", "Carol"]


def test_json_object_after_reasoning_and_fences():
    text = 'Let me think [1] about it... {"draft": 1}\n```json\n{"1": "Alice", "2": 4}\n```'
    assert parse(text, 2) == ["Alice", "4"]


def test_json_array_positional_and_lists():
    assert parse('["Alice", ["Bob", "Carol"], 2]', 3) == ["Alice", "Bob,Carol", "2"]


def test_json_object_with_list_values_is_preferred_over_inner_list():
    assert parse('{"1": ["Bob", "Carol"], "2": "None"}', 2) == ["Bob,Carol", "None"]


def test_numbered_lines_fallback():
    assert parse("1. Alice,Bob\n2) None\n**3**: 7", 3) == ["Alice,Bob", "None", "7"]


def test_garbage_gives_empty_answers():
    assert parse("I cannot answer that.", 2) == ["", ""]
    assert parse("", 2) == ["", ""]


def test_think_block_is_ignored():
    assert parse('<think>{"1": "wrong"}</think>{"1": "Right"}', 1) == ["Right"]


def test_batch_prompt_numbers_questions_and_asks_for_object():
    qs = [{"question": "Q one?"}, {"question": "Q two?"}]
    prompt = PromptBuilder.build_batch_prompt("TREE", qs, "en")
    assert "1. Q one?" in prompt and "2. Q two?" in prompt
    assert '{"1": "...", "2": "..."}' in prompt
    prompt_fr = PromptBuilder.build_batch_prompt("TREE", qs * 3, "fr")
    assert '"6": "..."' in prompt_fr
