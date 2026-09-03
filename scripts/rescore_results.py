#!/usr/bin/env python
"""Re-score des fichiers de résultats avec le scoring courant.

Utile après une correction du nettoyage/scoring : recalcule is_exact_match,
partial_match_score et is_correct à partir de model_answer / expected_answer
(déjà nettoyés), puis réécrit results_*.json, results_*.csv et le
summary_*.json correspondant. Les champs d'origine sont conservés dans
"rescored_from" du summary.

    python scripts/rescore_results.py evaluation_results/batch_sweep_deepseek/results_*.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tree_evaluator.evaluation.answer_cleaner import AnswerCleaner  # noqa: E402
from tree_evaluator.evaluation.model_evaluator import ModelEvaluator  # noqa: E402
from tree_evaluator.evaluation.result import EvaluationResult  # noqa: E402
from tree_evaluator.evaluation.stats import calculate_summary_stats  # noqa: E402
from tree_evaluator.evaluation.io import save_results_csv, save_results_json  # noqa: E402


def rescore(path: Path) -> None:
    rows = json.loads(path.read_text(encoding="utf-8"))
    cleaner = AnswerCleaner()
    changed = 0
    results = []
    for r in rows:
        before = r["is_correct"]
        if r.get("error") or r.get("no_response") or not r["model_answer"]:
            r["is_exact_match"], r["partial_match_score"], r["is_correct"] = False, 0.0, False
        else:
            r["is_exact_match"] = cleaner.check_exact_match(r["model_answer"], r["expected_answer"])
            r["partial_match_score"] = cleaner.calculate_partial_match(r["model_answer"], r["expected_answer"])
            r["is_correct"] = r["is_exact_match"] or r["partial_match_score"] >= ModelEvaluator.CORRECT_PARTIAL_THRESHOLD
        changed += (before != r["is_correct"])
        results.append(EvaluationResult(**{k: v for k, v in r.items() if k in EvaluationResult.__dataclass_fields__}))
    save_results_json(results, path)
    save_results_csv(results, path.with_suffix(".csv"))
    ts = path.stem.replace("results_", "")
    summary_path = path.with_name(f"summary_{ts}.json")
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        by_model = {}
        for r in results:
            by_model.setdefault(r.model_name, []).append(r)
        summary["rescored_from"] = {m: s.get("accuracy") for m, s in summary["summary_stats"].items()}
        summary["summary_stats"] = {m: calculate_summary_stats(rs) for m, rs in by_model.items()}
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path.name}: {changed} verdict(s) changed; accuracy now "
          f"{sum(r.is_correct for r in results) / len(results):.1%}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        rescore(Path(arg))
