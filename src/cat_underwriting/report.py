from __future__ import annotations

from pathlib import Path

from .schemas import RiskAssessment


def write_markdown_report(assessment: RiskAssessment, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    treaty = assessment.treaty
    lines = [
        "# Cat Treaty Underwriting Triage Report",
        "",
        "## Executive Summary",
        assessment.underwriter_summary,
        "",
        "## Extracted Treaty Terms",
        "",
        f"- **Cedent:** {treaty.cedent_name}",
        f"- **Broker:** {treaty.broker_name or 'Not found'}",
        f"- **Treaty type:** {treaty.treaty_type}",
        f"- **Effective date:** {treaty.effective_date or 'Not found'}",
        f"- **Expiration date:** {treaty.expiration_date or 'Not found'}",
        f"- **Limit:** ${treaty.limit_amount_usd:,.0f}",
        f"- **Attachment point:** ${treaty.attachment_point_usd:,.0f}",
        f"- **Covered perils:** {', '.join(treaty.covered_perils) or 'Not found'}",
        f"- **Excluded perils:** {', '.join(treaty.excluded_perils) or 'Not found'}",
        f"- **Territories:** {', '.join(treaty.territories) or 'Not found'}",
        f"- **Reinstatements:** {treaty.reinstatements if treaty.reinstatements is not None else 'Not found'}",
        f"- **Extraction confidence:** {treaty.confidence_score:.0%}",
        "",
        "## Risk Score",
        "",
        f"- **Overall risk score:** {assessment.risk_score}/100",
        f"- **Risk tier:** {assessment.risk_tier.value}",
        "",
        "| Component | Score |",
        "|---|---:|",
        f"| Geography hazard | {assessment.breakdown.geography_hazard_score:.1f} |",
        f"| Attachment/limit severity | {assessment.breakdown.attachment_limit_severity_score:.1f} |",
        f"| Historical loss overlap | {assessment.breakdown.historical_loss_overlap_score:.1f} |",
        f"| Exclusion ambiguity | {assessment.breakdown.exclusion_ambiguity_score:.1f} |",
        f"| Document quality risk | {assessment.breakdown.document_quality_score:.1f} |",
        "",
        "## Guideline and Referral Flags",
        "",
    ]
    if assessment.flags:
        for flag in assessment.flags:
            lines.append(f"- **{flag.severity.upper()} / {flag.flag_type}:** {flag.message}")
            if flag.evidence:
                lines.append(f"  - Evidence: {flag.evidence}")
    else:
        lines.append("- No guideline flags detected.")

    lines.extend(
        [
            "",
            "## Underwriter Next Steps",
            "",
            "- Confirm extracted financial terms against the original slip.",
            "- Review wording conflicts and missing exclusions.",
            "- Compare territory/peril exposure against current portfolio accumulations.",
            "- Request cleaner exposure data if extraction confidence is low.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
