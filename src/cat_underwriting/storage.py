from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schemas import RiskAssessment


DDL = """
CREATE TABLE IF NOT EXISTS treaty_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cedent_name TEXT NOT NULL,
    treaty_type TEXT NOT NULL,
    source_file TEXT,
    risk_score REAL NOT NULL,
    risk_tier TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def save_assessment_sqlite(assessment: RiskAssessment, db_path: str | Path) -> int:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload = assessment.model_dump(mode="json")
    with sqlite3.connect(db_path) as conn:
        conn.execute(DDL)
        cursor = conn.execute(
            """
            INSERT INTO treaty_assessments
            (cedent_name, treaty_type, source_file, risk_score, risk_tier, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                assessment.treaty.cedent_name,
                assessment.treaty.treaty_type,
                assessment.treaty.source_file,
                assessment.risk_score,
                assessment.risk_tier.value,
                json.dumps(payload, indent=2),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
