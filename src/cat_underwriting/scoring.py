from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schemas import GuidelineFlag, RiskAssessment, RiskScoreBreakdown, RiskTier, TreatySlip


WEIGHTS = {
    "geography_hazard_score": 0.30,
    "attachment_limit_severity_score": 0.25,
    "historical_loss_overlap_score": 0.20,
    "exclusion_ambiguity_score": 0.15,
    "document_quality_score": 0.10,
}


def score_treaty(
    treaty: TreatySlip,
    flags: list[GuidelineFlag] | None = None,
    hazard_scores_path: str | Path | None = None,
    historical_losses_path: str | Path | None = None,
) -> RiskAssessment:
    flags = flags or []
    breakdown = RiskScoreBreakdown(
        geography_hazard_score=_geography_score(treaty, hazard_scores_path),
        attachment_limit_severity_score=_attachment_limit_score(treaty),
        historical_loss_overlap_score=_loss_overlap_score(treaty, historical_losses_path),
        exclusion_ambiguity_score=_exclusion_ambiguity_score(treaty, flags),
        document_quality_score=_document_quality_score(treaty),
    )

    risk_score = sum(getattr(breakdown, key) * weight for key, weight in WEIGHTS.items())
    risk_score = round(risk_score, 1)
    tier = _tier(risk_score, flags)
    summary = _summary(treaty, risk_score, tier, flags)

    return RiskAssessment(
        treaty=treaty,
        risk_score=risk_score,
        risk_tier=tier,
        breakdown=breakdown,
        flags=flags,
        underwriter_summary=summary,
    )


def _geography_score(treaty: TreatySlip, hazard_scores_path: str | Path | None) -> float:
    if not hazard_scores_path or not Path(hazard_scores_path).exists():
        joined = " ".join(treaty.territories).lower()
        if "florida" in joined or "gulf" in joined:
            return 85.0
        if "california" in joined:
            return 75.0
        return 45.0 if treaty.territories else 65.0

    df = pd.read_csv(hazard_scores_path)
    if df.empty:
        return 50.0
    territories = [t.lower() for t in treaty.territories]
    mask = pd.Series(False, index=df.index)
    for territory in territories:
        mask |= df["territory"].astype(str).str.lower().str.contains(territory, regex=False)
    matched = df[mask]
    if matched.empty:
        return 55.0
    return float(round(matched["hazard_score"].mean(), 1))


def _attachment_limit_score(treaty: TreatySlip) -> float:
    if treaty.limit_amount_usd <= 0:
        return 80.0
    severity = 0.0
    if treaty.limit_amount_usd >= 100_000_000:
        severity += 35
    elif treaty.limit_amount_usd >= 50_000_000:
        severity += 25
    else:
        severity += 15

    if treaty.attachment_point_usd < 10_000_000:
        severity += 45
    elif treaty.attachment_point_usd < 25_000_000:
        severity += 30
    else:
        severity += 15

    ratio = treaty.limit_amount_usd / max(treaty.attachment_point_usd, 1)
    if ratio > 2:
        severity += 15
    elif ratio > 1:
        severity += 10

    return float(min(100, severity))


def _loss_overlap_score(treaty: TreatySlip, historical_losses_path: str | Path | None) -> float:
    if not historical_losses_path or not Path(historical_losses_path).exists():
        return 50.0
    losses = pd.read_csv(historical_losses_path)
    if losses.empty:
        return 50.0

    territories = " ".join(treaty.territories).lower()
    perils = " ".join(treaty.covered_perils).lower()
    mask = pd.Series(False, index=losses.index)
    for _, row in losses.iterrows():
        territory_match = str(row.get("territory", "")).lower() in territories or any(
            t.lower() in str(row.get("territory", "")).lower() for t in treaty.territories
        )
        peril_match = str(row.get("peril", "")).lower() in perils
        if territory_match and peril_match:
            mask.loc[row.name] = True
    matched = losses[mask]
    if matched.empty:
        return 30.0
    total_loss = matched["gross_loss_usd"].sum()
    if total_loss >= 500_000_000:
        return 95.0
    if total_loss >= 250_000_000:
        return 80.0
    if total_loss >= 100_000_000:
        return 65.0
    return 45.0


def _exclusion_ambiguity_score(treaty: TreatySlip, flags: list[GuidelineFlag]) -> float:
    critical_wording = any(f.flag_type == "wording" and f.severity == "critical" for f in flags)
    if critical_wording:
        return 95.0
    if not treaty.excluded_perils:
        return 70.0
    excluded = " ".join(treaty.excluded_perils).lower()
    if any(term in excluded for term in ["as per expiring", "tbd", "standard exclusions", "to be agreed"]):
        return 75.0
    return 30.0


def _document_quality_score(treaty: TreatySlip) -> float:
    return round((1 - treaty.confidence_score) * 100, 1)


def _tier(score: float, flags: list[GuidelineFlag]) -> RiskTier:
    if any(f.severity == "critical" for f in flags):
        return RiskTier.high
    if score >= 70:
        return RiskTier.high
    if score >= 45:
        return RiskTier.medium
    return RiskTier.low


def _summary(treaty: TreatySlip, risk_score: float, tier: RiskTier, flags: list[GuidelineFlag]) -> str:
    flag_text = "; ".join(f.message for f in flags) if flags else "No guideline exceptions detected."
    territories = ", ".join(treaty.territories) or "unspecified territories"
    perils = ", ".join(treaty.covered_perils) or "unspecified perils"
    return (
        f"{treaty.cedent_name} submission scored {risk_score}/100 ({tier.value}). "
        f"The slip covers {perils} in {territories} with a limit of "
        f"${treaty.limit_amount_usd:,.0f} attaching at ${treaty.attachment_point_usd:,.0f}. "
        f"Key triage notes: {flag_text}"
    )
