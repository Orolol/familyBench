#!/usr/bin/env python
"""Extrapole le coût du protocole complet depuis un run de test (smoke).

    python scripts/estimate_cost.py evaluation_results/hard_v4_smoke/summary_<ts>.json --questions 60

Pour chaque entrée du résumé : tokens de prompt (cachés / non cachés) et de
sortie par question, coût du smoke si `pricing` était renseigné, et coût
projeté pour N questions. La projection suppose que la part de prompt cachée
sera au moins celle du smoke (en pratique elle monte avec le nombre de requêtes).
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary", type=Path)
    ap.add_argument("--questions", type=int, default=60, help="taille du protocole complet (défaut 60)")
    args = ap.parse_args()
    summ = json.loads(args.summary.read_text(encoding="utf-8"))
    print(f"{'entrée':28s} {'n':>3} {'prompt/q':>9} {'cached':>7} {'out/q':>8} {'acc':>6} {'coût smoke':>11} {'coût x{}'.format(args.questions):>11}")
    for name, s in summ["summary_stats"].items():
        n = s["total_questions"]
        if not n:
            continue
        factor = args.questions / n
        cost = s.get("total_cost_usd")
        cached = s["total_cached_tokens"] / s["total_prompt_tokens"] if s["total_prompt_tokens"] else 0
        print(f"{name:28s} {n:>3} {s['total_prompt_tokens']/n:>9,.0f} {cached:>7.0%} {s['total_completion_tokens']/n:>8,.0f} "
              f"{s['accuracy']:>6.0%} {('$%.3f' % cost) if cost is not None else 'n/a':>11} "
              f"{('$%.2f' % (cost * factor)) if cost is not None else 'n/a':>11}")
    print("\nn/a = pas de `pricing` dans la config pour cette entrée (tokens ci-dessus x tarifs du vendeur).")


if __name__ == "__main__":
    main()
