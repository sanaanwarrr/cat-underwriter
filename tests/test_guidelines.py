from cat_underwriting.guidelines import GuidelineStore, evaluate_guidelines
from cat_underwriting.extract import rule_based_extract


def test_guideline_flags_for_florida_hurricane():
    text = """
Cedent: Test Mutual
Treaty Type: Property Cat XOL
Limit: $50M
Attachment Point: $25M
Territory: Florida
Covered Perils: Hurricane, Windstorm
Exclusions: Cyber, War, Nuclear
"""
    treaty = rule_based_extract(text)
    store = GuidelineStore("data/guidelines")
    flags = evaluate_guidelines(treaty, store)

    assert any(flag.flag_type == "referral" for flag in flags)
