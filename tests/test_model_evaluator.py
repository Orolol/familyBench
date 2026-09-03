import asyncio

import pytest

from tree_evaluator.evaluation.model_evaluator import ModelEvaluator


def make(api_base="https://openrouter.ai/api/v1", **extra):
    cfg = {"name": "test-model", "api_base": api_base, "api_key": "none", "model": "m"}
    cfg.update(extra)
    return ModelEvaluator(cfg)


def test_request_routing_openai_chat():
    m = make(max_tokens=123)
    assert m._get_api_url().endswith("/chat/completions")
    data = m._build_api_request("p", "en")
    assert data["max_tokens"] == 123 and data["messages"][1]["content"] == "p"


def test_request_routing_openai_responses_api():
    m = make(api_base="https://api.openai.com/v1", reasoning={"effort": "low"}, max_completion_tokens=50)
    assert m._get_api_url().endswith("/responses")
    data = m._build_api_request("p", "en")
    assert data["max_output_tokens"] == 50 and data["reasoning"] == {"effort": "low"}
    assert "messages" not in data and data["input"][1]["content"] == "p"


def test_request_routing_anthropic():
    m = make(api_base="https://api.anthropic.com/v1", max_tokens=10)
    assert m._get_api_url().endswith("/messages")


def test_extract_chat_completions():
    m = make()
    out = m._extract_api_response({
        "choices": [{"message": {"content": "Alice,Bob", "reasoning": "hmm hmm"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 7,
                  "prompt_tokens_details": {"cached_tokens": 40},
                  "completion_tokens_details": {"reasoning_tokens": 12}},
    })
    assert out == ("Alice,Bob", 7, 12, "hmm hmm", 100, 40)


def test_extract_responses_api():
    m = make(api_base="https://api.openai.com/v1", reasoning={"effort": "low"})
    out = m._extract_api_response({
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": " Alice "}]},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5,
                  "output_tokens_details": {"reasoning_tokens": 3},
                  "input_tokens_details": {"cached_tokens": 1}},
    })
    assert out == ("Alice", 5, 3, None, 10, 1)


def test_extract_anthropic():
    m = make(api_base="https://api.anthropic.com/v1")
    out = m._extract_api_response({"content": [{"type": "text", "text": "Bob"}],
                                   "usage": {"input_tokens": 9, "output_tokens": 2}})
    assert out[0] == "Bob" and out[1] == 2 and out[4] == 9


def test_compute_cost():
    assert make()._compute_cost(1000, 100, 0) is None
    m = make(pricing={"input_per_mtok": 1.0, "output_per_mtok": 10.0, "cached_input_per_mtok": 0.1})
    assert m._compute_cost(1_000_000, 100_000, 500_000) == pytest.approx(0.5 + 0.05 + 1.0)


def test_hallucination_count():
    m = make()
    m.set_known_names(["Alice", "Bob"])
    assert m.count_hallucinated_names("Alice,Bob") == 0
    assert m.count_hallucinated_names("Alice,Zed,Yann") == 2
    assert m.count_hallucinated_names("3") == 0
    assert m.count_hallucinated_names("None") == 0
    assert make().count_hallucinated_names("Zed") == 0  # no known names -> disabled
    # expected answer is an attribute / label, not names: detection disabled
    assert m.count_hallucinated_names("blue,Zed", expected_answer="blue") == 0
    assert m.count_hallucinated_names("Zed", expected_answer="Alice,Bob") == 1


QUESTION = {"id": 1, "question": "Who is Alice's father?", "answer": "Bob", "type": "relation_directe", "difficulty": "easy"}


def test_cache_hit_returns_a_result_without_network():
    """Régression : sur cache hit, la fonction renvoyait None."""
    m = make()
    m.set_known_names(["Alice", "Bob"])
    data = m._build_api_request(m.prompt_builder.build_single_question_prompt("tree", QUESTION["question"], "en"), "en")
    m.cache_manager.set({"model": m.name, "url": m._get_api_url(), "data": data},
                        {"choices": [{"message": {"content": "Bob"}}], "usage": {"completion_tokens": 1}})
    result = asyncio.run(m._evaluate_question_single_attempt("tree", QUESTION, session=None, timeout=5,
                                                             language="en", total_start_time=0.0))
    assert result is not None and result.error is None
    assert result.model_answer == "Bob" and result.is_correct
    assert result.difficulty == "easy" and result.hallucinated_names == 0


def test_cache_hit_batch_returns_results_without_network():
    m = make()
    qs = [QUESTION, {"id": 2, "question": "Who is Bob's child?", "answer": "Alice", "type": "relation_directe", "difficulty": "easy"}]
    data = m._build_api_request(m.prompt_builder.build_batch_prompt("tree", qs, "en"), "en", batch=True)
    m.cache_manager.set({"model": m.name, "url": m._get_api_url(), "data": data},
                        {"choices": [{"message": {"content": '["Bob", "Alice"]'}}], "usage": {"completion_tokens": 4}})
    results = asyncio.run(m._evaluate_questions_batch_single_attempt("tree", qs, session=None, timeout=5,
                                                                     language="en", total_start_time=0.0))
    assert [r.model_answer for r in results] == ["Bob", "Alice"]
    assert all(r.is_correct for r in results)


def test_error_result_keeps_difficulty():
    r = make()._create_error_result(QUESTION, "boom", 0.1)
    assert r.error == "boom" and r.difficulty == "easy" and not r.is_correct


def test_empty_or_truncated_responses_are_not_cached_and_retries_bypass_cache():
    m = make()
    data = m._build_api_request(m.prompt_builder.build_single_question_prompt("tree", QUESTION["question"], "en"), "en")
    key = {"model": m.name, "url": m._get_api_url(), "data": data}
    # une réponse tronquée déjà en cache ne doit pas être relue lors d'un retry
    m.cache_manager.set(key, {"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {}})
    hit = asyncio.run(m._evaluate_question_single_attempt("tree", QUESTION, session=None, timeout=5,
                                                          language="en", total_start_time=0.0, use_cache=True))
    assert hit.no_response and hit.finish_reason == "length"
    # use_cache=False -> tente le réseau (session None => erreur capturée, pas de relecture du cache)
    miss = asyncio.run(m._evaluate_question_single_attempt("tree", QUESTION, session=None, timeout=5,
                                                           language="en", total_start_time=0.0, use_cache=False))
    assert miss.error and "NoneType" in miss.error


def test_truncated_generation_is_not_retried():
    m = make()
    data = m._build_api_request(m.prompt_builder.build_single_question_prompt("tree", QUESTION["question"], "en"), "en")
    m.cache_manager.set({"model": m.name, "url": m._get_api_url(), "data": data},
                        {"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {}})
    # session=None : un retry tenterait le réseau et produirait une erreur "NoneType"
    r = asyncio.run(m.evaluate_question("tree", QUESTION, session=None, timeout=5, language="en"))
    assert r.no_response and r.finish_reason == "length" and r.error is None
