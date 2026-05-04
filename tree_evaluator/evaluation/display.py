"""Affichage rich pour le suivi de l'évaluation."""

import time
from typing import Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns

from .result import EvaluationResult

console = Console()


class EvalProgress:
    """Gestionnaire d'affichage rich pour l'évaluation."""

    def __init__(self, models: List[str], benchmarks: List[str], runs_per_benchmark: int = 1):
        self.models = models
        self.benchmarks = benchmarks
        self.runs_per_benchmark = runs_per_benchmark
        self.total_steps = len(models) * len(benchmarks) * runs_per_benchmark

        # State
        self.current_model: str = ""
        self.current_benchmark: str = ""
        self.current_run: int = 0
        self.questions_total: int = 0
        self.questions_done: int = 0
        self.correct: int = 0
        self.errors: int = 0
        self.no_responses: int = 0
        self.step_start_time: float = 0.0
        self.eval_start_time: float = time.time()
        self.steps_completed: int = 0
        self.model_results: Dict[str, List[Dict]] = {}  # model -> list of run summaries
        self.last_result: Optional[EvaluationResult] = None

        # Rich components
        self.progress = Progress(
            SpinnerColumn("dots"),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40, complete_style="green", finished_style="bright_green"),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
            expand=True,
        )
        self.overall_task = self.progress.add_task(
            "Évaluation globale", total=self.total_steps
        )
        self.question_task = self.progress.add_task(
            "Questions", total=0, visible=False
        )
        self.live: Optional[Live] = None

    def start(self):
        """Démarre l'affichage live."""
        self.eval_start_time = time.time()
        self.live = Live(self._build_display(), console=console, refresh_per_second=4)
        self.live.start()

    def stop(self):
        """Arrête l'affichage live."""
        if self.live:
            self.live.stop()

    def begin_model(self, model_name: str):
        """Signal le début de l'évaluation d'un modèle."""
        self.current_model = model_name
        if model_name not in self.model_results:
            self.model_results[model_name] = []

    def begin_run(self, benchmark_name: str, run: int, total_questions: int):
        """Signal le début d'un run."""
        self.current_benchmark = benchmark_name
        self.current_run = run
        self.questions_total = total_questions
        self.questions_done = 0
        self.correct = 0
        self.errors = 0
        self.no_responses = 0
        self.step_start_time = time.time()

        self.progress.update(
            self.question_task,
            description=f"  {benchmark_name} (run {run})",
            completed=0,
            total=total_questions,
            visible=True,
        )
        self._refresh()

    def update_question(self, result: EvaluationResult):
        """Met à jour après une question évaluée."""
        self.questions_done += 1
        if result.is_correct:
            self.correct += 1
        if result.error:
            self.errors += 1
        if result.no_response:
            self.no_responses += 1
        self.last_result = result

        self.progress.update(self.question_task, completed=self.questions_done)
        self._refresh()

    def update_questions_batch(self, results: List[EvaluationResult]):
        """Met à jour après un batch de questions."""
        for r in results:
            self.questions_done += 1
            if r.is_correct:
                self.correct += 1
            if r.error:
                self.errors += 1
            if r.no_response:
                self.no_responses += 1
        if results:
            self.last_result = results[-1]

        self.progress.update(self.question_task, completed=self.questions_done)
        self._refresh()

    def end_run(self, accuracy: float, avg_time: float):
        """Signal la fin d'un run."""
        self.steps_completed += 1
        self.progress.update(self.overall_task, completed=self.steps_completed)

        self.model_results.setdefault(self.current_model, []).append({
            "benchmark": self.current_benchmark,
            "run": self.current_run,
            "accuracy": accuracy,
            "avg_time": avg_time,
            "questions": self.questions_total,
            "correct": self.correct,
            "errors": self.errors,
            "no_responses": self.no_responses,
        })
        self._refresh()

    def _refresh(self):
        """Rafraîchit l'affichage."""
        if self.live:
            self.live.update(self._build_display())

    def _build_display(self) -> Table:
        """Construit le layout complet."""
        grid = Table.grid(expand=True)
        grid.add_row(self._build_header())
        grid.add_row(self._build_progress_panel())
        if self.last_result:
            grid.add_row(self._build_last_answer())
        if self.model_results:
            grid.add_row(self._build_results_table())
        return grid

    def _build_header(self) -> Panel:
        """Construit le header."""
        elapsed = time.time() - self.eval_start_time
        elapsed_str = _format_duration(elapsed)

        # ETA globale
        if self.steps_completed > 0:
            avg_step = elapsed / self.steps_completed
            remaining = avg_step * (self.total_steps - self.steps_completed)
            eta_str = _format_duration(remaining)
        else:
            eta_str = "—"

        header = Table.grid(expand=True)
        header.add_column(ratio=1)
        header.add_column(ratio=1, justify="right")
        header.add_row(
            Text("🌳 TreeEval", style="bold bright_green"),
            Text(f"⏱ {elapsed_str}  ⏳ ETA {eta_str}", style="dim"),
        )
        header.add_row(
            Text(f"{len(self.models)} modèle(s) • {len(self.benchmarks)} benchmark(s) • {self.runs_per_benchmark} run(s)", style="dim"),
            Text(f"Étape {self.steps_completed}/{self.total_steps}", style="bold"),
        )
        return Panel(header, border_style="bright_green", padding=(0, 1))

    def _build_progress_panel(self) -> Panel:
        """Construit le panneau de progression actuel."""
        grid = Table.grid(expand=True)

        # Progress bars
        grid.add_row(self.progress)

        # Live stats pour le run en cours
        if self.questions_total > 0:
            stats = Table.grid(expand=True, padding=(0, 2))
            stats.add_column(ratio=1)
            stats.add_column(ratio=1)
            stats.add_column(ratio=1)
            stats.add_column(ratio=1)

            acc = (self.correct / self.questions_done * 100) if self.questions_done > 0 else 0
            acc_style = "green" if acc >= 70 else ("yellow" if acc >= 50 else "red")

            elapsed = time.time() - self.step_start_time
            if self.questions_done > 0:
                avg_q = elapsed / self.questions_done
                eta_q = avg_q * (self.questions_total - self.questions_done)
                speed = f"{avg_q:.1f}s/q"
                eta_q_str = _format_duration(eta_q)
            else:
                speed = "—"
                eta_q_str = "—"

            stats.add_row(
                Text(f"🎯 Accuracy: {acc:.1f}%", style=acc_style),
                Text(f"⚡ {speed}", style="cyan"),
                Text(f"❌ Err: {self.errors}  🔇 NR: {self.no_responses}", style="dim red" if self.errors > 0 else "dim"),
                Text(f"⏳ {eta_q_str}", style="dim"),
            )
            grid.add_row(stats)

        title = f"[bold]{self.current_model}[/] → [cyan]{self.current_benchmark}[/]" if self.current_model else "En attente..."
        return Panel(grid, title=title, border_style="blue", padding=(0, 1))

    def _build_last_answer(self) -> Panel:
        """Construit le panneau de la dernière réponse du modèle."""
        r = self.last_result
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(style="bold", width=12)
        grid.add_column(ratio=1)

        # Question (tronquée si trop longue)
        q_text = r.question if len(r.question) <= 120 else r.question[:117] + "..."
        grid.add_row("Question", Text(q_text, style="white"))

        # Réponse attendue vs réponse du modèle
        grid.add_row("Attendu", Text(r.expected_answer, style="cyan"))

        if r.is_correct:
            answer_style = "bold green"
            icon = "✓"
        elif r.no_response:
            answer_style = "dim"
            icon = "∅"
        elif r.error:
            answer_style = "bold red"
            icon = "✗"
        else:
            answer_style = "bold red"
            icon = "✗"

        model_answer = r.model_answer if r.model_answer else "(vide)"
        grid.add_row("Modèle", Text(f"{icon} {model_answer}", style=answer_style))

        # Métadonnées
        meta_parts = [f"{r.response_time:.1f}s"]
        if r.tokens_used:
            meta_parts.append(f"{r.tokens_used} out tok")
        if r.cost_usd is not None:
            meta_parts.append(f"${r.cost_usd:.5f}")
        if r.partial_match_score > 0 and not r.is_exact_match:
            meta_parts.append(f"partial: {r.partial_match_score:.0%}")
        grid.add_row("", Text(" • ".join(meta_parts), style="dim"))

        return Panel(grid, title="Dernière réponse", border_style="dim")

    def _build_results_table(self) -> Panel:
        """Construit le tableau récapitulatif des runs terminés."""
        table = Table(expand=True, show_lines=False, padding=(0, 1))
        table.add_column("Modèle", style="bold")
        table.add_column("Benchmark", style="cyan")
        table.add_column("Run", justify="center")
        table.add_column("Accuracy", justify="center")
        table.add_column("Temps moy.", justify="center")
        table.add_column("Q", justify="center", style="dim")
        table.add_column("Err", justify="center")
        table.add_column("NR", justify="center")

        for model_name, runs in self.model_results.items():
            for run_info in runs:
                acc = run_info["accuracy"]
                acc_style = "green" if acc >= 0.7 else ("yellow" if acc >= 0.5 else "red")
                err_style = "red" if run_info["errors"] > 0 else "dim"
                nr_style = "yellow" if run_info["no_responses"] > 0 else "dim"

                table.add_row(
                    model_name,
                    run_info["benchmark"],
                    str(run_info["run"]),
                    Text(f"{acc:.1%}", style=acc_style),
                    f"{run_info['avg_time']:.2f}s",
                    str(run_info["questions"]),
                    Text(str(run_info["errors"]), style=err_style),
                    Text(str(run_info["no_responses"]), style=nr_style),
                )

        return Panel(table, title="Résultats", border_style="bright_yellow", padding=(0, 1))


def print_final_summary(summary_stats: Dict, output_paths: Dict[str, str]):
    """Affiche le résumé final après toute l'évaluation."""
    console.print()

    for model_name, stats in summary_stats.items():
        acc = stats["accuracy"]
        acc_style = "green" if acc >= 0.7 else ("yellow" if acc >= 0.5 else "red")

        table = Table(title=f"[bold]{model_name}[/]", expand=True, show_lines=True)
        table.add_column("Métrique", style="bold")
        table.add_column("Valeur", justify="right")

        table.add_row("Questions", str(stats["total_questions"]))
        table.add_row("Accuracy", Text(f"{acc:.1%}", style=acc_style))
        table.add_row("Exact match", f"{stats['exact_match_rate']:.1%}")
        table.add_row("Non-réponses", f"{stats['no_responses']} ({stats['no_response_rate']:.1%})")
        table.add_row("Temps moyen", f"{stats['avg_response_time']:.2f}s")
        completion = stats.get("total_completion_tokens", stats.get("total_tokens", 0))
        avg_completion = stats.get("avg_completion_tokens", 0)
        table.add_row(
            "Output tokens",
            f"{completion:,} (avg: {avg_completion:.0f}/q)",
        )
        prompt_total = stats.get("total_prompt_tokens", 0)
        if prompt_total:
            table.add_row("Prompt tokens", f"{prompt_total:,}")
        cached_total = stats.get("total_cached_tokens", 0)
        if cached_total:
            table.add_row("Cached input tokens", f"{cached_total:,}")
        total_cost = stats.get("total_cost_usd")
        avg_cost = stats.get("avg_cost_usd")
        if total_cost is not None:
            table.add_row(
                "Coût",
                f"${total_cost:.4f} (avg: ${avg_cost:.5f}/q)",
            )

        if stats["total_reasoning_tokens"] > 0:
            table.add_row("Reasoning tokens", f"{stats['total_reasoning_tokens']:,} (avg: {stats['avg_reasoning_tokens']:.0f})")

        # Enigmas
        if stats.get("enigma_stats"):
            es = stats["enigma_stats"]
            table.add_row("─ Énigmes", f"{es['accuracy']:.1%} ({es['correct']}/{es['total']})")
            for complexity, cs in (es.get("by_complexity") or {}).items():
                table.add_row(f"  Complexité {complexity}", f"{cs['accuracy']:.1%} ({cs['correct']}/{cs['total']})")

        if stats.get("normal_stats"):
            ns = stats["normal_stats"]
            table.add_row("─ Questions normales", f"{ns['accuracy']:.1%} ({ns['correct']}/{ns['total']})")

        console.print(Panel(table, border_style="bright_green"))

    # Output files
    if output_paths:
        file_table = Table.grid(padding=(0, 2))
        file_table.add_column(style="bold cyan")
        file_table.add_column()
        for label, path in output_paths.items():
            file_table.add_row(f"📄 {label}", str(path))
        console.print(Panel(file_table, title="Fichiers générés", border_style="blue"))

    console.print("[bold bright_green]✓ Évaluation terminée ![/]")


def _format_duration(seconds: float) -> str:
    """Formate une durée en h:mm:ss ou m:ss."""
    if seconds < 0:
        return "—"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    elif m > 0:
        return f"{m}m{s:02d}s"
    else:
        return f"{s}s"
