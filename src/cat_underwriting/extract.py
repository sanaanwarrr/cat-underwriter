from __future__ import annotations

from datetime import date
import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from .schemas import TreatySlip


SYSTEM_PROMPT = """You are an underwriting operations extraction assistant.
Extract catastrophe reinsurance treaty slip data into strict JSON only.
Do not invent values. Use null for missing optional values and [] for missing lists.
Return fields exactly matching the provided schema.
"""


def extract_treaty_terms(
    document_text: str,
    source_file: str | None = None,
    use_llm: bool = False,
) -> TreatySlip:
    """Extract treaty terms from document text.

    In demo mode, a deterministic rule-based extractor is used so the repo runs without an API key.
    If use_llm=True and GITHUB_TOKEN is present, GitHub Models is used first and the result is
    validated with Pydantic. If validation fails, the rule-based fallback is used.
    """
    if use_llm:
        llm_result = _try_github_models(document_text)
        if llm_result:
            try:
                llm_result["source_file"] = source_file
                return TreatySlip.model_validate(llm_result)
            except ValidationError:
                pass

    return rule_based_extract(document_text, source_file=source_file)


def _try_github_models(document_text: str) -> dict[str, Any] | None:
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    endpoint = os.getenv("GITHUB_MODELS_ENDPOINT", "https://models.inference.ai.azure.com")
    model_name = os.getenv("GITHUB_MODEL_NAME", "gpt-4o-mini")

    schema_hint = TreatySlip.model_json_schema()
    user_prompt = f"""
Schema:
{json.dumps(schema_hint, indent=2)}

Treaty slip text:
{document_text[:15000]}
"""
    try:
        client = OpenAI(base_url=endpoint, api_key=token)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception:
        return None


def rule_based_extract(document_text: str, source_file: str | None = None) -> TreatySlip:
    """Small deterministic extractor for the provided samples and simple broker slips.

    This is intentionally conservative and useful for tests/demos. In production, replace or augment
    this with an LLM extraction chain.
    """
    text = _normalize(document_text)

    cedent = _field_after_label(text, ["Cedent", "Insured", "Company", "Reinsured"]) or "Unknown Cedent"
    broker = _field_after_label(text, ["Broker", "Intermediary"])
    treaty_type = _field_after_label(text, ["Treaty Type", "Program Type", "Layer Type"]) or _infer_treaty_type(text)
    effective = _extract_date_after(text, ["Effective Date", "Inception", "Period"])
    expiration = _extract_date_after(text, ["Expiration Date", "Expiry"])

    limit = _extract_money_after(text, ["Limit", "Layer Limit", "Occurrence Limit"])
    attachment = _extract_money_after(text, ["Attachment Point", "Retention", "Attaches", "Excess of", "xs"])

    if limit is None:
        # Try common layer notation: $50M xs $25M
        layer_match = re.search(r"\$?([\d,.]+)\s*([kKmMbB]?)\s*(?:xs|x/s|excess of)\s*\$?([\d,.]+)\s*([kKmMbB]?)", text)
        if layer_match:
            limit = _money_to_float(layer_match.group(1), layer_match.group(2))
            attachment = _money_to_float(layer_match.group(3), layer_match.group(4))

    if attachment is None:
        attachment = 0.0
    if limit is None:
        limit = 0.0

    covered = _extract_list_after(text, ["Covered Perils", "Perils Covered", "Coverage", "Perils"])
    excluded = _extract_list_after(text, ["Exclusions", "Excluded Perils"])
    territories = _extract_list_after(text, ["Territory", "Territories", "Geography", "Covered Area"])
    reinstatements = _extract_int_after(text, ["Reinstatements", "Reinstatement"])

    # Keyword enrichment for common hurricane slips.
    covered = covered or _keyword_list(text, ["hurricane", "windstorm", "flood", "storm surge", "wildfire", "earthquake"])
    excluded = excluded or _keyword_list(text, ["cyber", "war", "nuclear", "communicable disease", "terrorism"])
    territories = territories or _keyword_list(text, ["Florida", "Gulf Coast", "Texas", "Louisiana", "Southeast", "California"])

    confidence = _estimate_confidence(limit, attachment, covered, territories, cedent)

    return TreatySlip(
        cedent_name=cedent,
        broker_name=broker,
        treaty_type=treaty_type,
        effective_date=effective,
        expiration_date=expiration,
        limit_amount_usd=float(limit),
        attachment_point_usd=float(attachment),
        covered_perils=covered,
        excluded_perils=excluded,
        territories=territories,
        reinstatements=reinstatements,
        confidence_score=confidence,
        source_file=source_file,
        raw_extraction_notes="Rule-based fallback extractor used.",
    )


def _normalize(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text)


def _field_after_label(text: str, labels: list[str]) -> str | None:
    for label in labels:
        pattern = rf"(?im)^\s*{re.escape(label)}\s*[:\-]\s*(.+?)\s*$"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(" .;")
    return None


def _extract_date_after(text: str, labels: list[str]) -> date | None:
    for label in labels:
        pattern = rf"(?i){re.escape(label)}[^\n\d]*(\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{2,4}}|\d{{4}}-\d{{2}}-\d{{2}})"
        match = re.search(pattern, text)
        if match:
            return _parse_date(match.group(1))
    return None


def _parse_date(value: str) -> date | None:
    for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y", "%m-%d-%y"]:
        try:
            from datetime import datetime

            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _extract_money_after(text: str, labels: list[str]) -> float | None:
    for label in labels:
        pattern = rf"(?i){re.escape(label)}[^\n$\d]*(?:\$)?([\d,.]+)\s*([kKmMbB]?)"
        match = re.search(pattern, text)
        if match:
            return _money_to_float(match.group(1), match.group(2))
    return None


def _money_to_float(num: str, suffix: str = "") -> float:
    value = float(num.replace(",", ""))
    suffix = suffix.lower()
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    elif suffix == "b":
        value *= 1_000_000_000
    return value


def _extract_list_after(text: str, labels: list[str]) -> list[str]:
    for label in labels:
        pattern = rf"(?im)^\s*{re.escape(label)}\s*[:\-]\s*(.+?)\s*$"
        match = re.search(pattern, text)
        if match:
            raw = match.group(1)
            items = re.split(r",|;|/|\band\b", raw)
            return [item.strip(" .") for item in items if item.strip(" .")]
    return []


def _extract_int_after(text: str, labels: list[str]) -> int | None:
    for label in labels:
        pattern = rf"(?i){re.escape(label)}[^\n\d]*(\d+)"
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _keyword_list(text: str, keywords: list[str]) -> list[str]:
    found = []
    lowered = text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            found.append(keyword.title() if keyword.islower() else keyword)
    return found


def _infer_treaty_type(text: str) -> str:
    lowered = text.lower()
    if "xol" in lowered or "excess of loss" in lowered or "xs" in lowered:
        return "Property Cat XOL"
    if "quota share" in lowered:
        return "Quota Share"
    return "Catastrophe Treaty"


def _estimate_confidence(limit: float, attachment: float, covered: list[str], territories: list[str], cedent: str) -> float:
    score = 0.30
    if cedent != "Unknown Cedent":
        score += 0.15
    if limit > 0:
        score += 0.20
    if attachment > 0:
        score += 0.15
    if covered:
        score += 0.10
    if territories:
        score += 0.10
    return round(min(score, 0.95), 2)
