from pathlib import Path

from cat_underwriting.pipeline import run_pipeline


def test_pipeline_writes_outputs(tmp_path):
    assessment = run_pipeline(
        "data/sample_slips/treaty_slip_hurricane_florida.md",
        guideline_dir="data/guidelines",
        hazard_scores_path="data/hazard_data/county_hazard_scores.csv",
        historical_losses_path="data/synthetic_losses/historical_losses.csv",
        output_dir=tmp_path,
        use_llm=False,
    )

    assert assessment.treaty.cedent_name == "Gulf Mutual Insurance Company"
    assert (tmp_path / "treaty_slip_hurricane_florida_assessment.json").exists()
    assert (tmp_path / "treaty_slip_hurricane_florida_triage_report.md").exists()
    assert (tmp_path / "cat_triage.sqlite").exists()
