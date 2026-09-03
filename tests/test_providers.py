"""Adaptateurs par famille d'API : Anthropic Messages, OpenAI Responses, OpenAI-compatible."""
import json

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from tree_evaluator.evaluation.model_evaluator import ModelEvaluator

Q = {"id": 1, "question": "Who is Alice's father?", "answer": "Bob", "type": "relation_directe", "difficulty": "easy"}
BATCH = [Q, {"id": 2, "question": "Who is Bob's child?", "answer": "Alice", "type": "relation_directe", "difficulty": "easy"}]


def sse(obj, event=None):
    head = f"event: {event}\n" if event else ""
    return (head + f"data: {json.dumps(obj)}\n\n").encode()


# ------------------------------------------------------------------ Anthropic
@pytest.mark.asyncio
async def test_anthropic_messages_streaming():
    seen = {}

    async def messages(request):
        seen["headers"] = dict(request.headers)
        seen["body"] = await request.json()
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        await resp.write(sse({"type": "message_start", "message": {"usage": {"input_tokens": 20, "cache_read_input_tokens": 500, "cache_creation_input_tokens": 0, "output_tokens": 1}}}, "message_start"))
        await resp.write(sse({"type": "ping"}, "ping"))
        await resp.write(sse({"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "hmm"}}, "content_block_delta"))
        await resp.write(sse({"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Bob"}}, "content_block_delta"))
        await resp.write(sse({"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 42}}, "message_delta"))
        await resp.write(sse({"type": "message_stop"}, "message_stop"))
        return resp

    app = web.Application(); app.router.add_post("/v1/messages", messages)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        m = ModelEvaluator({"name": "claude@high", "api_base": f"http://127.0.0.1:{server.port}/v1", "api": "anthropic",
                            "api_key": "sk-test", "model": "claude-opus-5", "effort": "high", "max_tokens_per_question": 1000})
        m.set_known_names(["Alice", "Bob"])
        r = await m.evaluate_question("TREE", Q, session, timeout=10, language="en")
    h = seen["headers"]; b = seen["body"]
    assert h["x-api-key"] == "sk-test" and h["anthropic-version"] == "2023-06-01" and "Authorization" not in h
    assert b["model"] == "claude-opus-5" and b["max_tokens"] == 1000 and b["stream"] is True
    assert b["thinking"] == {"type": "adaptive"} and b["output_config"] == {"effort": "high"}
    assert "temperature" not in b
    # arbre dans un bloc système avec cache_control, question dans le message utilisateur
    assert b["system"][1]["cache_control"] == {"type": "ephemeral"} and "TREE" in b["system"][1]["text"]
    assert "Question: Who is Alice's father?" in b["messages"][0]["content"] and "TREE" not in b["messages"][0]["content"]
    assert r.model_answer == "Bob" and r.is_correct and r.finish_reason == "stop"
    assert r.reasoning_text == "hmm" and r.tokens_used == 42 and r.prompt_tokens == 520 and r.cached_tokens == 500
    assert r.thinking_level == "high" and r.provider == "anthropic"


@pytest.mark.asyncio
async def test_anthropic_max_tokens_stop_reason_and_batch_cap():
    seen = {}

    async def messages(request):
        seen["body"] = await request.json()
        return web.json_response({"content": [{"type": "text", "text": '{"1": "Bob", "2": "Alice"}'}],
                                  "stop_reason": "max_tokens", "usage": {"input_tokens": 5, "output_tokens": 7}})

    app = web.Application(); app.router.add_post("/v1/messages", messages)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        m = ModelEvaluator({"name": "c", "api_base": f"http://127.0.0.1:{server.port}/v1", "api": "anthropic",
                            "api_key": "k", "model": "m", "max_tokens_per_question": 16000, "stream": False})
        results = await m.evaluate_questions_batch("TREE", BATCH, session, timeout=10, language="en")
    assert seen["body"]["max_tokens"] == 32000, "plafond par question x taille du batch"
    assert [r.model_answer for r in results] == ["Bob", "Alice"]
    assert all(r.finish_reason == "length" for r in results)


# ------------------------------------------------------------------ OpenAI Responses
@pytest.mark.asyncio
async def test_openai_responses_streaming():
    seen = {}

    async def responses(request):
        seen["body"] = await request.json()
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        await resp.write(sse({"type": "response.created", "response": {}}, "response.created"))
        await resp.write(sse({"type": "response.reasoning_summary_text.delta", "delta": "thinking "}, "response.reasoning_summary_text.delta"))
        await resp.write(sse({"type": "response.output_text.delta", "delta": "Bo"}, "response.output_text.delta"))
        await resp.write(sse({"type": "response.output_text.delta", "delta": "b"}, "response.output_text.delta"))
        await resp.write(sse({"type": "response.completed", "response": {"status": "completed",
                              "usage": {"input_tokens": 30, "output_tokens": 9, "input_tokens_details": {"cached_tokens": 24},
                                        "output_tokens_details": {"reasoning_tokens": 6}}}}, "response.completed"))
        return resp

    app = web.Application(); app.router.add_post("/v1/responses", responses)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        m = ModelEvaluator({"name": "gpt@xhigh", "api_base": f"http://127.0.0.1:{server.port}/v1", "api": "openai_responses",
                            "api_key": "k", "model": "gpt-5.5", "effort": "xhigh", "max_tokens_per_question": 2000})
        r = await m.evaluate_question("TREE", Q, session, timeout=10, language="en")
    b = seen["body"]
    assert b["reasoning"] == {"effort": "xhigh"} and b["max_output_tokens"] == 2000 and "temperature" not in b
    assert r.model_answer == "Bob" and r.is_correct and r.reasoning_tokens == 6 and r.cached_tokens == 24
    assert r.reasoning_text == "thinking " and r.finish_reason == "stop" and r.thinking_level == "xhigh"


# ------------------------------------------------------------------ OpenAI-compatible vendors
@pytest.mark.asyncio
async def test_openai_compatible_effort_extra_body_and_vendor_cache_fields():
    seen = {}

    async def chat(request):
        seen["body"] = await request.json()
        return web.json_response({"choices": [{"message": {"content": "Bob", "reasoning_content": "r"}, "finish_reason": "stop"}],
                                  "usage": {"prompt_tokens": 50, "completion_tokens": 3, "prompt_cache_hit_tokens": 40,
                                            "completion_tokens_details": {"reasoning_tokens": 2}}})

    app = web.Application(); app.router.add_post("/v1/chat/completions", chat)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        m = ModelEvaluator({"name": "deepseek@max", "api_base": f"http://127.0.0.1:{server.port}/v1", "api_key": "k",
                            "model": "deepseek-v4-flash", "effort": "max", "thinking_level": "max", "effort_param": "thinking",
                            "extra_body": {"thinking": {"type": "enabled"}}, "max_tokens_per_question": 16000, "stream": False})
        r = await m.evaluate_question("TREE", Q, session, timeout=10, language="en")
    b = seen["body"]
    assert "reasoning_effort" not in b and b["thinking"] == {"type": "enabled", "reasoning_effort": "max"} and b["max_tokens"] == 16000
    assert "temperature" not in b and "reasoning" not in b
    assert r.cached_tokens == 40 and r.reasoning_tokens == 2 and r.is_correct


def test_openrouter_keeps_its_reasoning_shape_and_temperature_when_given():
    m = ModelEvaluator({"name": "r", "api_base": "https://openrouter.ai/api/v1", "api_key": "k", "model": "m",
                        "effort": "high", "provider": {"order": ["baidu/fp8"]}, "temperature": 0.3})
    d = m._build_api_request("p", "en")
    assert d["reasoning"] == {"effort": "high"} and d["provider"] == {"order": ["baidu/fp8"]} and d["temperature"] == 0.3
    assert "reasoning_effort" not in d


def test_entry_metadata_and_moonshot_cached_tokens():
    m = ModelEvaluator({"name": "kimi@high", "api_base": "https://api.moonshot.ai/v1", "api_key": "k", "model": "kimi-k3",
                        "effort": "high", "max_tokens_per_question": 16000})
    meta = m.entry_metadata()
    assert meta["thinking_level"] == "high" and meta["max_tokens"] == 16000 and meta["api"] == "openai_chat"
    out = m._extract_api_response({"choices": [{"message": {"content": "Bob"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 1, "cached_tokens": 8}})
    assert out[5] == 8


def test_default_effort_param_is_reasoning_effort_for_openai_compatible():
    m = ModelEvaluator({"name": "glm@high", "api_base": "https://api.z.ai/api/paas/v4", "api_key": "k", "model": "glm-5.3",
                        "effort": "high", "extra_body": {"thinking": {"type": "enabled"}}})
    d = m._build_api_request("p", "en")
    assert d["reasoning_effort"] == "high" and d["thinking"] == {"type": "enabled"}


def test_openrouter_reasoning_details_streaming_fallback():
    m = ModelEvaluator({"name": "r", "api_base": "https://openrouter.ai/api/v1", "api_key": "k", "model": "m"})
    acc = {"content": [], "reasoning": [], "usage": {}, "finish_reason": None, "provider": None, "role": "assistant", "error": None}
    assert m._consume_event({"choices": [{"delta": {"reasoning_details": [{"type": "reasoning.text", "text": "abc"}]}}]}, acc)
    assert m._consume_event({"choices": [{"delta": {"reasoning": "def", "reasoning_details": [{"type": "reasoning.text", "text": "def"}]}}]}, acc)
    assert "".join(acc["reasoning"]) == "abcdef", "no double counting when both fields are present"


def test_budget_param_scales_with_batch_size():
    m = ModelEvaluator({"name": "qwen@b16k", "api_base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "api_key": "k",
                        "model": "qwen3.8-max", "effort_param": "none", "thinking_level": "budget16k", "budget_param": "thinking_budget",
                        "max_tokens_per_question": 16000, "extra_body": {"enable_thinking": True}})
    d = m._build_api_request("p", "en", batch=True, n_questions=5)
    assert d["thinking_budget"] == 80000 and d["max_tokens"] == 80000 and d["enable_thinking"] is True
    assert "reasoning_effort" not in d


def test_openai_requests_carry_a_stable_prompt_cache_key():
    m = ModelEvaluator({"name": "o", "api_base": "https://api.openai.com/v1", "api_key": "k", "model": "gpt-5.6", "api": "openai_responses", "effort": "high"})
    a = m._build_api_request("TREE\n\nQ1", "en", parts=("TREE", "Q1"))
    b = m._build_api_request("TREE\n\nQ2", "en", parts=("TREE", "Q2"))
    assert a["prompt_cache_key"] == b["prompt_cache_key"] and a["prompt_cache_key"].startswith("familybench-")
    r = ModelEvaluator({"name": "r", "api_base": "https://openrouter.ai/api/v1", "api_key": "k", "model": "m"})
    assert "prompt_cache_key" not in r._build_api_request("p", "en")
