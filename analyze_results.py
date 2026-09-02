#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CLI script to analyze evaluation results from CSV/JSON files."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False


def _is_failed_run(df: pd.DataFrame) -> bool:
    """True si toutes les lignes du fichier sont en erreur (ex: serveur local éteint)."""
    if "error" not in df.columns or df.empty:
        return False
    return bool(df["error"].notna().all() & (df["error"].astype(str).str.len() > 0).all())


def load_results(file_paths: List[Path], exclude_failed_runs: bool = False) -> pd.DataFrame:
    """Load results from CSV or JSON files into a DataFrame.

    Args:
        exclude_failed_runs: ignore les fichiers dont 100 % des lignes sont en
            erreur, pour ne pas polluer les agrégats avec des runs ratés.
    """
    frames = []
    for fp in file_paths:
        if fp.suffix.lower() == ".csv":
            frame = pd.read_csv(fp)
        elif fp.suffix.lower() == ".json":
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                frame = pd.DataFrame(data)
            elif isinstance(data, dict) and "questions_answers" in data:
                frame = pd.DataFrame(data["questions_answers"])
            else:
                raise ValueError(f"Unsupported JSON structure in {fp}")
        else:
            raise ValueError(f"Unsupported file format: {fp.suffix}")
        if exclude_failed_runs and _is_failed_run(frame):
            print(f"Skipping {fp}: every row is an error")
            continue
        frame["source_file"] = fp.name
        frames.append(frame)
    if not frames:
        raise ValueError("No usable result files")
    return pd.concat(frames, ignore_index=True)


def compute_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute summary statistics per model."""
    stats = {}
    if "batch_size" in df.columns and df["batch_size"].nunique() > 1:
        df = df.assign(model_name=df["model_name"] + " [batch=" + df["batch_size"].astype(int).astype(str) + "]")
    for model, group in df.groupby("model_name"):
        total = len(group)
        correct = group["is_correct"].sum()
        exact = group["is_exact_match"].sum()
        no_resp = group["no_response"].sum()
        avg_time = group["response_time"].mean()
        avg_partial = group["partial_match_score"].mean()
        tokens = group["tokens_used"].sum()
        reasoning = group["reasoning_tokens"].sum()

        # Per question type
        by_type = {}
        for qtype, sub in group.groupby("question_type"):
            by_type[qtype] = {
                "total": len(sub),
                "correct": int(sub["is_correct"].sum()),
                "accuracy": float(sub["is_correct"].mean()),
            }

        # Per difficulty tier (files produced before the field existed have no column)
        by_difficulty = {}
        if "difficulty" in group.columns:
            for tier, sub in group.dropna(subset=["difficulty"]).groupby("difficulty"):
                by_difficulty[tier] = {
                    "total": len(sub),
                    "correct": int(sub["is_correct"].sum()),
                    "accuracy": float(sub["is_correct"].mean()),
                }
        # Hallucinations: answered questions containing at least one unknown name
        hallucination_rate = None
        if "hallucinated_names" in group.columns:
            answered = group[(group["error"].isna()) & (group["no_response"] == False)]
            if len(answered):
                hallucination_rate = float((answered["hallucinated_names"].fillna(0) > 0).mean())
        # Enigma vs normal
        enigma = group[group["is_enigma"] == True]
        normal = group[group["is_enigma"] == False]

        stats[model] = {
            "total_questions": total,
            "accuracy": float(correct / total),
            "exact_match_rate": float(exact / total),
            "no_response_rate": float(no_resp / total),
            "avg_response_time": float(avg_time),
            "avg_partial_score": float(avg_partial),
            "total_tokens": int(tokens),
            "total_reasoning_tokens": int(reasoning),
            "by_question_type": by_type,
            "by_difficulty": by_difficulty,
            "hallucination_rate": hallucination_rate,
            "enigma": {
                "total": len(enigma),
                "correct": int(enigma["is_correct"].sum()),
                "accuracy": float(enigma["is_correct"].mean()) if len(enigma) else 0.0,
            },
            "normal": {
                "total": len(normal),
                "correct": int(normal["is_correct"].sum()),
                "accuracy": float(normal["is_correct"].mean()) if len(normal) else 0.0,
            },
        }
    return stats


def print_stats(stats: Dict[str, Any]):
    """Print formatted statistics to stdout."""
    print("=" * 60)
    print("FAMILYBENCH RESULTS ANALYSIS")
    print("=" * 60)
    for model, s in stats.items():
        print(f"\n📊 {model}")
        print("-" * 40)
        print(f"  Total questions : {s['total_questions']}")
        print(f"  Accuracy        : {s['accuracy']:.1%}")
        print(f"  Exact match     : {s['exact_match_rate']:.1%}")
        print(f"  No response     : {s['no_response_rate']:.1%}")
        print(f"  Avg response    : {s['avg_response_time']:.2f}s")
        print(f"  Avg partial     : {s['avg_partial_score']:.2f}")
        print(f"  Total tokens    : {s['total_tokens']:,}")
        if s["total_reasoning_tokens"]:
            print(f"  Reasoning tok   : {s['total_reasoning_tokens']:,}")
        if s["enigma"]["total"]:
            print(f"  Enigmas         : {s['enigma']['accuracy']:.1%} ({s['enigma']['correct']}/{s['enigma']['total']})")
        if s["normal"]["total"]:
            print(f"  Normal Qs       : {s['normal']['accuracy']:.1%} ({s['normal']['correct']}/{s['normal']['total']})")
        if s.get("hallucination_rate") is not None:
            print(f"  Hallucinations  : {s['hallucination_rate']:.1%} of answers contain an unknown name")
        if s.get("by_difficulty"):
            print(f"  By difficulty:")
            for tier in ("easy", "medium", "hard", "enigma"):
                if tier in s["by_difficulty"]:
                    d = s["by_difficulty"][tier]
                    print(f"    {tier:25s} {d['accuracy']:.1%} ({d['correct']}/{d['total']})")
        if s["by_question_type"]:
            print(f"  By type:")
            for qtype, qs in sorted(s["by_question_type"].items(), key=lambda x: -x[1]["accuracy"]):
                print(f"    {qtype:25s} {qs['accuracy']:.1%} ({qs['correct']}/{qs['total']})")
    print("\n" + "=" * 60)


def generate_plots(df: pd.DataFrame, output_dir: Path):
    """Generate comparative plots."""
    if not HAS_PLOTTING:
        print("Plotting libraries not installed. Install pandas, matplotlib, seaborn.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    # Accuracy by model
    fig, ax = plt.subplots(figsize=(10, 6))
    model_stats = df.groupby("model_name")["is_correct"].mean().sort_values(ascending=True)
    colors = ["#2ecc71" if v >= 0.7 else "#f1c40f" if v >= 0.5 else "#e74c3c" for v in model_stats.values]
    model_stats.plot(kind="barh", color=colors, ax=ax)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Accuracy")
    ax.set_title("Model Accuracy Comparison")
    ax.axvline(x=0.5, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(x=0.7, color="gray", linestyle="--", alpha=0.5)
    plt.tight_layout()
    fig.savefig(output_dir / "accuracy_comparison.png", dpi=150)
    plt.close(fig)

    # Response time by model
    fig, ax = plt.subplots(figsize=(10, 6))
    df.boxplot(column="response_time", by="model_name", ax=ax, grid=False)
    ax.set_xlabel("Model")
    ax.set_ylabel("Response Time (s)")
    ax.set_title("Response Time Distribution")
    plt.suptitle("")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(output_dir / "response_time_distribution.png", dpi=150)
    plt.close(fig)

    # Accuracy by question type
    if "question_type" in df.columns and df["question_type"].notna().any():
        fig, ax = plt.subplots(figsize=(12, 6))
        type_stats = df.groupby("question_type")["is_correct"].mean().sort_values(ascending=False)
        type_stats.plot(kind="bar", ax=ax, color="steelblue")
        ax.set_ylim(0, 1)
        ax.set_ylabel("Accuracy")
        ax.set_title("Accuracy by Question Type")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        fig.savefig(output_dir / "accuracy_by_question_type.png", dpi=150)
        plt.close(fig)

    # Enigma complexity
    enigma_df = df[df["is_enigma"] == True]
    if not enigma_df.empty and "enigma_complexity" in enigma_df.columns:
        fig, ax = plt.subplots(figsize=(8, 5))
        complexity_stats = enigma_df.groupby("enigma_complexity")["is_correct"].mean()
        complexity_stats.plot(kind="bar", ax=ax, color="coral")
        ax.set_ylim(0, 1)
        ax.set_ylabel("Accuracy")
        ax.set_xlabel("Enigma Complexity")
        ax.set_title("Enigma Accuracy by Complexity")
        plt.tight_layout()
        fig.savefig(output_dir / "enigma_by_complexity.png", dpi=150)
        plt.close(fig)

    print(f"Plots saved to {output_dir}/")


def generate_html_report(stats: Dict[str, Any], output_path: Path):
    """Generate an HTML report."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        "<title>FamilyBench Results Report</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#333}",
        "h1{color:#2c3e50}h2{color:#34495e;border-bottom:2px solid #ecf0f1;padding-bottom:.3rem}",
        "table{border-collapse:collapse;width:100%;margin:1rem 0}",
        "th,td{border:1px solid #ddd;padding:8px;text-align:left}",
        "th{background:#f8f9fa}tr:nth-child(even){background:#f8f9fa}",
        ".metric{font-size:1.2rem;font-weight:bold;color:#27ae60}",
        ".bad{color:#e74c3c}.warn{color:#f39c12}",
        "</style></head><body>",
        "<h1>FamilyBench Results Report</h1>",
    ]

    for model, s in stats.items():
        acc_class = "metric" if s["accuracy"] >= 0.7 else "warn" if s["accuracy"] >= 0.5 else "bad"
        html_parts.append(f"<h2>{model}</h2>")
        html_parts.append("<table>")
        html_parts.append(f"<tr><th>Metric</th><th>Value</th></tr>")
        html_parts.append(f"<tr><td>Total Questions</td><td>{s['total_questions']}</td></tr>")
        html_parts.append(f"<tr><td>Accuracy</td><td class='{acc_class}'>{s['accuracy']:.1%}</td></tr>")
        html_parts.append(f"<tr><td>Exact Match</td><td>{s['exact_match_rate']:.1%}</td></tr>")
        html_parts.append(f"<tr><td>No Response Rate</td><td>{s['no_response_rate']:.1%}</td></tr>")
        html_parts.append(f"<tr><td>Avg Response Time</td><td>{s['avg_response_time']:.2f}s</td></tr>")
        html_parts.append(f"<tr><td>Total Tokens</td><td>{s['total_tokens']:,}</td></tr>")
        if s["enigma"]["total"]:
            html_parts.append(f"<tr><td>Enigma Accuracy</td><td>{s['enigma']['accuracy']:.1%}</td></tr>")
        if s["normal"]["total"]:
            html_parts.append(f"<tr><td>Normal Q Accuracy</td><td>{s['normal']['accuracy']:.1%}</td></tr>")
        html_parts.append("</table>")

        if s["by_question_type"]:
            html_parts.append("<h3>By Question Type</h3><table>")
            html_parts.append("<tr><th>Type</th><th>Total</th><th>Correct</th><th>Accuracy</th></tr>")
            for qtype, qs in sorted(s["by_question_type"].items(), key=lambda x: -x[1]["accuracy"]):
                html_parts.append(f"<tr><td>{qtype}</td><td>{qs['total']}</td><td>{qs['correct']}</td><td>{qs['accuracy']:.1%}</td></tr>")
            html_parts.append("</table>")

    html_parts.append("</body></html>")
    output_path.write_text("\n".join(html_parts), encoding="utf-8")
    print(f"HTML report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze FamilyBench evaluation results.")
    parser.add_argument("files", nargs="+", type=Path, help="Result files (CSV or JSON)")
    parser.add_argument("--plots", action="store_true", help="Generate comparative plots")
    parser.add_argument("--report", type=Path, help="Generate HTML report to given path")
    parser.add_argument("--output-dir", type=Path, default=Path("analysis_output"), help="Directory for plots")
    parser.add_argument("--exclude-failed-runs", action="store_true",
                        help="Skip files where every row is an error (e.g. API server down)")
    args = parser.parse_args()

    try:
        df = load_results(args.files, exclude_failed_runs=args.exclude_failed_runs)
    except Exception as e:
        print(f"Error loading results: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df)} results from {len(args.files)} file(s)")

    stats = compute_stats(df)
    print_stats(stats)

    if args.plots:
        if HAS_PLOTTING:
            generate_plots(df, args.output_dir)
        else:
            print("Warning: plotting libraries not available. Install pandas, matplotlib, seaborn.")

    if args.report:
        generate_html_report(stats, args.report)


if __name__ == "__main__":
    main()
