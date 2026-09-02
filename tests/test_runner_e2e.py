"""Évaluation de bout en bout contre un faux serveur OpenAI-compatible local."""
import json
import re

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from tree_evaluator.evaluation.model_evaluator import ModelEvaluator
from tree_evaluator.evaluation.runner import run_benchmark_evaluation
from tree_evaluator.evaluation.stats import calculate_summary_stats
from tree_evaluator.tree_generator import generate_tree
from tree_evaluator.question_generator import generate_questions

BENCH = {"name": "tiny", "people": 25, "depth": 3, "questions": 12, "root_couples": 1, "seed": 9, "language": "en"}


def _oracle():
    """Réponses attendues, calculées comme le runner le fera (même seed)."""
    tree = generate_tree(BENCH["people"], BENCH["depth"], seed=BENCH["seed"], num_root_couples=1, language="en")
    known = {p.first_name for p in tree.values()}
    answers = {q["question"]: q["answer"] for q in generate_questions(tree, BENCH["questions"], language="en")}
    return answers, known


@pytest.mark.asyncio
async def test_end_to_end_against_fake_server():
    answers, known = _oracle()
    calls = {"n": 0}

    async def chat(request):
        calls["n"] += 1
        body = await request.json()
        prompt = body["messages"][-1]["content"]
        question = re.search(r"Question: (.*)", prompt).group(1).strip()
        answer = answers[question]
        # une réponse sur trois (parmi les réponses "liste de prénoms") contient
        # un nom inventé pour tester la détection d'hallucinations
        if calls["n"] % 3 == 0 and all(t in known for t in answer.split(",")):
            answer = answer + ",Zorglub"
        return web.json_response({"choices": [{"message": {"content": answer}}],
                                  "usage": {"prompt_tokens": 50, "completion_tokens": 5}})

    app = web.Application()
    app.router.add_post("/v1/chat/completions", chat)
    async with TestServer(app) as server:
        model = ModelEvaluator({"name": "fake", "api_base": f"http://127.0.0.1:{server.port}/v1",
                                "api_key": "none", "model": "fake"})
        run = await run_benchmark_evaluation(model, BENCH, timeout=10, batch_size=1, max_concurrent=4)

    assert len(run.results) == BENCH["questions"]
    assert run.benchmark_fingerprint and run.tree_depth_actual <= BENCH["depth"]
    assert all(r.error is None for r in run.results)
    assert all(r.difficulty is not None for r in run.results)
    stats = calculate_summary_stats(run.results)
    assert stats["by_difficulty"] and stats["by_question_type"]
    hallucinated = [r for r in run.results if r.hallucinated_names > 0]
    assert hallucinated, "the injected unknown name must be detected"
    assert all(not r.is_exact_match for r in hallucinated)
    clean = [r for r in run.results if r.hallucinated_names == 0]
    assert all(r.is_correct for r in clean)
    assert stats["hallucination_rate"] == pytest.approx(len(hallucinated) / len(run.results))
