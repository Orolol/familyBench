"""Streaming SSE : ré-assemblage des chunks en réponse non-streamée."""
import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from tree_evaluator.evaluation.model_evaluator import ModelEvaluator

Q = {"id": 1, "question": "Who is Alice's father?", "answer": "Bob", "type": "relation_directe", "difficulty": "easy"}


def sse(obj):
    return f"data: {json.dumps(obj)}\n\n".encode()


@pytest.mark.asyncio
async def test_streaming_reassembles_content_reasoning_and_usage():
    seen = {}

    async def chat(request):
        body = await request.json()
        seen.update(body)
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        await resp.write(b": keep-alive\n\n")
        await resp.write(sse({"choices": [{"delta": {"role": "assistant", "reasoning": "let me "}}]}))
        await resp.write(sse({"choices": [{"delta": {"reasoning_content": "think"}}]}))
        await resp.write(sse({"choices": [{"delta": {"content": "B"}}]}))
        await resp.write(sse({"choices": [{"delta": {"content": "ob"}, "finish_reason": "stop"}]}))
        await resp.write(sse({"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 3,
                                                       "completion_tokens_details": {"reasoning_tokens": 2}}}))
        await resp.write(b"data: [DONE]\n\n")
        return resp

    app = web.Application(); app.router.add_post("/v1/chat/completions", chat)
    async with TestServer(app) as server, __import__("aiohttp").ClientSession() as session:
        m = ModelEvaluator({"name": "s", "api_base": f"http://127.0.0.1:{server.port}/v1", "api_key": "none", "model": "m"})
        m.set_known_names(["Alice", "Bob"])
        r = await m.evaluate_question("tree", Q, session, timeout=10, language="en")
    assert seen["stream"] is True and seen["stream_options"] == {"include_usage": True}
    assert r.error is None and r.model_answer == "Bob" and r.is_correct
    assert r.reasoning_text == "let me think" and r.reasoning_tokens == 2
    assert r.prompt_tokens == 12 and r.tokens_used == 3


@pytest.mark.asyncio
async def test_streaming_error_event_and_disable():
    async def chat(request):
        body = await request.json()
        if body.get("stream"):
            resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
            await resp.prepare(request)
            await resp.write(sse({"error": {"message": "provider overloaded"}}))
            return resp
        return web.json_response({"choices": [{"message": {"content": "Bob"}}], "usage": {}})

    app = web.Application(); app.router.add_post("/v1/chat/completions", chat)
    async with TestServer(app) as server, __import__("aiohttp").ClientSession() as session:
        base = f"http://127.0.0.1:{server.port}/v1"
        m = ModelEvaluator({"name": "s", "api_base": base, "api_key": "none", "model": "m"})
        r = await m.evaluate_question("tree", Q, session, timeout=10, language="en")
        assert r.error and "provider overloaded" in r.error
        m2 = ModelEvaluator({"name": "s", "api_base": base, "api_key": "none", "model": "m", "stream": False})
        r2 = await m2.evaluate_question("tree", Q, session, timeout=10, language="en")
        assert r2.model_answer == "Bob"


def test_streaming_not_used_for_anthropic_or_responses_api():
    assert not ModelEvaluator({"name": "a", "api_base": "https://api.anthropic.com/v1", "api_key": "k", "model": "m"})._uses_streaming()
    assert not ModelEvaluator({"name": "o", "api_base": "https://api.openai.com/v1", "api_key": "k", "model": "m", "reasoning": {"effort": "low"}})._uses_streaming()
    assert ModelEvaluator({"name": "r", "api_base": "https://openrouter.ai/api/v1", "api_key": "k", "model": "m"})._uses_streaming()
