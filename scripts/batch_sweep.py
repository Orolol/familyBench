#!/usr/bin/env python
"""Compare l'effet de la taille de batch sur un même modèle et un même benchmark.

Lance evaluate.py une fois par taille de batch (mêmes seed, modèle et
questions), puis affiche un tableau comparatif : accuracy, exact match,
non-réponses, erreurs, tokens (prompt / complétion / raisonnement), coût et
durée, plus l'accuracy par tier de difficulté et l'accord question par
question avec le batch de référence (le plus petit).

Exemple :
    python scripts/batch_sweep.py --config evaluation_config_batch_sweep.yaml --batch-sizes 1 5 10 20
    python scripts/batch_sweep.py --config evaluation_config_batch_sweep.yaml --batch-sizes 1 10 20 --runs 2
    python scripts/batch_sweep.py --report-only evaluation_results/batch_sweep   # ré-afficher sans relancer
"""

import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_one(config: str, batch_size: int, runs: int, output_dir: Path, extra: list) -> Path:
    """Lance evaluate.py et renvoie le chemin du summary produit."""
    before = set(output_dir.glob("summary_*.json"))
    cmd = [sys.executable, str(ROOT / "evaluate.py"), "--config", config,
           "--batch-size", str(batch_size), "--runs", str(runs), "--output-dir", str(output_dir), *extra]
    print(f"\n>>> batch_size={batch_size}: {' '.join(cmd)}", flush=True)
    t0 = time.time()
    subprocess.run(cmd, cwd=ROOT, check=True)
    new = sorted(set(output_dir.glob("summary_*.json")) - before)
    if not new:
        raise RuntimeError("evaluate.py did not produce a summary file")
    print(f"<<< batch_size={batch_size} done in {time.time() - t0:.0f}s -> {new[-1].name}", flush=True)
    return new[-1]


def load_run(summary_path: Path) -> dict:
    """Charge un summary et les résultats détaillés associés (même timestamp)."""
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    ts = summary_path.stem.replace("summary_", "")
    results_path = summary_path.with_name(f"results_{ts}.json")
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else []
    bench_meta = next(iter(summary.get("benchmarks", {}).values()), {})
    batch_size = bench_meta.get("batch_size") or (results[0].get("batch_size", 1) if results else 1)
    return {"summary": summary, "results": results, "batch_size": batch_size, "path": summary_path,
            "fingerprint": bench_meta.get("fingerprint")}


def fmt_pct(x):
    return "-" if x is None else f"{x:6.1%}"


def report(runs: list) -> None:
    runs = sorted(runs, key=lambda r: r["batch_size"])
    fingerprints = {r["fingerprint"] for r in runs if r["fingerprint"]}
    if len(fingerprints) > 1:
        print(f"\n!! Les runs n'ont pas tous la même empreinte de benchmark: {fingerprints} - comparaison non valide")

    for model in sorted({m for r in runs for m in r["summary"]["summary_stats"]}):
        print(f"\n=== {model} ===")
        header = f"{'batch':>5} {'n':>4} {'acc':>7} {'exact':>7} {'noresp':>7} {'errors':>6} {'halluc':>7} " \
                 f"{'prompt_tok':>11} {'compl_tok':>10} {'reason_tok':>11} {'cost_usd':>9} {'s/question':>10}"
        print(header)
        for r in runs:
            s = r["summary"]["summary_stats"].get(model)
            if not s:
                continue
            print(f"{r['batch_size']:>5} {s['total_questions']:>4} {fmt_pct(s['accuracy']):>7} {fmt_pct(s['exact_match_rate']):>7} "
                  f"{fmt_pct(s['no_response_rate']):>7} {s['errors']:>6} {fmt_pct(s.get('hallucination_rate')):>7} "
                  f"{s.get('total_prompt_tokens', 0):>11,} {s.get('total_completion_tokens', s.get('total_tokens', 0)):>10,} "
                  f"{s.get('total_reasoning_tokens', 0):>11,} "
                  f"{('%.3f' % s['total_cost_usd']) if s.get('total_cost_usd') is not None else '-':>9} "
                  f"{s['avg_response_time']:>10.1f}")

        # accuracy par tier
        tiers = ["easy", "medium", "hard", "enigma"]
        print(f"\n{'batch':>5} " + " ".join(f"{t:>8}" for t in tiers))
        for r in runs:
            s = r["summary"]["summary_stats"].get(model, {})
            bd = s.get("by_difficulty", {})
            print(f"{r['batch_size']:>5} " + " ".join(fmt_pct(bd[t]["accuracy"]) + f"({bd[t]['total']})" if t in bd else f"{'-':>8}" for t in tiers))

        # accord question par question avec le plus petit batch
        ref = next((r for r in runs if any(x["model_name"] == model for x in r["results"])), None)
        if ref and len(runs) > 1:
            ref_by_q = defaultdict(list)
            for x in ref["results"]:
                if x["model_name"] == model:
                    ref_by_q[(x["benchmark_name"], x["question_id"])].append(x["is_correct"])
            print(f"\nAccord avec batch={ref['batch_size']} (même question, même verdict correct/incorrect) :")
            for r in runs:
                if r is ref:
                    continue
                agree = total = lost = gained = 0
                for x in r["results"]:
                    if x["model_name"] != model:
                        continue
                    key = (x["benchmark_name"], x["question_id"])
                    if key not in ref_by_q:
                        continue
                    ref_ok = sum(ref_by_q[key]) / len(ref_by_q[key]) >= 0.5
                    total += 1
                    agree += (ref_ok == x["is_correct"])
                    lost += (ref_ok and not x["is_correct"])
                    gained += ((not ref_ok) and x["is_correct"])
                if total:
                    print(f"  batch={r['batch_size']:>3}: accord {agree/total:6.1%}  perdues {lost:>3}  gagnées {gained:>3}  (n={total})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="evaluation_config_batch_sweep.yaml")
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 5, 10, 20])
    parser.add_argument("--runs", type=int, default=1, help="runs par taille de batch (moyenne sur plusieurs runs)")
    parser.add_argument("--output-dir", type=Path, default=None, help="défaut: evaluation.output_dir de la config")
    parser.add_argument("--report-only", type=Path, metavar="DIR", help="ne relance rien, agrège les summaries de DIR")
    parser.add_argument("--models", nargs="+", help="transmis à evaluate.py")
    args = parser.parse_args()

    if args.report_only:
        runs = [load_run(p) for p in sorted(args.report_only.glob("summary_*.json"))]
        report(runs)
        return

    import yaml
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    output_dir = args.output_dir or Path(config["evaluation"].get("output_dir", "evaluation_results/batch_sweep"))
    output_dir.mkdir(parents=True, exist_ok=True)
    extra = ["--models", *args.models] if args.models else []

    runs = []
    for bs in args.batch_sizes:
        summary_path = run_one(args.config, bs, args.runs, output_dir, extra)
        runs.append(load_run(summary_path))
    report(runs)


if __name__ == "__main__":
    main()
