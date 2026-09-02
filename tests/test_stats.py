from tree_evaluator.evaluation.result import EvaluationResult
from tree_evaluator.evaluation.stats import calculate_summary_stats


def r(**kw):
    base = dict(model_name="m", benchmark_name="b", question_id=1, question="q", expected_answer="a",
                model_answer="a", is_correct=True, is_exact_match=True, partial_match_score=1.0,
                response_time=1.0, tokens_used=10)
    base.update(kw)
    return EvaluationResult(**base)


def test_summary_groups_by_type_and_difficulty_and_counts_hallucinations():
    results = [
        r(question_type="relation_directe", difficulty="easy"),
        r(question_type="relation_directe", difficulty="easy", is_correct=False, is_exact_match=False,
          model_answer="Zed", hallucinated_names=1),
        r(question_type="enigme", difficulty="enigma", is_enigma=True, enigma_complexity=5),
        r(question_type="multihop", difficulty="hard", error="Timeout", model_answer="", is_correct=False,
          is_exact_match=False),
    ]
    s = calculate_summary_stats(results)
    assert s["total_questions"] == 4 and s["correct_answers"] == 2
    assert s["by_question_type"]["relation_directe"] == {"total": 2, "correct": 1, "accuracy": 0.5}
    assert s["by_difficulty"]["hard"]["total"] == 1
    assert s["by_difficulty"]["enigma"]["accuracy"] == 1.0
    assert s["enigma_stats"]["by_complexity"][5]["total"] == 1
    # 3 réponses exploitables (l'erreur est exclue), 1 contient un nom inconnu
    assert s["hallucination_rate"] == 1 / 3
    assert s["total_hallucinated_names"] == 1
    assert s["errors"] == 1


def test_empty():
    assert calculate_summary_stats([]) == {}
