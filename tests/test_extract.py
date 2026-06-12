from pathlib import Path

from cat_underwriting.extract import rule_based_extract


def test_rule_based_extract_sample_slip():
    text = Path("data/sample_slips/treaty_slip_hurricane_florida.md").read_text()
    treaty = rule_based_extract(text, source_file="sample")

    assert treaty.cedent_name == "Gulf Mutual Insurance Company"
    assert treaty.limit_amount_usd == 50_000_000
    assert treaty.attachment_point_usd == 25_000_000
    assert "Hurricane" in treaty.covered_perils
    assert "Florida" in treaty.territories
    assert treaty.confidence_score >= 0.8
