from __future__ import annotations

from pathlib import Path

from .extract import extract_treaty_terms
from .guidelines import GuidelineStore, evaluate_guidelines
from .ingest import read_document
from .report import write_markdown_report
from .schemas import RiskAssessment
from .scoring import score_treaty
from .storage import save_assessment_sqlite


def run_pipeline(
    submission_path: str | Path,
    guideline_dir: str | Path = "data/guidelines",
    hazard_scores_path: str | Path | None = "data/hazard_data/county_hazard_scores.csv",
    historical_losses_path: str | Path | None = "data/synthetic_losses/historical_losses.csv",
    output_dir: str | Path = "outputs",
    use_llm: bool = False,
    save_sqlite: bool = True,
) -> RiskAssessment:
    submission_path = Path(submission_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    document_text = read_document(submission_path)
    treaty = extract_treaty_terms(document_text, source_file=str(submission_path), use_llm=use_llm)

    store = GuidelineStore(guideline_dir)
    flags = evaluate_guidelines(treaty, store)
    assessment = score_treaty(
        treaty,
        flags=flags,
        hazard_scores_path=hazard_scores_path,
        historical_losses_path=historical_losses_path,
    )

    safe_name = submission_path.stem.replace(" ", "_")
    write_markdown_report(assessment, output_dir / f"{safe_name}_triage_report.md")
    (output_dir / f"{safe_name}_assessment.json").write_text(
        assessment.model_dump_json(indent=2), encoding="utf-8"
    )

    if save_sqlite:
        save_assessment_sqlite(assessment, output_dir / "cat_triage.sqlite")

    return assessment
