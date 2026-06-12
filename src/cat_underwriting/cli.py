from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .pipeline import run_pipeline

app = typer.Typer(help="Catastrophe treaty underwriting triage assistant")
console = Console()


@app.callback()
def main():
    """Catastrophe treaty underwriting triage assistant."""
    pass


@app.command()
def triage(
    submission: Path = typer.Argument(..., help="Path to treaty slip PDF/Markdown/Excel/CSV."),
    use_llm: bool = typer.Option(False, help="Use GitHub Models if GITHUB_TOKEN is configured."),
    output_dir: Path = typer.Option(Path("outputs"), help="Where reports and JSON output are written."),
    guideline_dir: Path = typer.Option(Path("data/guidelines"), help="Guideline document directory."),
    hazard_scores: Path = typer.Option(Path("data/hazard_data/county_hazard_scores.csv")),
    historical_losses: Path = typer.Option(Path("data/synthetic_losses/historical_losses.csv")),
):
    assessment = run_pipeline(
        submission_path=submission,
        guideline_dir=guideline_dir,
        hazard_scores_path=hazard_scores,
        historical_losses_path=historical_losses,
        output_dir=output_dir,
        use_llm=use_llm,
    )

    table = Table(title="Cat Treaty Triage Result")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Cedent", assessment.treaty.cedent_name)
    table.add_row("Treaty type", assessment.treaty.treaty_type)
    table.add_row("Risk score", str(assessment.risk_score))
    table.add_row("Risk tier", assessment.risk_tier.value)
    table.add_row("Flags", str(len(assessment.flags)))
    console.print(table)
    console.print("\n[bold]Summary:[/bold] " + assessment.underwriter_summary)
    console.print(f"\nReports written to: [green]{output_dir.resolve()}[/green]")


if __name__ == "__main__":
    app()
