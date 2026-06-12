from cat_underwriting.extract import rule_based_extract
from cat_underwriting.guidelines import evaluate_guidelines
from cat_underwriting.scoring import score_treaty


def test_scoring_returns_valid_assessment():
    text = """
Cedent: Coastal Shield P&C
Treaty Type: Property Cat XOL
Limit: $120M
Attachment Point: $8M
Territory: Florida
Covered Perils: Hurricane, Windstorm, Flood
Exclusions: Flood, Cyber, War
"""
    treaty = rule_based_extract(text)
    flags = evaluate_guidelines(treaty)
    assessment = score_treaty(
        treaty,
        flags=flags,
        hazard_scores_path="data/hazard_data/county_hazard_scores.csv",
        historical_losses_path="data/synthetic_losses/historical_losses.csv",
    )

    assert 0 <= assessment.risk_score <= 100
    assert assessment.risk_tier.value == "High"
    assert any(flag.flag_type == "wording" for flag in assessment.flags)
