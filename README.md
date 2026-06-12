# Automated Catastrophe Treaty Underwriting Assistant

A portfolio-grade MVP that ingests a catastrophe reinsurance treaty slip, extracts structured treaty terms, validates them with Pydantic, checks underwriting guidelines, scores risk using deterministic logic, and writes triage outputs for underwriter review.

This is intentionally built as a **triage assistant**, not a system that makes final underwriting decisions.

## What the MVP does

For each submission, the pipeline produces:

- structured treaty terms
- Pydantic validation
- guideline/referral flags
- deterministic risk score
- underwriter summary
- Markdown report
- JSON assessment
- local SQLite persistence

## Current scope

The demo focuses on **U.S. property catastrophe hurricane treaty triage** using synthetic data.

You can later extend it to wildfire, earthquake, flood, or real portfolio/loss data.

## Project structure

```text
cat-treaty-underwriting-assistant/
├── app_streamlit.py
├── data/
│   ├── guidelines/
│   ├── hazard_data/
│   ├── sample_slips/
│   └── synthetic_losses/
├── notebooks/
├── outputs/
├── src/cat_underwriting/
│   ├── cli.py
│   ├── extract.py
│   ├── guidelines.py
│   ├── ingest.py
│   ├── pipeline.py
│   ├── report.py
│   ├── schemas.py
│   ├── scoring.py
│   └── storage.py
└── tests/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Optional integrations:

```bash
pip install -r requirements-optional.txt
```

## Run the sample triage

```bash
cat-triage triage data/sample_slips/treaty_slip_hurricane_florida.md
```

Or run directly:

```bash
python -m cat_underwriting.cli triage data/sample_slips/treaty_slip_hurricane_florida.md
```

Expected outputs are written to `outputs/`:

```text
outputs/
├── treaty_slip_hurricane_florida_assessment.json
├── treaty_slip_hurricane_florida_triage_report.md
└── cat_triage.sqlite
```

## Run with the Streamlit UI

```bash
pip install -r requirements-optional.txt
PYTHONPATH=src streamlit run app_streamlit.py
```

## Run tests

```bash
pytest
```

## GitHub Models integration

The repo runs without an API key using a rule-based demo extractor.

To use GitHub Models:

1. Copy `.env.example` to `.env`.
2. Add your `GITHUB_TOKEN`.
3. Install optional LLM dependency:

```bash
pip install openai python-dotenv
```

4. Run:

```bash
cat-triage triage data/sample_slips/treaty_slip_hurricane_florida.md --use-llm
```

The LLM output is still validated by the `TreatySlip` Pydantic schema before scoring.

## Risk score logic

The current deterministic scoring model uses:

| Component | Weight |
|---|---:|
| Geography hazard score | 30% |
| Attachment/limit severity | 25% |
| Historical loss overlap | 20% |
| Exclusion ambiguity | 15% |
| Document quality risk | 10% |

The scoring logic lives in `src/cat_underwriting/scoring.py` and has unit tests.

## Databricks extension

The local MVP stores results in SQLite. To adapt this to Databricks:

1. Keep `TreatySlip` and `RiskAssessment` as the canonical schemas.
2. Convert `assessment.model_dump(mode="json")` into a Spark DataFrame.
3. Write to Delta tables such as:

```python
spark.createDataFrame([assessment.model_dump(mode="json")]).write.mode("append").saveAsTable("cat_triage.treaty_assessments")
```

Suggested Delta tables:

- `cat_triage.treaty_submissions`
- `cat_triage.extracted_terms`
- `cat_triage.guideline_flags`
- `cat_triage.risk_assessments`
- `cat_triage.historical_losses`
- `cat_triage.hazard_scores`

## What to improve next

Good next steps:

1. Replace sample Markdown slips with real PDF slips.
2. Install Docling or MarkItDown for higher-quality document extraction.
3. Add ChromaDB guideline retrieval.
4. Add geocoding for county/ZIP exposure schedules.
5. Add Delta Lake writes from Databricks notebooks.
6. Add a Deepnote workflow/dashboard.
7. Add human-in-the-loop review fields.

## Resume bullet

> Built an AI-assisted catastrophe treaty underwriting triage pipeline that extracts structured treaty terms from broker submissions, validates LLM outputs with Pydantic schemas, applies guideline/referral checks, and scores hurricane accumulation risk using deterministic Python logic and synthetic hazard/loss data.

## Important disclaimer

This repo uses synthetic data and simplified scoring logic. It is not a pricing model, regulatory compliance system, or substitute for licensed underwriting judgment.
