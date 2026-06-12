from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class RiskTier(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class TreatySlip(BaseModel):
    """Validated structured output extracted from a broker treaty slip."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    cedent_name: str = Field(..., min_length=2)
    broker_name: str | None = None
    treaty_type: str = Field(..., min_length=2)
    effective_date: date | None = None
    expiration_date: date | None = None
    limit_amount_usd: float = Field(..., ge=0)
    attachment_point_usd: float = Field(..., ge=0)
    covered_perils: list[str] = Field(default_factory=list)
    excluded_perils: list[str] = Field(default_factory=list)
    territories: list[str] = Field(default_factory=list)
    reinstatements: int | None = Field(default=None, ge=0)
    confidence_score: float = Field(default=0.50, ge=0, le=1)
    source_file: str | None = None
    raw_extraction_notes: str | None = None

    @field_validator("covered_perils", "excluded_perils", "territories", mode="before")
    @classmethod
    def normalize_string_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [x.strip() for x in value.split(",") if x.strip()]
        return [str(x).strip() for x in value if str(x).strip()]

    @model_validator(mode="after")
    def check_dates(self):
        if self.effective_date and self.expiration_date:
            if self.expiration_date <= self.effective_date:
                raise ValueError("expiration_date must be after effective_date")
        return self


class GuidelineFlag(BaseModel):
    flag_type: Literal["appetite", "wording", "data_quality", "accumulation", "referral"]
    severity: Literal["info", "warning", "critical"]
    message: str
    evidence: str | None = None


class RiskScoreBreakdown(BaseModel):
    geography_hazard_score: float = Field(..., ge=0, le=100)
    attachment_limit_severity_score: float = Field(..., ge=0, le=100)
    historical_loss_overlap_score: float = Field(..., ge=0, le=100)
    exclusion_ambiguity_score: float = Field(..., ge=0, le=100)
    document_quality_score: float = Field(..., ge=0, le=100)


class RiskAssessment(BaseModel):
    treaty: TreatySlip
    risk_score: float = Field(..., ge=0, le=100)
    risk_tier: RiskTier
    breakdown: RiskScoreBreakdown
    flags: list[GuidelineFlag] = Field(default_factory=list)
    underwriter_summary: str
